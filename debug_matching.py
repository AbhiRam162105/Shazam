#!/usr/bin/env python3
"""
Debug script to understand why fingerprints don't match.
"""

import sys
import os
sys.path.append('src')

from shazam_system import ShazamSystem
import numpy as np

def debug_fingerprint_consistency():
    """Check if the same audio produces the same fingerprints."""
    print("🔍 FINGERPRINT CONSISTENCY DEBUG")
    print("=" * 50)
    
    # Initialize system
    system = ShazamSystem()
    
    # Load the same audio file twice
    audio_file = "sample_music/test_song_major_chord.wav"
    
    print(f"📁 Loading: {audio_file}")
    
    # Load audio twice using the same method
    audio1, sr1 = system.audio_processor.load_audio(audio_file)
    audio2, sr2 = system.audio_processor.load_audio(audio_file)
    
    print(f"Audio 1: shape={audio1.shape}, sr={sr1}")
    print(f"Audio 2: shape={audio2.shape}, sr={sr2}")
    print(f"Arrays identical: {np.array_equal(audio1, audio2)}")
    
    # Generate fingerprints twice
    print("\n🔨 Generating fingerprints...")
    fingerprints1 = system.fingerprinter.fingerprint_audio(audio1)
    fingerprints2 = system.fingerprinter.fingerprint_audio(audio2)
    
    print(f"Fingerprints 1: {len(fingerprints1)} hashes")
    print(f"Fingerprints 2: {len(fingerprints2)} hashes")
    
    if len(fingerprints1) > 0 and len(fingerprints2) > 0:
        # Compare first few hashes
        print("\n📊 Comparing first 5 hashes:")
        for i in range(min(5, len(fingerprints1), len(fingerprints2))):
            h1 = fingerprints1[i]
            h2 = fingerprints2[i]
            print(f"Hash {i+1}:")
            print(f"  1: {h1.hash_value} @ t={h1.time_offset}")
            print(f"  2: {h2.hash_value} @ t={h2.time_offset}")
            print(f"  Match: {h1.hash_value == h2.hash_value}")
        
        # Check if any hashes match
        hashes1_set = {h.hash_value for h in fingerprints1}
        hashes2_set = {h.hash_value for h in fingerprints2}
        common_hashes = hashes1_set.intersection(hashes2_set)
        
        print(f"\n🎯 Hash overlap:")
        print(f"  Set 1: {len(hashes1_set)} unique hashes")
        print(f"  Set 2: {len(hashes2_set)} unique hashes")
        print(f"  Common: {len(common_hashes)} hashes")
        print(f"  Overlap: {len(common_hashes)/len(hashes1_set)*100:.1f}%")
    
    # Now check what's in the database
    print("\n📚 Checking database...")
    # Get song info using SQLite query
    song_info = None
    with system.database._get_sqlite_connection() as conn:
        cursor = conn.execute(
            "SELECT id, title, artist FROM songs WHERE title = ?", 
            ("Major Chord Progression",)
        )
        row = cursor.fetchone()
        if row:
            song_info = {'id': row[0], 'title': row[1], 'artist': row[2]}
    
    if song_info:
        song_id = song_info['id']
        print(f"Song ID: {song_id}")
        
        # Get some hashes for this song from database
        sample_hashes = []
        cursor = 0
        for _ in range(5):  # Get first 5 hash keys
            keys = system.database.redis_client.scan(cursor, match="hash:*", count=10)[1]
            if not keys:
                break
            for key in keys:
                hash_data = system.database.redis_client.hgetall(key)
                if hash_data and str(song_id).encode() in hash_data:
                    sample_hashes.append(key.decode().replace("hash:", ""))
                    break
            if sample_hashes:
                break
        
        print(f"Sample database hashes for song {song_id}:")
        for i, hash_val in enumerate(sample_hashes[:3]):
            print(f"  DB Hash {i+1}: {hash_val}")
        
        print(f"\n🔍 Checking if generated hashes exist in DB:")
        matches_found = 0
        for i, fp in enumerate(fingerprints1[:10]):
            exists = system.database.redis_client.hexists(f"hash:{fp.hash_value}", song_id)
            if exists:
                matches_found += 1
            print(f"  Hash {i+1}: {fp.hash_value} - {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        
        print(f"\n📊 Database lookup results:")
        print(f"  Checked: 10 hashes")
        print(f"  Found: {matches_found} matches")
        print(f"  Success rate: {matches_found/10*100:.1f}%")
    else:
        print("❌ Song not found in database!")
    
    system.close()

if __name__ == "__main__":
    debug_fingerprint_consistency()
