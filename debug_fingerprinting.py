#!/usr/bin/env python3
"""
Debug script to analyze fingerprinting process step by step.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from audio_processing import AudioProcessor
from fingerprinting import AudioFingerprinter
from config import *

def debug_fingerprinting():
    """Debug the fingerprinting process step by step."""
    
    # Load test audio
    audio_file = "sample_music/test_song_major_chord.wav"
    if not Path(audio_file).exists():
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    print(f"🔍 Debugging fingerprinting for: {audio_file}")
    
    # Load audio
    processor = AudioProcessor()
    audio_data, sample_rate = processor.load_audio(audio_file)
    print(f"📊 Audio loaded: {len(audio_data)} samples at {sample_rate}Hz")
    print(f"📊 Duration: {len(audio_data)/sample_rate:.2f}s")
    print(f"📊 Audio range: [{np.min(audio_data):.3f}, {np.max(audio_data):.3f}]")
    
    # Preprocess
    processed_audio = processor.preprocess_audio(audio_data, sample_rate)
    print(f"📊 Processed audio: {len(processed_audio)} samples")
    print(f"📊 Processed range: [{np.min(processed_audio):.3f}, {np.max(processed_audio):.3f}]")
    
    # Create spectrogram
    fingerprinter = AudioFingerprinter()
    
    # Generate spectrogram directly to inspect
    from scipy.signal import stft
    frequencies, times, Zxx = stft(
        processed_audio, 
        fs=SAMPLE_RATE,
        nperseg=FFT_WINDOW_SIZE,
        noverlap=FFT_WINDOW_SIZE - HOP_LENGTH
    )
    
    magnitude_spectrogram = np.abs(Zxx)
    print(f"📊 Spectrogram shape: {magnitude_spectrogram.shape}")
    print(f"📊 Frequency range: {frequencies[0]:.1f}Hz to {frequencies[-1]:.1f}Hz")
    print(f"📊 Time frames: {len(times)}")
    print(f"📊 Spectrogram range: [{np.min(magnitude_spectrogram):.3f}, {np.max(magnitude_spectrogram):.3f}]")
    
    # Check frequency bands
    print(f"\n🎼 Frequency bands analysis:")
    for i, (low_freq, high_freq) in enumerate(FREQ_BANDS):
        # Find frequency indices
        freq_mask = (frequencies >= low_freq) & (frequencies <= high_freq)
        band_freqs = frequencies[freq_mask]
        band_spectrogram = magnitude_spectrogram[freq_mask, :]
        
        print(f"Band {i+1}: {low_freq}-{high_freq}Hz")
        print(f"  - Frequency bins: {len(band_freqs)}")
        print(f"  - Energy range: [{np.min(band_spectrogram):.3f}, {np.max(band_spectrogram):.3f}]")
        print(f"  - Mean energy: {np.mean(band_spectrogram):.3f}")
        
        # Look for peaks in this band
        max_energies = np.max(band_spectrogram, axis=0)  # Max energy per time frame
        peak_threshold = MIN_PEAK_AMPLITUDE
        peaks_found = np.sum(max_energies > peak_threshold)
        print(f"  - Frames above threshold {peak_threshold}: {peaks_found}/{len(max_energies)}")
        
        if peaks_found > 0:
            print(f"  - Peak energy range: [{np.min(max_energies[max_energies > peak_threshold]):.3f}, {np.max(max_energies):.3f}]")
    
    # Try fingerprinting with current settings
    print(f"\n🔧 Testing fingerprinting...")
    fingerprints = fingerprinter.fingerprint_audio(processed_audio)
    print(f"📊 Fingerprints generated: {len(fingerprints)}")
    
    if len(fingerprints) == 0:
        print("❌ No fingerprints generated. Let's try with relaxed parameters...")
        
        # Try with lower threshold
        print(f"\n🔧 Trying with MIN_PEAK_AMPLITUDE = 1.0...")
        import importlib
        import config
        config.MIN_PEAK_AMPLITUDE = 1.0
        importlib.reload(config)
        
        # Create new fingerprinter
        fingerprinter2 = AudioFingerprinter()
        fingerprints2 = fingerprinter2.fingerprint_audio(processed_audio)
        print(f"📊 Fingerprints with relaxed threshold: {len(fingerprints2)}")
        
        if len(fingerprints2) > 0:
            print("✅ Success with relaxed parameters!")
            # Show some fingerprint samples
            for i, fp in enumerate(fingerprints2[:5]):
                print(f"  Fingerprint {i+1}: hash={fp.hash[:16]}..., time={fp.time_offset}")
    else:
        print("✅ Fingerprinting successful!")
        for i, fp in enumerate(fingerprints[:5]):
            print(f"  Fingerprint {i+1}: hash={fp.hash[:16]}..., time={fp.time_offset}")

if __name__ == "__main__":
    debug_fingerprinting()
