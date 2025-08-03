#!/usr/bin/env python3
"""
Real-time web interface for Shazam-like song recognition.
Supports microphone input and live audio identification.
"""

import sys
from pathlib import Path
import logging
import asyncio
import json
import base64
import io
import numpy as np
import soundfile as sf
import librosa
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shazam_system import ShazamSystem
from audio_processing import AudioProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'shazam_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global Shazam system
shazam_system = None
audio_buffer = []
is_recording = False
buffer_lock = threading.Lock()
last_match_found = False  # Track if we found a match during this session

class RealTimeRecognizer:
    """Handles real-time audio recognition optimized for music and singing."""
    
    def __init__(self, shazam_system: ShazamSystem):
        self.shazam_system = shazam_system
        self.sample_rate = 22050  # Match fingerprinting sample rate
        self.min_duration = 1.0   # Minimum 1 second for recognition
        self.max_duration = 5.0   # Maximum 5 seconds to process
        
    def process_audio_chunk(self, audio_data: np.ndarray) -> dict:
        """Process audio chunk and return identification result."""
        try:
            import scipy.signal
            # Ensure audio is mono and correct sample rate
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # --- BASIC BANDPASS FILTER ONLY ---
            # Assume incoming audio is 44100 Hz if not specified (common for browsers)
            # Use sample rate from client if provided, else default to 44100
            input_sr = getattr(self, 'input_sample_rate', 44100)
            if hasattr(self, 'pending_input_sample_rate'):
                input_sr = self.pending_input_sample_rate
                del self.pending_input_sample_rate
            # Only resample if the input sample rate doesn't match our target sample rate
            expected_samples = int(self.sample_rate * 5.0)
            if input_sr != self.sample_rate:
                try:
                    # Use librosa's high-quality resampling for better audio quality
                    audio_data = librosa.resample(
                        y=audio_data, 
                        orig_sr=input_sr, 
                        target_sr=self.sample_rate,
                        res_type='kaiser_fast'  # Fast but still high-quality resampling
                    )
                    
                    # If we need to adjust the number of samples to exactly match expected duration
                    if len(audio_data) != expected_samples:
                        # Either trim or pad to get exactly the expected duration
                        if len(audio_data) > expected_samples:
                            audio_data = audio_data[:expected_samples]
                        else:
                            # Pad with zeros if too short
                            padding = np.zeros(expected_samples - len(audio_data))
                            audio_data = np.concatenate([audio_data, padding])
                    
                    logger.info(f"[AUDIO] Resampled from {input_sr} Hz to {self.sample_rate} Hz: {len(audio_data)} samples (expected {expected_samples})")
                except Exception as resample_err:
                    logger.warning(f"Resampling failed: {resample_err}")
            else:
                # If sample rates match but length doesn't, adjust length
                if len(audio_data) != expected_samples:
                    if len(audio_data) > expected_samples:
                        audio_data = audio_data[:expected_samples]
                    else:
                        padding = np.zeros(expected_samples - len(audio_data))
                        audio_data = np.concatenate([audio_data, padding])
                logger.info(f"[AUDIO] No resampling needed: input_sr={input_sr}, samples={len(audio_data)} (expected {expected_samples})")

            # Apply bandpass filter: 300 Hz - 4000 Hz
            try:
                sos = scipy.signal.butter(4, [300, 4000], btype='band', fs=self.sample_rate, output='sos')
                audio_data = scipy.signal.sosfilt(sos, audio_data)
            except Exception as filter_err:
                logger.warning(f"Bandpass filter failed: {filter_err}")
            # --- END BANDPASS FILTER ONLY ---

            # ...existing code...

            # Check audio duration
            duration = len(audio_data) / self.sample_rate
            if duration < self.min_duration:
                return {'found': False, 'message': f'Audio too short ({duration:.1f}s), need at least {self.min_duration}s'}

            # Check if audio has sufficient volume
            rms = np.sqrt(np.mean(audio_data**2))
            if rms < 0.001:  # Adjusted threshold for normalized audio
                return {'found': False, 'message': 'No audio detected - please try again'}
            
            # Apply additional gain if audio is still too quiet for recognition
            if rms < 0.1:  # Increased threshold for boost
                boost_gain = min(0.15 / rms, 8.0)  # Boost to higher level, max 8x gain
                audio_data = audio_data * boost_gain
                rms = np.sqrt(np.mean(audio_data**2))  # Recalculate RMS after boost
                logger.info(f"Applied boost gain {boost_gain:.2f}x, new RMS: {rms:.4f}")
            
            # Apply soft limiter to prevent clipping while maintaining loudness
            peak_level = np.max(np.abs(audio_data))
            if peak_level > 0.95:  # If we're close to clipping
                # Soft compression/limiting
                threshold = 0.8
                ratio = 4.0  # 4:1 compression ratio
                
                # Find samples above threshold
                over_threshold = np.abs(audio_data) > threshold
                
                # Apply compression to samples above threshold
                if np.any(over_threshold):
                    signs = np.sign(audio_data)
                    abs_audio = np.abs(audio_data)
                    
                    # Compress the portions above threshold
                    compressed = np.where(
                        over_threshold,
                        threshold + (abs_audio - threshold) / ratio,
                        abs_audio
                    )
                    
                    audio_data = signs * compressed
                    logger.info(f"Applied soft limiting (peak: {peak_level:.3f} -> {np.max(np.abs(audio_data)):.3f})")
                    rms = np.sqrt(np.mean(audio_data**2))  # Recalculate RMS after limiting

            # Save improved audio at higher quality
            temp_path = "temp/live_audio.wav"
            Path("temp").mkdir(exist_ok=True)
            
            # Final RMS check before saving - ensure audio is at good level
            final_rms = np.sqrt(np.mean(audio_data**2))
            if final_rms < 0.08:  # If still too quiet, apply one more boost
                final_boost = min(0.12 / final_rms, 3.0)  # Conservative final boost
                audio_data = audio_data * final_boost
                final_rms = np.sqrt(np.mean(audio_data**2))
                logger.info(f"Applied final boost {final_boost:.2f}x before saving, RMS: {final_rms:.4f}")
            
            # Using higher quality parameters for soundfile to avoid distortion
            sf.write(
                temp_path, 
                audio_data, 
                self.sample_rate, 
                subtype='PCM_24',  # 24-bit for better quality
                format='WAV'
            )

            # Identify using Shazam system
            result = self.shazam_system.identify_audio_file(temp_path)

            if result:
                recognition_type = 'music' if rms > 0.1 else 'singing/humming'  # Adjusted threshold
                logger.info(f"✅ Match found: {result.title} by {result.artist} (confidence: {result.confidence:.3f})")
                return {
                    'found': True,
                    'title': str(result.title),
                    'artist': str(result.artist),
                    'album': str(result.album or 'Unknown Album'),
                    'confidence': float(round(result.confidence, 3)),
                    'time_offset': float(round(result.time_offset, 2)),
                    'recognition_type': str(recognition_type),
                    'audio_duration': float(round(duration, 1)),
                    'audio_level': float(round(rms, 3))
                }
            else:
                logger.info(f"❌ No match found for {duration:.1f}s audio (RMS: {rms:.4f})")
                return {
                    'found': False, 
                    'message': 'No match found - continuing to listen...',
                    'audio_duration': float(round(duration, 1)),
                    'audio_level': float(round(rms, 3))
                }
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {'found': False, 'error': str(e)}

# Initialize recognizer
recognizer = None

@app.route('/')
def index():
    """Main web interface."""
    return render_template('index.html')

@app.route('/status')
def status():
    """Get system status."""
    global shazam_system
    
    if not shazam_system:
        return jsonify({'status': 'not_initialized', 'system_ready': False})
    
    try:
        # Get database stats
        all_songs = shazam_system.database.get_all_songs()
        total_songs = len(all_songs) if all_songs else 0
        
        return jsonify({
            'status': 'ready',
            'total_songs': total_songs,
            'system_ready': True,
            'message': f'Database loaded with {total_songs} songs'
        })
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({'status': 'error', 'system_ready': False, 'message': str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    emit('status', {'message': 'Connected to Shazam server'})

@socketio.on('disconnect') 
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")

@socketio.on('start_recording')
def handle_start_recording():
    """Start audio recording session."""
    global is_recording, audio_buffer, last_match_found
    
    with buffer_lock:
        is_recording = True
        audio_buffer = []
        last_match_found = False  # Reset match status for new session
    
    logger.info("Started recording session")
    emit('recording_status', {'recording': True})

@socketio.on('stop_recording')
def handle_stop_recording():
    """Stop recording and process accumulated audio."""
    global is_recording, audio_buffer, recognizer, last_match_found
    
    with buffer_lock:
        is_recording = False
        current_buffer = audio_buffer.copy()
        audio_buffer = []
    
    logger.info(f"Stopped recording, processing {len(current_buffer)} audio chunks")
    emit('recording_status', {'recording': False})
    
    # Process remaining audio if we have enough and haven't found a match yet
    if current_buffer and recognizer and not last_match_found:
        try:
            # Concatenate all remaining audio chunks
            remaining_audio = np.concatenate(current_buffer)
            
            # Only process if we have at least 2 seconds of audio
            min_final_samples = int(recognizer.sample_rate * 2.0)  # 2 seconds minimum
            
            if len(remaining_audio) >= min_final_samples:
                # For final processing, use whatever audio we have (don't enforce 5-second requirement)
                duration = len(remaining_audio) / recognizer.sample_rate
                logger.info(f"[FINAL] Processing final {duration:.1f}s of audio")
                
                emit('processing', {'message': f'Analyzing final {duration:.1f}s of audio...'})
                result = recognizer.process_audio_chunk(remaining_audio)
                
                # Send result back to client
                emit('recognition_result', result)
            else:
                logger.info(f"Final audio too short ({len(remaining_audio)} samples, need {min_final_samples})")
                
        except Exception as e:
            logger.error(f"Error processing final recorded audio: {e}")
            emit('recognition_result', {'found': False, 'error': str(e)})
    else:
        if last_match_found:
            logger.info("Skipping final processing - match already found during recording")
        else:
            logger.info("No audio to process on stop")

@socketio.on('audio_data')
def handle_audio_data(data):
    """Handle incoming audio data from client."""
    global audio_buffer, is_recording
    
    logger.info(f"Received audio_data event. is_recording: {is_recording}")
    
    if not is_recording:
        logger.warning("Received audio data but recording is not active - ignoring")
        return
    
    try:
        # Get sample rate from client if provided
        sample_rate = data.get('sample_rate')
        if sample_rate and recognizer:
            try:
                recognizer.pending_input_sample_rate = int(sample_rate)
            except Exception:
                pass
        # Decode base64 audio data
        audio_bytes = base64.b64decode(data['audio'])
        logger.info(f"Decoded {len(audio_bytes)} bytes of audio data")
        
        # Check if this is raw PCM data or WebM
        audio_format = data.get('format', 'webm')
        
        if audio_format == 'pcm':
            # Handle raw PCM data (preferred method)
            try:
                # Convert directly from 16-bit PCM and normalize to float [-1.0, 1.0] range
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                
                # Log raw audio levels before normalization
                raw_rms = np.sqrt(np.mean((audio_data)**2))
                raw_peak = np.max(np.abs(audio_data))
                logger.info(f"Raw 16-bit audio: RMS={raw_rms:.0f}, Peak={raw_peak:.0f} (max possible: 32768)")
                
                # Normalize to [-1.0, 1.0] range - critical for audio processing
                audio_data = audio_data / 32768.0
                
                # Apply gain to boost signal strength for better recognition
                # Check current level and apply appropriate gain
                rms_level = np.sqrt(np.mean(audio_data**2))
                if rms_level > 0:
                    target_rms = 0.15  # Increased target RMS level for better recognition
                    gain = min(target_rms / rms_level, 15.0)  # Increased max gain to 15x
                    audio_data = audio_data * gain
                    logger.info(f"Applied gain {gain:.2f}x (RMS: {rms_level:.4f} -> {np.sqrt(np.mean(audio_data**2)):.4f})")
                
                logger.debug(f"Received PCM audio chunk: {len(audio_data)} samples")
                
            except Exception as e:
                logger.error(f"Error decoding PCM audio: {e}")
                return
        else:
            # Handle WebM data (fallback method)
            # The WebM chunks from MediaRecorder are often incomplete/malformed
            # Let's accumulate them and try different approaches
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            # Try to decode as raw audio first (fallback approach)
            # This assumes the browser is sending raw PCM data despite the WebM container
            try:
                # First, try to treat it as raw audio data
                # MediaRecorder sometimes sends raw audio despite the WebM mime type
                
                # Skip WebM headers if present (look for audio data patterns)
                audio_start = 0
                if len(audio_bytes) > 100:  # Only for chunks large enough to have headers
                    # Look for patterns that might indicate where audio data starts
                    for i in range(0, min(1000, len(audio_bytes) - 2), 2):
                        if i + 1000 < len(audio_bytes):
                            # Check if this looks like 16-bit PCM data (reasonable amplitude range)
                            sample_chunk = audio_bytes[i:i+1000]
                            if len(sample_chunk) % 2 == 0:
                                try:
                                    test_data = np.frombuffer(sample_chunk, dtype=np.int16).astype(np.float32)
                                    # Check if the data looks reasonable (not too extreme values)
                                    max_val = np.max(np.abs(test_data))
                                    if 100 < max_val < 32000:  # Reasonable audio range
                                        audio_start = i
                                        break
                                except:
                                    continue
                
                # Extract audio data starting from the detected position
                audio_portion = audio_bytes[audio_start:]
                
                # Ensure buffer size is aligned for 16-bit PCM
                if len(audio_portion) % 2 != 0:
                    audio_portion = audio_portion[:-1]  # Remove last byte if odd
                
                if len(audio_portion) < 4:  # Too small to be meaningful
                    return
                
                # Convert to numpy array (assuming 16-bit PCM) and normalize
                audio_data = np.frombuffer(audio_portion, dtype=np.int16).astype(np.float32)
                
                # Log raw audio levels before normalization
                raw_rms = np.sqrt(np.mean((audio_data)**2))
                raw_peak = np.max(np.abs(audio_data))
                logger.info(f"Raw WebM 16-bit audio: RMS={raw_rms:.0f}, Peak={raw_peak:.0f}")
                
                # Normalize to [-1.0, 1.0] range for proper audio processing
                audio_data = audio_data / 32768.0
                
                # Apply gain to boost signal strength for better recognition
                rms_level = np.sqrt(np.mean(audio_data**2))
                if rms_level > 0:
                    target_rms = 0.15  # Increased target RMS level for better recognition
                    gain = min(target_rms / rms_level, 15.0)  # Increased max gain to 15x
                    audio_data = audio_data * gain
                    logger.info(f"Applied gain {gain:.2f}x (RMS: {rms_level:.4f} -> {np.sqrt(np.mean(audio_data**2)):.4f})")
                
                # Basic sanity check for normalized [-1.0, 1.0] range
                max_val = np.max(np.abs(audio_data))
                if max_val > 2.0:  # Beyond normalized range with some tolerance
                    logger.warning(f"Audio data seems corrupted (max value: {max_val}), skipping chunk")
                    return
                    
            except Exception as decode_error:
                logger.error(f"Error decoding audio chunk: {decode_error}")
                return
        
        # Ensure mono audio
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Skip empty audio chunks
        if len(audio_data) == 0:
            return
        
        with buffer_lock:
            audio_buffer.append(audio_data)
            
            # Process based on continuous mode with overlapping windows to catch all audio
            total_samples = sum(len(chunk) for chunk in audio_buffer)
            min_samples = int(recognizer.sample_rate * 5.0)  # 5 seconds minimum
            max_samples = int(recognizer.sample_rate * 5.0)  # 5 seconds maximum
            
            if total_samples >= min_samples:
                current_audio = np.concatenate(audio_buffer)
                # Take exactly 5 seconds of the most recent audio
                if len(current_audio) > max_samples:
                    current_audio = current_audio[-max_samples:]
                
                # Keep a 3-second overlap in buffer to ensure no audio is lost
                overlap_samples = int(recognizer.sample_rate * 3.0)  # 3 seconds overlap
                if len(current_audio) > overlap_samples:
                    # Keep the last 3 seconds in buffer for next processing
                    overlap_audio = current_audio[-overlap_samples:]
                    audio_buffer = [overlap_audio]
                else:
                    # If we don't have enough for overlap, keep everything
                    audio_buffer = [current_audio]
                
                logger.info(f"[AUDIO] Received {len(current_audio)} samples before processing. Expected: {max_samples}")
                try:
                    duration = len(current_audio) / recognizer.sample_rate
                    logger.info(f"[AUDIO] Processing {duration:.3f}s of audio for recognition (should be ~5.0s)")
                    result = recognizer.process_audio_chunk(current_audio)
                    if result.get('found', False):
                        global last_match_found
                        last_match_found = True
                    emit('recognition_result', result)
                except Exception as e:
                    logger.error(f"Error in audio processing: {e}")
                    emit('recognition_result', {'found': False, 'error': str(e)})
                
    except Exception as e:
        logger.error(f"Error handling audio data: {e}")
        emit('recognition_result', {'found': False, 'error': str(e)})

@app.route('/upload', methods=['POST'])
def upload_audio():
    """Handle audio file upload for identification."""
    global recognizer
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'})
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    try:
        # Save uploaded file
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / "uploaded_audio.wav"
        
        file.save(str(temp_path))
        
        # Process with Shazam system
        result = shazam_system.identify_audio_file(str(temp_path))
        
        if result:
            return jsonify({
                'found': True,
                'title': str(result.title),
                'artist': str(result.artist),
                'album': str(result.album or 'Unknown Album'),
                'confidence': float(round(result.confidence, 3)),
                'time_offset': float(round(result.time_offset, 2))
            })
        else:
            return jsonify({'found': False, 'message': 'No match found'})
            
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        return jsonify({'error': str(e)})

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

def initialize_system():
    """Initialize the Shazam system."""
    global shazam_system, recognizer
    
    logger.info("🎵 Initializing Shazam system...")
    shazam_system = ShazamSystem()
    recognizer = RealTimeRecognizer(shazam_system)
    logger.info("✅ System ready!")

def main():
    """Main function to start web server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Shazam Web Interface')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Create templates directory if it doesn't exist
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Create static directory if it doesn't exist
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Initialize system
    initialize_system()
    
    # Start the web server
    logger.info(f"🌐 Starting Shazam web interface on http://{args.host}:{args.port}")
    logger.info("🎤 Features available:")
    logger.info("   - Real-time microphone recognition")
    logger.info("   - Audio file upload")
    logger.info("   - Live audio streaming")
    logger.info("   - Singing detection")
    
    try:
        socketio.run(app, host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    finally:
        if shazam_system:
            shazam_system.close()

if __name__ == "__main__":
    main()
