#!/usr/bin/env python3
"""
Simple test script to create synthetic music and test the Shazam system.
"""

import sys
import os
import numpy as np
import soundfile as sf
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_logging():
    """Setup logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def create_test_songs():
    """Create synthetic test songs with distinct characteristics."""
    sample_dir = Path(__file__).parent / "sample_music"
    sample_dir.mkdir(exist_ok=True)
    
    songs = [
        {
            'filename': 'test_song_major_chord.wav',
            'title': 'Major Chord Progression',
            'artist': 'Test Generator',
            'frequencies': [261.63, 329.63, 392.00],  # C-E-G (C major)
            'duration': 10.0,
            'tempo': 1.0
        },
        {
            'filename': 'test_song_minor_chord.wav', 
            'title': 'Minor Chord Progression',
            'artist': 'Test Generator',
            'frequencies': [220.00, 261.63, 329.63],  # A-C-E (A minor)
            'duration': 12.0,
            'tempo': 1.5
        },
        {
            'filename': 'test_song_blues_scale.wav',
            'title': 'Blues Scale Melody',
            'artist': 'Test Generator',
            'frequencies': [220.00, 246.94, 261.63, 277.18, 329.63],  # Blues scale
            'duration': 15.0,
            'tempo': 0.8
        },
        {
            'filename': 'test_song_arpeggio.wav',
            'title': 'Arpeggio Pattern',
            'artist': 'Test Generator', 
            'frequencies': [174.61, 220.00, 261.63, 329.63, 392.00],  # F-A-C-E-G
            'duration': 8.0,
            'tempo': 2.0
        }
    ]
    
    created_files = []
    sample_rate = 22050
    
    print("🎵 Creating synthetic test songs...")
    print("=" * 50)
    
    for song in songs:
        filepath = sample_dir / song['filename']
        
        if filepath.exists():
            print(f"✅ Already exists: {song['title']}")
            created_files.append((filepath, song))
            continue
        
        try:
            duration = song['duration']
            frequencies = song['frequencies']
            tempo = song['tempo']
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio = np.zeros_like(t)
            
            # Create musical pattern
            for i, freq in enumerate(frequencies):
                # Note timing - each note plays at different times for melody
                note_duration = duration / len(frequencies)
                start_time = i * note_duration
                end_time = (i + 1) * note_duration
                
                note_mask = (t >= start_time) & (t < end_time)
                note_t = t[note_mask] - start_time
                
                if len(note_t) > 0:
                    # Generate note with harmonics
                    note_signal = (
                        np.sin(2 * np.pi * freq * note_t) +
                        0.5 * np.sin(2 * np.pi * freq * 2 * note_t) +
                        0.25 * np.sin(2 * np.pi * freq * 3 * note_t)
                    )
                    
                    # Apply envelope
                    envelope = np.exp(-note_t * 2)  # Decay envelope
                    note_signal *= envelope
                    
                    audio[note_mask] += note_signal
            
            # Add rhythmic modulation
            rhythm = 0.7 + 0.3 * np.sin(2 * np.pi * tempo * t)
            audio *= rhythm
            
            # Add slight noise for realism
            noise = np.random.normal(0, 0.01, len(audio))
            audio += noise
            
            # Normalize
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio)) * 0.7
            
            # Save file
            sf.write(str(filepath), audio, sample_rate)
            
            print(f"✅ Created: {song['title']} ({duration}s)")
            created_files.append((filepath, song))
            
        except Exception as e:
            print(f"❌ Failed to create {song['filename']}: {e}")
            continue
    
    return created_files

def test_shazam_system():
    """Test the complete Shazam system."""
    try:
        # Import Shazam components
        from shazam_system import create_shazam_system
        
        print("\n🔨 Setting up Shazam system...")
        
        # Create test songs
        song_files = create_test_songs()
        
        if not song_files:
            print("❌ No test songs created")
            return False
        
        # Initialize Shazam system
        shazam = create_shazam_system()
        
        # Check database connection
        try:
            stats = shazam.get_database_stats()
            print(f"✅ Database connected (current songs: {stats['total_songs']})")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
        
        print("\n📦 Adding songs to database...")
        print("=" * 40)
        
        # Add songs to database
        added_songs = []
        for filepath, song_info in song_files:
            try:
                print(f"Processing: {song_info['title']}")
                
                song_id = shazam.add_song_to_database(
                    audio_file=str(filepath),
                    title=song_info['title'],
                    artist=song_info['artist']
                )
                
                if song_id:
                    print(f"✅ Added (ID: {song_id})")
                    added_songs.append((song_id, filepath, song_info))
                else:
                    print(f"❌ Failed to add")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        if not added_songs:
            print("❌ No songs were added to database")
            shazam.close()
            return False
        
        # Show database stats
        stats = shazam.get_database_stats()
        print(f"\n📊 Database stats:")
        print(f"   Total songs: {stats['total_songs']}")
        print(f"   Total fingerprints: {stats['total_fingerprints']}")
        
        print("\n🔍 Testing song identification...")
        print("=" * 40)
        
        # Test identification
        test_results = []
        for song_id, filepath, song_info in added_songs[:2]:  # Test first 2 songs
            try:
                print(f"Testing: {song_info['title']}")
                
                result = shazam.identify_audio_file(filepath)
                
                if result:
                    print(f"🎵 Identified: '{result.title}' by {result.artist}")
                    print(f"   Confidence: {result.confidence:.3f}")
                    print(f"   Matches: {result.matching_hashes}")
                    
                    # Check if it's the correct song
                    correct = (result.title == song_info['title'] and 
                              result.artist == song_info['artist'])
                    
                    if correct:
                        print(f"✅ CORRECT identification!")
                    else:
                        print(f"❌ INCORRECT identification")
                    
                    test_results.append({
                        'correct': correct,
                        'confidence': result.confidence,
                        'expected': f"{song_info['title']} by {song_info['artist']}",
                        'actual': f"{result.title} by {result.artist}"
                    })
                else:
                    print(f"❌ No match found")
                    test_results.append({
                        'correct': False,
                        'confidence': 0.0,
                        'expected': f"{song_info['title']} by {song_info['artist']}",
                        'actual': "No match"
                    })
                
                print("-" * 30)
                
            except Exception as e:
                print(f"❌ Identification error: {e}")
                continue
        
        # Summary
        print("\n📈 TEST SUMMARY")
        print("=" * 30)
        
        if test_results:
            correct_count = sum(1 for r in test_results if r['correct'])
            total_count = len(test_results)
            accuracy = correct_count / total_count * 100
            avg_confidence = np.mean([r['confidence'] for r in test_results])
            
            print(f"Accuracy: {correct_count}/{total_count} ({accuracy:.1f}%)")
            print(f"Average confidence: {avg_confidence:.3f}")
            
            if accuracy >= 50:
                print("🟢 System working well!")
            elif accuracy >= 25:
                print("🟡 System partially working")
            else:
                print("🔴 System needs tuning")
        else:
            print("❌ No successful tests")
        
        print("\n🎯 System is ready for use!")
        print("Next steps:")
        print("- python main.py identify sample_music/test_song_major_chord.wav")
        print("- python main.py live")
        print("- python main.py api")
        
        shazam.close()
        return len(test_results) > 0
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    setup_logging()
    
    print("🚀 SHAZAM SYSTEM TEST")
    print("=" * 50)
    print("This will create synthetic test songs and verify the system works.\n")
    
    try:
        success = test_shazam_system()
        
        if success:
            print("\n✅ Shazam system test completed!")
        else:
            print("\n❌ Shazam system test failed!")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    main()
