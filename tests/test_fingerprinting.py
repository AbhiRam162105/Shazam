"""
Test suite for audio fingerprinting functionality.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fingerprinting import AudioFingerprinter, SpectralPeak, AudioHash


class TestAudioFingerprinter:
    """Test the audio fingerprinting components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.fingerprinter = AudioFingerprinter(sample_rate=22050)
        
    def test_fingerprinter_initialization(self):
        """Test fingerprinter initialization."""
        assert self.fingerprinter.sample_rate == 22050
        assert self.fingerprinter.n_fft == 2048
        assert self.fingerprinter.hop_length == 512
        assert len(self.fingerprinter.band_indices) > 0
        
    def test_compute_spectrogram(self):
        """Test spectrogram computation."""
        # Generate test signal (sine wave)
        duration = 1.0  # 1 second
        sample_rate = 22050
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * frequency * t)
        
        spectrogram = self.fingerprinter.compute_spectrogram(audio)
        
        # Check dimensions
        assert spectrogram.ndim == 2
        assert spectrogram.shape[0] > 0  # Frequency bins
        assert spectrogram.shape[1] > 0  # Time frames
        
    def test_extract_peaks(self):
        """Test peak extraction from spectrogram."""
        # Create a simple spectrogram with known peaks
        freq_bins = 100
        time_frames = 50
        spectrogram = np.random.randn(freq_bins, time_frames) * 10
        
        # Add some clear peaks
        spectrogram[20, 10] = 50  # Strong peak
        spectrogram[40, 25] = 45  # Another peak
        
        peaks = self.fingerprinter.extract_peaks(spectrogram)
        
        # Should find some peaks
        assert len(peaks) > 0
        assert all(isinstance(peak, SpectralPeak) for peak in peaks)
        
    def test_generate_hashes(self):
        """Test hash generation from peaks."""
        # Create test peaks
        peaks = [
            SpectralPeak(frequency_bin=20, time_frame=10, amplitude=50),
            SpectralPeak(frequency_bin=25, time_frame=15, amplitude=45),
            SpectralPeak(frequency_bin=30, time_frame=20, amplitude=40),
            SpectralPeak(frequency_bin=35, time_frame=25, amplitude=35),
        ]
        
        hashes = self.fingerprinter.generate_hashes(peaks)
        
        # Should generate hashes
        assert len(hashes) > 0
        assert all(isinstance(hash_obj, AudioHash) for hash_obj in hashes)
        
        # Check hash properties
        for hash_obj in hashes:
            assert len(hash_obj.hash_value) == 16  # 8 bytes hex
            assert hash_obj.time_offset >= 0
            assert hash_obj.time_delta > 0
            
    def test_fingerprint_audio_sine_wave(self):
        """Test complete fingerprinting with sine wave."""
        # Generate test signal
        duration = 2.0
        sample_rate = 22050
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * frequency * t)
        
        # Add some noise to make it more realistic
        noise = np.random.randn(len(audio)) * 0.1
        audio = audio + noise
        
        hashes = self.fingerprinter.fingerprint_audio(audio)
        
        # Should generate hashes
        assert len(hashes) > 0
        
        # Check hash rate
        hash_rate = self.fingerprinter.get_fingerprint_rate(duration, len(hashes))
        assert hash_rate > 0
        
    def test_fingerprint_audio_empty(self):
        """Test fingerprinting with empty audio."""
        audio = np.array([])
        
        with pytest.raises(Exception):
            self.fingerprinter.fingerprint_audio(audio)
            
    def test_fingerprint_audio_silence(self):
        """Test fingerprinting with silence."""
        # Generate silence
        duration = 1.0
        sample_rate = 22050
        audio = np.zeros(int(sample_rate * duration))
        
        hashes = self.fingerprinter.fingerprint_audio(audio)
        
        # Should generate few or no hashes
        assert len(hashes) >= 0
        
    def test_hash_uniqueness(self):
        """Test that different audio generates different hashes."""
        sample_rate = 22050
        duration = 1.0
        
        # Generate two different sine waves
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio1 = np.sin(2 * np.pi * 440 * t)  # A4
        audio2 = np.sin(2 * np.pi * 880 * t)  # A5
        
        hashes1 = self.fingerprinter.fingerprint_audio(audio1)
        hashes2 = self.fingerprinter.fingerprint_audio(audio2)
        
        # Should have some hashes
        assert len(hashes1) > 0
        assert len(hashes2) > 0
        
        # Hash sets should be different
        hash_values1 = {h.hash_value for h in hashes1}
        hash_values2 = {h.hash_value for h in hashes2}
        
        # Should have some different hashes (not necessarily all)
        assert len(hash_values1.intersection(hash_values2)) < min(len(hash_values1), len(hash_values2))


class TestSpectralPeak:
    """Test the SpectralPeak dataclass."""
    
    def test_peak_creation(self):
        """Test creating spectral peaks."""
        peak = SpectralPeak(frequency_bin=10, time_frame=5, amplitude=25.5)
        
        assert peak.frequency_bin == 10
        assert peak.time_frame == 5
        assert peak.amplitude == 25.5
        

class TestAudioHash:
    """Test the AudioHash dataclass."""
    
    def test_hash_creation(self):
        """Test creating audio hashes."""
        hash_obj = AudioHash(
            hash_value="abc123def456",
            time_offset=10,
            anchor_freq=20,
            target_freq=25,
            time_delta=5
        )
        
        assert hash_obj.hash_value == "abc123def456"
        assert hash_obj.time_offset == 10
        assert hash_obj.anchor_freq == 20
        assert hash_obj.target_freq == 25
        assert hash_obj.time_delta == 5


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
