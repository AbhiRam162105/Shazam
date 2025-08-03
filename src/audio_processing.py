"""
Audio processing module for the Shazam system.
Handles audio loading, preprocessing, and format conversion.
"""

import numpy as np
from typing import Tuple, Optional, Union
import logging
from pathlib import Path
import warnings

# Handle potentially problematic imports
try:
    import librosa
    HAVE_LIBROSA = True
except ImportError:
    HAVE_LIBROSA = False
    warnings.warn("librosa not available; some audio features will be limited")

try:
    import sounddevice as sd
    HAVE_SOUNDDEVICE = True
except ImportError:
    HAVE_SOUNDDEVICE = False
    warnings.warn("sounddevice not available; recording features will be disabled")

try:
    import soundfile as sf
    HAVE_SOUNDFILE = True
except ImportError:
    HAVE_SOUNDFILE = False
    warnings.warn("soundfile not available; some audio I/O features will be limited")

try:
    from scipy.signal import resample, resample_poly
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False
    warnings.warn("scipy not available; resampling will be disabled")

from config import (
    SAMPLE_RATE, MONO,
    MAX_QUERY_DURATION, AUDIO_FORMATS
)

logger = logging.getLogger(__name__)

import numpy as np
from typing import Tuple, Optional, Union
import logging
from pathlib import Path
import warnings

# Handle potentially problematic imports
try:
    import librosa
    HAVE_LIBROSA = True
except ImportError:
    HAVE_LIBROSA = False
    warnings.warn("librosa not available; some audio features will be limited")

try:
    import sounddevice as sd
    HAVE_SOUNDDEVICE = True
except ImportError:
    HAVE_SOUNDDEVICE = False
    warnings.warn("sounddevice not available; recording features will be disabled")

try:
    import soundfile as sf
    HAVE_SOUNDFILE = True
except ImportError:
    HAVE_SOUNDFILE = False
    warnings.warn("soundfile not available; some audio I/O features will be limited")

try:
    from scipy.signal import resample, resample_poly
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False
    warnings.warn("scipy not available; resampling will be disabled")

from config import (
    SAMPLE_RATE, MONO,
    MAX_QUERY_DURATION, AUDIO_FORMATS
)

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles all audio processing tasks for the Shazam system."""
    
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.mono = MONO
        
    def load_audio(self, audio_path: Union[str, Path]) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to target format.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_signal, sample_rate)
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio format not supported
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        if audio_path.suffix.lower() not in AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {audio_path.suffix}")
            
        try:
            # Try loading with soundfile first (avoids Numba dependency issues)
            if HAVE_SOUNDFILE:
                try:
                    # Load with soundfile which is more robust to NumPy version issues
                    audio, file_sr = sf.read(str(audio_path))
                    
                    # Convert to mono if needed
                    if self.mono and audio.ndim > 1:
                        audio = np.mean(audio, axis=1)
                    
                    # Resample if needed
                    if file_sr != self.sample_rate and HAVE_SCIPY:
                        gcd = np.gcd(file_sr, self.sample_rate)
                        audio = resample_poly(audio, 
                                             self.sample_rate // gcd, 
                                             file_sr // gcd)
                    
                    logger.info(f"Loaded audio with soundfile: {audio_path} ({len(audio)/self.sample_rate:.2f}s, {self.sample_rate}Hz)")
                    return audio, self.sample_rate
                    
                except Exception as sf_error:
                    logger.warning(f"Soundfile loading failed: {sf_error}")
            
            # Fall back to librosa if soundfile fails or is unavailable
            if HAVE_LIBROSA:
                try:
                    audio, sr = librosa.load(
                        str(audio_path),
                        sr=self.sample_rate,
                        mono=self.mono
                    )
                    
                    logger.info(f"Loaded audio with librosa: {audio_path} ({len(audio)/sr:.2f}s, {sr}Hz)")
                    return audio, sr
                    
                except Exception as librosa_error:
                    logger.error(f"Librosa failed to load audio {audio_path}: {librosa_error}")
                    raise librosa_error
            
            # If both fail, raise an error
            raise RuntimeError("No working audio loading libraries available")
            
        except Exception as e:
            logger.error(f"Failed to load audio {audio_path}: {e}")
            raise
    
    def preprocess_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Minimal processing for fingerprinting - no preprocessing applied.
        
        Args:
            audio: Input audio signal
            sr: Sample rate
            
        Returns:
            Raw audio signal (minimal processing only)
        """
        # Ensure mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)
        
        # Resample if needed - using scipy's resample_poly for better compatibility
        if sr != self.sample_rate and HAVE_SCIPY:
            try:
                # Find the greatest common divisor to minimize loss
                gcd = np.gcd(sr, self.sample_rate)
                audio = resample_poly(audio, 
                                     self.sample_rate // gcd, 
                                     sr // gcd)
            except Exception as e:
                logger.warning(f"resample_poly failed: {e}, trying basic resample")
                try:
                    # Fall back to the older resample function
                    audio = resample(audio, int(len(audio) * self.sample_rate / sr))
                except Exception as e2:
                    logger.warning(f"Basic resample also failed: {e2}, keeping original sample rate")
        elif sr != self.sample_rate:
            logger.warning(f"Sample rate conversion needed but scipy not available: {sr} -> {self.sample_rate}")
        
        # NO filtering or normalization - preserve raw audio characteristics
        
        # Limit duration for queries
        max_samples = int(MAX_QUERY_DURATION * self.sample_rate)
        if len(audio) > max_samples:
            audio = audio[:max_samples]
            logger.warning(f"Audio truncated to {MAX_QUERY_DURATION}s")
        
        return audio
    def record_audio(self, duration: float = 10.0, device: Optional[int] = None) -> Tuple[np.ndarray, int]:
        """
        Record audio from microphone.
        
        Args:
            duration: Recording duration in seconds
            device: Audio device ID (None for default)
            
        Returns:
            Tuple of (audio_signal, sample_rate)
        """
        if not HAVE_SOUNDDEVICE:
            raise ImportError("sounddevice module is not available. Cannot record audio.")
            
        logger.info(f"Recording audio for {duration}s...")
        
        try:
            # Record audio
            audio = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1 if self.mono else 2,
                device=device,
                dtype=np.float32
            )
            sd.wait()  # Wait for recording to complete
            
            # Convert to mono if needed
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            else:
                audio = audio.flatten()
            
            logger.info(f"Recording completed: {len(audio)} samples")
            return audio, self.sample_rate
            
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            raise
    
    def compute_spectrogram(self, audio: np.ndarray, 
                          n_fft: int = 2048, 
                          hop_length: int = 512) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute magnitude spectrogram of audio signal.
        
        Args:
            audio: Input audio signal
            n_fft: FFT window size
            hop_length: Hop length between frames
            
        Returns:
            Tuple of (magnitude_spectrogram, frequencies)
        """
        try:
            # Try librosa first if available
            if HAVE_LIBROSA:
                # Compute STFT with librosa
                stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
                
                # Get magnitude spectrogram
                magnitude = np.abs(stft)
                
                # Convert to dB scale for better peak detection
                magnitude_db = librosa.amplitude_to_db(magnitude, ref=np.max)
                
                # Get frequency bins
                frequencies = librosa.fft_frequencies(sr=self.sample_rate, n_fft=n_fft)
                
                return magnitude_db, frequencies
            else:
                raise ImportError("librosa not available")
                
        except Exception as e:
            # Manual fallback implementation using NumPy/SciPy directly
            logger.warning(f"Librosa spectrogram failed, using NumPy fallback: {e}")
            
            if HAVE_SCIPY:
                # Manual STFT implementation using SciPy
                from scipy import signal
                
                # Apply window function
                window = signal.get_window('hann', n_fft)
                
                # Compute STFT
                _, _, stft = signal.stft(audio, fs=self.sample_rate, window=window, 
                                         nperseg=n_fft, noverlap=n_fft-hop_length)
                
                # Get magnitude spectrogram
                magnitude = np.abs(stft)
                
                # Convert to dB scale (manual implementation)
                magnitude_db = 20.0 * np.log10(np.maximum(magnitude, 1e-10))
                
                # Calculate frequency bins
                frequencies = np.fft.rfftfreq(n_fft, 1.0/self.sample_rate)
                
                return magnitude_db, frequencies
            else:
                # Pure NumPy fallback (very basic)
                logger.warning("Using basic NumPy FFT fallback")
                
                # Simple windowed FFT approach
                hop_samples = hop_length
                n_frames = (len(audio) - n_fft) // hop_samples + 1
                
                # Prepare output arrays
                stft_shape = (n_fft // 2 + 1, n_frames)
                magnitude_db = np.zeros(stft_shape)
                
                # Apply Hann window
                window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n_fft) / (n_fft - 1))
                
                for frame in range(n_frames):
                    start = frame * hop_samples
                    end = start + n_fft
                    
                    if end <= len(audio):
                        windowed = audio[start:end] * window
                        fft_result = np.fft.rfft(windowed)
                        magnitude = np.abs(fft_result)
                        magnitude_db[:, frame] = 20.0 * np.log10(np.maximum(magnitude, 1e-10))
                
                # Calculate frequency bins
                frequencies = np.fft.rfftfreq(n_fft, 1.0/self.sample_rate)
                
                return magnitude_db, frequencies
    
    def save_audio(self, audio: np.ndarray, output_path: Union[str, Path], 
                   sr: Optional[int] = None) -> None:
        """
        Save audio signal to file.
        
        Args:
            audio: Audio signal to save
            output_path: Output file path
            sr: Sample rate (uses default if None)
        """
        if sr is None:
            sr = self.sample_rate
            
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if HAVE_SOUNDFILE:
            try:
                sf.write(str(output_path), audio, sr)
                logger.info(f"Audio saved to: {output_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to save audio with soundfile: {e}")
        
        # Try scipy.io.wavfile as fallback
        try:
            import scipy.io.wavfile
            # Normalize to [-1, 1] range if needed
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / np.max(np.abs(audio))
            # Convert to int16 for WAV
            audio_int16 = (audio * 32767).astype(np.int16)
            scipy.io.wavfile.write(str(output_path), sr, audio_int16)
            logger.info(f"Audio saved to: {output_path}")
            return
        except Exception as e:
            logger.warning(f"Failed to save audio with scipy: {e}")
        
        # Last resort - try librosa if available
        if HAVE_LIBROSA:
            try:
                # Note: librosa.output.write_wav is deprecated in newer versions
                import librosa.output
                librosa.output.write_wav(str(output_path), audio, sr)
                logger.info(f"Audio saved to: {output_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to save audio with librosa: {e}")
                
        raise RuntimeError("Could not save audio - no working audio output libraries available")
    
    def get_audio_info(self, audio_path: Union[str, Path]) -> dict:
        """
        Get audio file information without loading the full file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with audio information
        """
        # Try soundfile first
        if HAVE_SOUNDFILE:
            try:
                with sf.SoundFile(str(audio_path)) as f:
                    info = {
                        'duration': len(f) / f.samplerate,
                        'sample_rate': f.samplerate,
                        'channels': f.channels,
                        'frames': len(f),
                        'format': f.format,
                        'subtype': f.subtype
                    }
                return info
            except Exception as e:
                logger.warning(f"Could not get audio info with soundfile: {e}")
        
        # Try librosa as fallback
        if HAVE_LIBROSA:
            try:
                duration = librosa.get_duration(path=str(audio_path))
                sr = librosa.get_samplerate(path=str(audio_path))
                return {
                    'duration': duration,
                    'sample_rate': sr,
                    'frames': int(duration * sr),
                    'format': Path(audio_path).suffix[1:],  # Remove dot
                    'channels': None,  # Unknown without loading
                    'subtype': None,   # Unknown without loading
                }
            except Exception as e:
                logger.warning(f"Could not get audio info with librosa: {e}")
        
        # Last resort - try to load the file to get basic info
        try:
            import wave
            with wave.open(str(audio_path), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                channels = wf.getnchannels()
                return {
                    'duration': frames / rate,
                    'sample_rate': rate,
                    'channels': channels,
                    'frames': frames,
                    'format': 'wav',
                    'subtype': None
                }
        except Exception:
            pass
            
        logger.warning(f"Could not get any audio info for {audio_path}")
        return {}


def preprocess_for_fingerprinting(audio_path: Union[str, Path]) -> Tuple[np.ndarray, int]:
    """
    Convenience function to load and preprocess audio for fingerprinting.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Tuple of (preprocessed_audio, sample_rate)
    """
    processor = AudioProcessor()
    audio, sr = processor.load_audio(audio_path)
    audio = processor.preprocess_audio(audio, sr)
    return audio, processor.sample_rate
