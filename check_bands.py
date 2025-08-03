#!/usr/bin/env python3
"""
Simple test to check frequency band calculations.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import *

def check_frequency_bands():
    """Check what our frequency bands map to in terms of FFT bins."""
    
    print("🔍 FREQUENCY BAND ANALYSIS")
    print("=" * 50)
    
    # Calculate frequency bins
    freq_resolution = SAMPLE_RATE / FFT_WINDOW_SIZE
    total_bins = FFT_WINDOW_SIZE // 2 + 1
    
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print(f"FFT window size: {FFT_WINDOW_SIZE}")
    print(f"Frequency resolution: {freq_resolution:.2f} Hz/bin")
    print(f"Total frequency bins: {total_bins}")
    print(f"Max frequency: {SAMPLE_RATE/2:.0f} Hz")
    
    print("\nFrequency band mapping:")
    print("-" * 30)
    
    for i, (low_freq, high_freq) in enumerate(FREQ_BANDS):
        low_bin = int(low_freq / freq_resolution)
        high_bin = int(high_freq / freq_resolution)
        bin_count = high_bin - low_bin + 1
        
        print(f"Band {i+1}: {low_freq}-{high_freq} Hz")
        print(f"  Bins: {low_bin} to {high_bin} ({bin_count} bins)")
        print(f"  Actual freq range: {low_bin * freq_resolution:.1f} - {high_bin * freq_resolution:.1f} Hz")
        print()
    
    print(f"Peak detection parameters:")
    print(f"  MIN_PEAK_AMPLITUDE: {MIN_PEAK_AMPLITUDE}")
    print(f"  PEAK_NEIGHBORHOOD_SIZE: {PEAK_NEIGHBORHOOD_SIZE}")

if __name__ == "__main__":
    check_frequency_bands()
