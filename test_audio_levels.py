#!/usr/bin/env python3
"""
Test script to verify audio level improvements.
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_audio_normalization():
    """Test the audio normalization and gain adjustment logic."""
    
    print("Testing audio normalization and gain adjustment...")
    
    # Simulate low-level 16-bit audio (like what might come from browser)
    sample_rate = 44100
    duration = 1.0  # 1 second
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a test signal (1kHz sine wave at low amplitude)
    low_amplitude_signal = np.sin(2 * np.pi * 1000 * t) * 1000  # Very quiet signal
    
    print(f"Original 16-bit signal:")
    print(f"  RMS: {np.sqrt(np.mean(low_amplitude_signal**2)):.0f}")
    print(f"  Peak: {np.max(np.abs(low_amplitude_signal)):.0f}")
    print(f"  Range: [{np.min(low_amplitude_signal):.0f}, {np.max(low_amplitude_signal):.0f}]")
    
    # Simulate the normalization process from web_interface.py
    audio_data = low_amplitude_signal.astype(np.float32)
    print(f"\nAfter float conversion:")
    print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.0f}")
    
    # Normalize to [-1.0, 1.0] range
    audio_data = audio_data / 32768.0
    print(f"\nAfter normalization (/32768):")
    print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")
    print(f"  Peak: {np.max(np.abs(audio_data)):.6f}")
    
    # Apply gain boost (same logic as in web_interface.py)
    rms_level = np.sqrt(np.mean(audio_data**2))
    if rms_level > 0:
        target_rms = 0.1  # Target RMS level for good recognition
        gain = min(target_rms / rms_level, 10.0)  # Limit gain to 10x
        audio_data = audio_data * gain
        new_rms = np.sqrt(np.mean(audio_data**2))
        print(f"\nAfter gain adjustment ({gain:.2f}x):")
        print(f"  RMS: {new_rms:.6f}")
        print(f"  Peak: {np.max(np.abs(audio_data)):.6f}")
        
        if new_rms >= 0.05:
            print("✅ Audio level is now good for recognition")
        else:
            print("⚠️  Audio level is still low")
    
    # Save test audio file
    test_file = "temp/test_audio_levels.wav"
    Path("temp").mkdir(exist_ok=True)
    sf.write(test_file, audio_data, 22050)
    print(f"\nSaved test audio to: {test_file}")
    
    return audio_data

if __name__ == "__main__":
    test_audio_normalization()
