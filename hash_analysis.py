#!/usr/bin/env python3
"""
Check hash distribution and uniqueness.
"""

import sys
sys.path.append('src')

from shazam_system import ShazamSystem
from collections import Counter

def analyze_hashes():
    """Analyze hash distribution."""
    print("🔍 HASH DISTRIBUTION ANALYSIS")
    print("=" * 40)
    
    # Initialize system
    system = ShazamSystem()
    
    # Generate fingerprints
    audio_file = "sample_music/test_song_major_chord.wav"
    audio, sr = system.audio_processor.load_audio(audio_file)
    fingerprints = system.fingerprinter.fingerprint_audio(audio)
    
    print(f"Total fingerprints: {len(fingerprints)}")
    
    # Analyze hash uniqueness
    hash_values = [fp.hash_value for fp in fingerprints]
    unique_hashes = set(hash_values)
    print(f"Unique hashes: {len(unique_hashes)}")
    print(f"Duplication ratio: {len(fingerprints) / len(unique_hashes):.1f}")
    
    # Analyze time distribution
    times = [fp.time_offset for fp in fingerprints]
    time_counter = Counter(times)
    print(f"\nTime distribution (top 10):")
    for time_offset, count in time_counter.most_common(10):
        print(f"  t={time_offset}: {count} hashes")
    
    # Analyze hash value distribution
    hash_counter = Counter(hash_values)
    print(f"\nHash frequency (top 10):")
    for hash_val, count in hash_counter.most_common(10):
        print(f"  {hash_val}: {count} occurrences")
    
    # Check what the minimum matching requirement is
    from config import MIN_MATCHING_HASHES, CONFIDENCE_THRESHOLD
    print(f"\nMatching thresholds:")
    print(f"  MIN_MATCHING_HASHES: {MIN_MATCHING_HASHES}")
    print(f"  CONFIDENCE_THRESHOLD: {CONFIDENCE_THRESHOLD}")
    
    system.close()

if __name__ == "__main__":
    analyze_hashes()
