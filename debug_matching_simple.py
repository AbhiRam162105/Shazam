#!/usr/bin/env python3
"""
Debug the matching process step by step.
"""

import sys
sys.path.append('src')

from shazam_system import ShazamSystem
from collections import defaultdict, Counter
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def debug_matching():
    """Debug the matching process."""
    print("🔍 MATCHING DEBUG")
    print("=" * 30)
    
    # Initialize system
    system = ShazamSystem()
    
    # Generate fingerprints
    audio_file = "sample_music/test_song_major_chord.wav"
    audio, sr = system.audio_processor.load_audio(audio_file)
    fingerprints = system.fingerprinter.fingerprint_audio(audio)
    
    print(f"Query fingerprints: {len(fingerprints)}")
    print(f"Unique hashes: {len(set(fp.hash_value for fp in fingerprints))}")
    
    # Step 1: Check database lookup
    print(f"\n🔍 Step 1: Database Lookup")
    raw_matches = system.database.search_fingerprints(fingerprints[:10])  # Test with first 10
    print(f"Raw matches: {len(raw_matches) if raw_matches else 0}")
    
    if raw_matches:
        for song_id, occurrences in raw_matches.items():
            print(f"  Song {song_id}: {len(occurrences)} matches")
    
    # Step 2: Try full matching
    print(f"\n🔍 Step 2: Full Matching")
    matches = system.matcher.find_matches(fingerprints[:50])  # Test with first 50
    print(f"Match results: {len(matches)}")
    
    for match in matches:
        print(f"  {match.title}: confidence={match.confidence:.3f}, "
              f"aligned={match.matching_hashes}/{match.total_query_hashes}")
    
    system.close()

if __name__ == "__main__":
    debug_matching()
