#!/usr/bin/env python3
"""
Simple peak detection test.
"""

import sys
import numpy as np
import soundfile as sf
from pathlib import Path
from scipy.signal import find_peaks, stft

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import *

def test_peak_detection():
    """Test peak detection on actual audio."""
    
    # Load audio
    audio_file = "sample_music/test_song_major_chord.wav"
    data, sr = sf.read(audio_file)
    
    print(f"Loaded: {audio_file}")
    print(f"Audio shape: {data.shape}, Sample rate: {sr}")
    print(f"Audio range: [{np.min(data):.3f}, {np.max(data):.3f}]")
    
    # Generate spectrogram
    frequencies, times, Zxx = stft(
        data, 
        fs=SAMPLE_RATE,
        nperseg=FFT_WINDOW_SIZE,
        noverlap=FFT_WINDOW_SIZE - HOP_LENGTH
    )
    
    magnitude = np.abs(Zxx)
    print(f"Spectrogram shape: {magnitude.shape}")
    print(f"Magnitude range: [{np.min(magnitude):.6f}, {np.max(magnitude):.6f}]")
    
    # Test each frequency band
    for i, (low_freq, high_freq) in enumerate(FREQ_BANDS):
        print(f"\nBand {i+1}: {low_freq}-{high_freq} Hz")
        
        # Get frequency mask
        freq_mask = (frequencies >= low_freq) & (frequencies <= high_freq)
        band_mag = magnitude[freq_mask, :]
        
        print(f"  Band shape: {band_mag.shape}")
        print(f"  Band magnitude range: [{np.min(band_mag):.6f}, {np.max(band_mag):.6f}]")
        
        # Count peaks with different thresholds
        thresholds = [0.001, 0.01, 0.1, 1.0]
        for thresh in thresholds:
            peak_count = 0
            for time_idx in range(band_mag.shape[1]):
                time_slice = band_mag[:, time_idx]
                peaks, _ = find_peaks(time_slice, height=thresh, distance=PEAK_NEIGHBORHOOD_SIZE)
                peak_count += len(peaks)
            
            print(f"  Threshold {thresh:5.3f}: {peak_count} peaks total")
        
        # Show some actual values from the middle of the audio
        mid_time = band_mag.shape[1] // 2
        mid_slice = band_mag[:, mid_time]
        print(f"  Mid-time slice max: {np.max(mid_slice):.6f}")
        print(f"  Mid-time slice values: {mid_slice[:5]}")

if __name__ == "__main__":
    test_peak_detection()
