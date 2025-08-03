#!/usr/bin/env python3
"""
Audio level monitor for debugging microphone input levels.
"""

import sys
from pathlib import Path
import numpy as np
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def monitor_live_audio():
    """Monitor the live_audio.wav file and report levels."""
    
    try:
        import soundfile as sf
        
        live_audio_path = "temp/live_audio.wav"
        processed_audio_path = "temp/processed_live_audio.wav"
        
        # Check original file
        if Path(live_audio_path).exists():
            print("🎵 ORIGINAL Live Audio Analysis:")
            analyze_audio_file(live_audio_path, sf)
        else:
            print(f"❌ {live_audio_path} does not exist")
        
        # Check processed file if it exists
        if Path(processed_audio_path).exists():
            print("\n🎵 PROCESSED Live Audio Analysis:")
            analyze_audio_file(processed_audio_path, sf)
        
        if not Path(live_audio_path).exists():
            print("   Please record some audio first using the web interface")
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Please install: pip install soundfile")
    except Exception as e:
        print(f"❌ Error analyzing audio: {e}")

def analyze_audio_file(file_path, sf):
    """Analyze a single audio file."""
        
        # Load the live audio file
        audio, sr = sf.read(live_audio_path)
        
        # Calculate various audio metrics
        duration = len(audio) / sr
        rms = np.sqrt(np.mean(audio**2))
        peak = np.max(np.abs(audio))
        
        # Calculate dynamic range
        if rms > 0:
            dynamic_range_db = 20 * np.log10(peak / rms)
        else:
            dynamic_range_db = float('inf')
        
        # Calculate loudness in LUFS (approximate)
        # This is a simplified version - not true LUFS
        loudness_approx = -23 + 20 * np.log10(rms) if rms > 0 else float('-inf')
        
        print(f"🎵 Live Audio Analysis: {live_audio_path}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Sample Rate: {sr}Hz")
        print(f"   RMS Level: {rms:.6f}")
        print(f"   Peak Level: {peak:.6f}")
        print(f"   Dynamic Range: {dynamic_range_db:.1f} dB")
        print(f"   Approx Loudness: {loudness_approx:.1f} LUFS")
        
        # Provide diagnostic information
        print(f"\n📊 Diagnostic Information:")
        
        if rms < 0.001:
            print("   🔇 SILENT: Audio is essentially silent")
            print("      • Check microphone permissions in browser")
            print("      • Check system microphone levels")
            print("      • Ensure microphone is not muted")
        elif rms < 0.01:
            print("   🔉 VERY QUIET: Audio level is very low")
            print("      • Check microphone gain/volume settings")
            print("      • Move closer to microphone")
            print("      • Check for background noise suppression")
        elif rms < 0.05:
            print("   🔊 QUIET: Audio level is low but usable")
            print("      • Should work with gain boost applied")
            print("      • Consider increasing microphone level")
        elif rms < 0.2:
            print("   ✅ GOOD: Audio level is appropriate")
            print("      • Should work well for recognition")
        else:
            print("   📢 LOUD: Audio level is high")
            print("      • Check for clipping or distortion")
            print("      • May need to reduce input gain")
        
        # Check for clipping
        clipped_samples = np.sum(np.abs(audio) > 0.99)
        if clipped_samples > 0:
            clipped_percent = (clipped_samples / len(audio)) * 100
            print(f"   ⚠️  CLIPPING: {clipped_samples} samples ({clipped_percent:.2f}%) are clipped")
        
        # Check signal-to-noise ratio (very rough estimate)
        if len(audio) > sr:  # If we have at least 1 second
            # Take first 0.1 seconds as potential "noise floor"
            noise_samples = int(0.1 * sr)
            noise_floor = np.sqrt(np.mean(audio[:noise_samples]**2))
            
            if noise_floor > 0 and rms > noise_floor:
                snr_db = 20 * np.log10(rms / noise_floor)
                print(f"   📡 Estimated SNR: {snr_db:.1f} dB")
                
                if snr_db < 10:
                    print("      ⚠️  Low SNR - may have noise issues")
                elif snr_db > 30:
                    print("      ✅ Good SNR")
        
        # Audio content analysis
        print(f"\n🔍 Content Analysis:")
        
        # Check for silence periods
        silence_threshold = 0.001
        silent_samples = np.sum(np.abs(audio) < silence_threshold)
        silence_percent = (silent_samples / len(audio)) * 100
        print(f"   Silence: {silence_percent:.1f}% of audio")
        
        # Frequency content (very basic)
        # Calculate spectral centroid as a rough measure of "brightness"
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1/sr)
        magnitude = np.abs(fft)
        
        if np.sum(magnitude) > 0:
            spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
            print(f"   Spectral Centroid: {spectral_centroid:.0f} Hz")
            
            if spectral_centroid < 500:
                print("      📉 Low frequency content (bass heavy)")
            elif spectral_centroid > 2000:
                print("      📈 High frequency content (treble heavy)")
            else:
                print("      🎯 Balanced frequency content")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Please install: pip install soundfile")
    except Exception as e:
        print(f"❌ Error analyzing audio: {e}")

if __name__ == "__main__":
    monitor_live_audio()
