"""
Audio fingerprinting module implementing the Wang 2003 algorithm.
Generates robust spectral peak-based fingerprints for audio recognition.
"""

import numpy as np
import hashlib
from typing import List, Tuple, Dict, Optional
import logging
from scipy.signal import find_peaks
from dataclasses import dataclass

try:
    from .audio_processing import preprocess_for_fingerprinting
    from .config import (
        SAMPLE_RATE, FFT_WINDOW_SIZE, HOP_LENGTH, OVERLAP_RATIO,
        FREQ_BAND_LOW, FREQ_BAND_HIGH, FREQ_BANDS,
        PEAK_NEIGHBORHOOD_SIZE, PEAK_SORT, MIN_PEAK_AMPLITUDE,
        HASH_TIME_DELTA_MIN, HASH_TIME_DELTA_MAX, TARGET_ZONE_SIZE,
        HASH_FAN_VALUE, MAX_FINGERPRINTS_PER_TRACK
    )
except ImportError:
    from audio_processing import preprocess_for_fingerprinting
    from config import (
        SAMPLE_RATE, FFT_WINDOW_SIZE, HOP_LENGTH, OVERLAP_RATIO,
        FREQ_BAND_LOW, FREQ_BAND_HIGH, FREQ_BANDS,
        PEAK_NEIGHBORHOOD_SIZE, PEAK_SORT, MIN_PEAK_AMPLITUDE,
        HASH_TIME_DELTA_MIN, HASH_TIME_DELTA_MAX, TARGET_ZONE_SIZE,
        HASH_FAN_VALUE, MAX_FINGERPRINTS_PER_TRACK
    )

logger = logging.getLogger(__name__)


@dataclass
class SpectralPeak:
    """Represents a spectral peak in the constellation map."""
    frequency_bin: int
    time_frame: int
    amplitude: float


@dataclass
class AudioHash:
    """Represents a combinatorial hash from peak pairs."""
    hash_value: str
    time_offset: int
    anchor_freq: int
    target_freq: int
    time_delta: int


class AudioFingerprinter:
    """
    Implements the Wang 2003 audio fingerprinting algorithm.
    
    The algorithm works by:
    1. Computing spectrogram of audio signal
    2. Extracting spectral peaks in frequency bands
    3. Creating combinatorial hashes from peak pairs
    4. Generating compact fingerprint representation
    """
    
    def __init__(self, 
                 sample_rate: int = 22050,
                 n_fft: int = FFT_WINDOW_SIZE,
                 hop_length: int = HOP_LENGTH):
        """
        Initialize the fingerprinter.
        
        Args:
            sample_rate: Audio sample rate
            n_fft: FFT window size
            hop_length: Hop length between frames
        """
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        # Pre-compute frequency bins
        self.freq_bins = np.fft.rfftfreq(n_fft, d=1/sample_rate)
        
        # Map frequency bands to bin indices
        self.band_indices = self._compute_band_indices()
        
        logger.info(f"Fingerprinter initialized: sr={sample_rate}, "
                   f"n_fft={n_fft}, hop_length={hop_length}")
    
    def _compute_band_indices(self) -> List[Tuple[int, int]]:
        """Convert frequency bands to bin indices."""
        band_indices = []
        for low_freq, high_freq in FREQ_BANDS:
            low_bin = np.searchsorted(self.freq_bins, low_freq)
            high_bin = np.searchsorted(self.freq_bins, high_freq)
            band_indices.append((low_bin, high_bin))
        return band_indices
    
    def compute_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """
        Compute magnitude spectrogram of audio signal.
        
        Args:
            audio: Input audio signal
            
        Returns:
            Magnitude spectrogram (freq_bins x time_frames)
        """
        # Compute STFT
        from scipy.signal import stft
        
        frequencies, times, stft_data = stft(
            audio,
            fs=self.sample_rate,
            window='hann',
            nperseg=self.n_fft,
            noverlap=self.n_fft - self.hop_length,
            return_onesided=True
        )
        
        # Get magnitude spectrogram
        magnitude = np.abs(stft_data)
        
        # Use linear magnitude for peak detection (dB conversion makes values negative)
        return magnitude
    
    def extract_peaks(self, spectrogram: np.ndarray) -> List[SpectralPeak]:
        """
        Extract spectral peaks using Wang's constellation mapping approach.
        
        Args:
            spectrogram: Magnitude spectrogram
            
        Returns:
            List of spectral peaks
        """
        peaks = []
        
        # Process each frequency band separately
        for band_idx, (low_bin, high_bin) in enumerate(self.band_indices):
            band_spec = spectrogram[low_bin:high_bin, :]
            
            # Find peaks in this frequency band
            band_peaks = self._find_peaks_in_band(
                band_spec, 
                freq_offset=low_bin,
                band_idx=band_idx
            )
            peaks.extend(band_peaks)
        
        # Sort peaks by time, then by amplitude (strongest first)
        peaks.sort(key=lambda p: (p.time_frame, -p.amplitude))
        
        logger.debug(f"Extracted {len(peaks)} spectral peaks")
        return peaks
    
    def _find_peaks_in_band(self, band_spectrogram: np.ndarray, 
                           freq_offset: int, band_idx: int) -> List[SpectralPeak]:
        """
        Find local maxima peaks within a frequency band.
        
        Args:
            band_spectrogram: Spectrogram for this frequency band
            freq_offset: Frequency bin offset for this band
            band_idx: Band index for logging
            
        Returns:
            List of peaks in this band
        """
        peaks = []
        freq_bins, time_frames = band_spectrogram.shape
        
        # For each time frame, find the strongest peak in the band
        for time_idx in range(time_frames):
            time_slice = band_spectrogram[:, time_idx]
            
            # Find peaks using scipy
            peak_indices, properties = find_peaks(
                time_slice,
                height=MIN_PEAK_AMPLITUDE,
                distance=PEAK_NEIGHBORHOOD_SIZE
            )
            
            # Take only the strongest peak in this time frame
            if len(peak_indices) > 0:
                # Get the peak with highest amplitude
                amplitudes = time_slice[peak_indices]
                strongest_idx = np.argmax(amplitudes)
                
                freq_bin = peak_indices[strongest_idx] + freq_offset
                amplitude = amplitudes[strongest_idx]
                
                peak = SpectralPeak(
                    frequency_bin=freq_bin,
                    time_frame=time_idx,
                    amplitude=amplitude
                )
                peaks.append(peak)
        
        return peaks
    
    def generate_hashes(self, peaks: List[SpectralPeak]) -> List[AudioHash]:
        """
        Generate combinatorial hashes from spectral peaks.
        
        This implements the core Wang algorithm: for each anchor peak,
        pair it with nearby target peaks to create combinatorial hashes.
        
        Args:
            peaks: List of spectral peaks
            
        Returns:
            List of audio hashes
        """
        hashes = []
        
        # Sort peaks by time for efficient pairing
        peaks_by_time = sorted(peaks, key=lambda p: p.time_frame)
        
        for anchor_idx, anchor_peak in enumerate(peaks_by_time):
            # Find target peaks within the time window
            target_peaks = self._find_target_peaks(
                anchor_peak, 
                peaks_by_time[anchor_idx + 1:],
                max_targets=HASH_FAN_VALUE
            )
            
            # Generate hashes for each anchor-target pair
            for target_peak in target_peaks:
                hash_obj = self._create_hash(anchor_peak, target_peak)
                if hash_obj:
                    hashes.append(hash_obj)
        
        logger.debug(f"Generated {len(hashes)} hashes from {len(peaks)} peaks")
        return hashes
    
    def _find_target_peaks(self, anchor_peak: SpectralPeak, 
                          candidate_peaks: List[SpectralPeak],
                          max_targets: int) -> List[SpectralPeak]:
        """
        Find target peaks for hash generation within the target zone.
        
        Args:
            anchor_peak: The anchor peak
            candidate_peaks: Candidate target peaks (sorted by time)
            max_targets: Maximum number of target peaks
            
        Returns:
            List of target peaks
        """
        targets = []
        
        for peak in candidate_peaks:
            time_delta = peak.time_frame - anchor_peak.time_frame
            
            # Check if peak is within time window
            if time_delta < HASH_TIME_DELTA_MIN:
                continue
            if time_delta > HASH_TIME_DELTA_MAX:
                break  # No more valid targets (sorted by time)
            
            targets.append(peak)
            
            # Limit number of targets per anchor
            if len(targets) >= max_targets:
                break
        
        return targets
    
    def _create_hash(self, anchor: SpectralPeak, target: SpectralPeak) -> Optional[AudioHash]:
        """
        Create a combinatorial hash from an anchor-target peak pair.
        
        Hash format: combines anchor frequency, target frequency, and time delta
        into a compact representation following Wang's approach.
        
        Args:
            anchor: Anchor peak
            target: Target peak
            
        Returns:
            AudioHash object or None if invalid
        """
        time_delta = target.time_frame - anchor.time_frame
        
        # Validate time delta
        if not (HASH_TIME_DELTA_MIN <= time_delta <= HASH_TIME_DELTA_MAX):
            return None
        
        # Create hash string: anchor_freq|target_freq|time_delta
        hash_string = f"{anchor.frequency_bin}|{target.frequency_bin}|{time_delta}"
        
        # Generate compact hash using SHA-256 (first 8 bytes for efficiency)
        hash_value = hashlib.sha256(hash_string.encode()).hexdigest()[:16]
        
        return AudioHash(
            hash_value=hash_value,
            time_offset=anchor.time_frame,
            anchor_freq=anchor.frequency_bin,
            target_freq=target.frequency_bin,
            time_delta=time_delta
        )
    
    def fingerprint_audio(self, audio: np.ndarray) -> List[AudioHash]:
        """
        Complete fingerprinting pipeline for audio signal.
        
        Args:
            audio: Preprocessed audio signal
            
        Returns:
            List of audio hashes representing the fingerprint
        """
        try:
            # Step 1: Compute spectrogram
            spectrogram = self.compute_spectrogram(audio)
            
            # Step 2: Extract spectral peaks
            peaks = self.extract_peaks(spectrogram)
            
            if len(peaks) == 0:
                logger.warning("No spectral peaks found in audio")
                return []
            
            # Step 3: Generate combinatorial hashes
            hashes = self.generate_hashes(peaks)
            
            if len(hashes) == 0:
                logger.warning("No hashes generated from peaks")
                return []
            
            logger.info(f"Fingerprinting complete: {len(hashes)} hashes from "
                       f"{len(audio)/self.sample_rate:.2f}s audio")
            
            return hashes
            
        except Exception as e:
            logger.error(f"Fingerprinting failed: {e}")
            raise
    
    def get_fingerprint_rate(self, audio_duration: float, num_hashes: int) -> float:
        """
        Calculate fingerprint generation rate.
        
        Args:
            audio_duration: Duration of audio in seconds
            num_hashes: Number of hashes generated
            
        Returns:
            Hashes per second rate
        """
        if audio_duration <= 0:
            return 0.0
        return num_hashes / audio_duration


def create_fingerprint(audio: np.ndarray, sample_rate: int = 22050) -> List[AudioHash]:
    """
    Convenience function to create fingerprint from audio signal.
    
    Args:
        audio: Audio signal
        sample_rate: Sample rate
        
    Returns:
        List of audio hashes
    """
    fingerprinter = AudioFingerprinter(sample_rate=sample_rate)
    return fingerprinter.fingerprint_audio(audio)
