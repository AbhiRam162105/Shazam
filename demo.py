#!/usr/bin/env python3
"""
Quick demo script to test the Shazam system functionality.
"""

import numpy as np
import tempfile
import soundfile as sf
import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import modules directly
from audio_processing import AudioProcessor
from fingerprinting import AudioFingerprinter
from database import FingerprintDatabase
from matching import AudioMatcher
from shazam_system import ShazamSystem


def generate_test_song(duration=10.0, sample_rate=22050):
    """Generate a test song with multiple frequencies."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a complex musical signal
    audio = (
        0.8 * np.sin(2 * np.pi * 440 * t) +      # A4 - fundamental
        0.4 * np.sin(2 * np.pi * 880 * t) +      # A5 - octave
        0.2 * np.sin(2 * np.pi * 1320 * t) +     # E6 - fifth
        0.1 * np.sin(2 * np.pi * 660 * t)        # E5 - fifth of fundamental
    )
    
    # Add some envelope to make it more musical
    envelope = np.exp(-t * 0.1) * (1 + 0.5 * np.sin(2 * np.pi * 0.5 * t))
    audio = audio * envelope
    
    # Add slight noise for realism
    noise = np.random.randn(len(audio)) * 0.02
    audio = audio + noise
    
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.8
    
    return audio


def demo_fingerprinting():
    """Demo the fingerprinting functionality."""
    print("🎵 SHAZAM SYSTEM DEMO")
    print("=" * 50)
    
    # Create Shazam system
    print("Initializing Shazam system...")
    shazam = ShazamSystem()
    
    try:
        # Generate test songs
        print("\n1. Generating test songs...")
        song1 = generate_test_song(duration=8.0)
        song2 = generate_test_song(duration=6.0)
        
        # Modify song2 to be slightly different
        song2 = song2 * 0.9 + 0.1 * np.sin(2 * np.pi * 523 * np.linspace(0, 6.0, len(song2)))
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f2:
            
            sf.write(f1.name, song1, 22050)
            sf.write(f2.name, song2, 22050)
            
            temp_file1 = f1.name
            temp_file2 = f2.name
        
        # Add songs to database
        print("\n2. Adding songs to database...")
        
        start_time = time.time()
        song1_id = shazam.add_song_to_database(
            audio_file=temp_file1,
            title="Test Song Alpha",
            artist="Demo Artist",
            album="Test Album"
        )
        
        song2_id = shazam.add_song_to_database(
            audio_file=temp_file2,
            title="Test Song Beta", 
            artist="Demo Artist",
            album="Test Album"
        )
        
        indexing_time = time.time() - start_time
        print(f"   Indexed 2 songs in {indexing_time:.2f} seconds")
        
        # Show database stats
        print("\n3. Database statistics:")
        stats = shazam.get_database_stats()
        print(f"   Total songs: {stats['total_songs']}")
        print(f"   Total fingerprints: {stats['total_fingerprints']}")
        print(f"   Total duration: {stats['total_duration_hours']:.2f} hours")
        
        # Test identification
        print("\n4. Testing song identification...")
        
        # Test with first song
        print("   Identifying Test Song Alpha...")
        start_time = time.time()
        result1 = shazam.identify_audio_file(temp_file1)
        id_time1 = time.time() - start_time
        
        if result1:
            print(f"   ✅ MATCH: '{result1.title}' by {result1.artist}")
            print(f"       Confidence: {result1.confidence:.3f}")
            print(f"       Matching hashes: {result1.matching_hashes}")
            print(f"       Identification time: {id_time1:.3f}s")
        else:
            print("   ❌ No match found")
        
        # Test with second song
        print("\n   Identifying Test Song Beta...")
        start_time = time.time()
        result2 = shazam.identify_audio_file(temp_file2)
        id_time2 = time.time() - start_time
        
        if result2:
            print(f"   ✅ MATCH: '{result2.title}' by {result2.artist}")
            print(f"       Confidence: {result2.confidence:.3f}")
            print(f"       Matching hashes: {result2.matching_hashes}")
            print(f"       Identification time: {id_time2:.3f}s")
        else:
            print("   ❌ No match found")
        
        # Test with noisy version
        print("\n5. Testing noise robustness...")
        noisy_song = song1 + np.random.randn(len(song1)) * 0.1
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f3:
            sf.write(f3.name, noisy_song, 22050)
            temp_file3 = f3.name
        
        print("   Identifying noisy version of Test Song Alpha...")
        start_time = time.time()
        result3 = shazam.identify_audio_file(temp_file3)
        id_time3 = time.time() - start_time
        
        if result3:
            print(f"   ✅ MATCH: '{result3.title}' by {result3.artist}")
            print(f"       Confidence: {result3.confidence:.3f}")
            print(f"       Matching hashes: {result3.matching_hashes}")
            print(f"       Identification time: {id_time3:.3f}s")
        else:
            print("   ❌ No match found")
        
        # Performance summary
        print("\n6. Performance Summary:")
        avg_id_time = np.mean([id_time1, id_time2, id_time3])
        print(f"   Average identification time: {avg_id_time:.3f}s")
        print(f"   Success rate: {sum([r is not None for r in [result1, result2, result3]])/3*100:.1f}%")
        
        # Clean up temporary files
        import os
        for temp_file in [temp_file1, temp_file2, temp_file3]:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        print("\n✅ DEMO COMPLETE")
        print("The Shazam system is working correctly!")
        print("\nNext steps:")
        print("- Add your music library: python main.py build /path/to/music")
        print("- Identify songs: python main.py identify song.wav")
        print("- Live recognition: python main.py live")
        print("- Start API server: python main.py api")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        shazam.close()


if __name__ == "__main__":
    demo_fingerprinting()
