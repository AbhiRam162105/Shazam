#!/usr/bin/env python3
"""
Download copyright-free music samples for testing the Shazam system.
Uses freemusicarchive.org and other sources for royalty-free music.
"""

import os
import sys
import urllib.request
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample copyright-free music URLs (these are examples - you'll need to find actual URLs)
SAMPLE_MUSIC_URLS = [
    {
        'url': 'https://freemusicarchive.org/file/music/creative_commons/Kevin_MacLeod/Impact/Kevin_MacLeod_-_02_-_Cipher.mp3',
        'filename': 'cipher_kevin_macleod.mp3',
        'title': 'Cipher',
        'artist': 'Kevin MacLeod'
    },
    {
        'url': 'https://freemusicarchive.org/file/music/creative_commons/Kevin_MacLeod/Impact/Kevin_MacLeod_-_03_-_Call_to_Adventure.mp3',
        'filename': 'call_to_adventure_kevin_macleod.mp3',
        'title': 'Call to Adventure',
        'artist': 'Kevin MacLeod'
    },
    {
        'url': 'https://freemusicarchive.org/file/music/creative_commons/Kevin_MacLeod/Impact/Kevin_MacLeod_-_04_-_District_Four.mp3',
        'filename': 'district_four_kevin_macleod.mp3',
        'title': 'District Four',
        'artist': 'Kevin MacLeod'
    }
]

def download_sample_music():
    """Download sample music files."""
    sample_dir = Path(__file__).parent / "sample_music"
    sample_dir.mkdir(exist_ok=True)
    
    downloaded_files = []
    
    print("📥 Downloading copyright-free music samples...")
    print("=" * 50)
    
    for music_info in SAMPLE_MUSIC_URLS:
        filename = music_info['filename']
        filepath = sample_dir / filename
        
        if filepath.exists():
            print(f"✅ Already exists: {filename}")
            downloaded_files.append(filepath)
            continue
        
        try:
            print(f"📥 Downloading: {music_info['title']} by {music_info['artist']}")
            urllib.request.urlretrieve(music_info['url'], str(filepath))
            print(f"✅ Downloaded: {filename}")
            downloaded_files.append(filepath)
            
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
            continue
    
    return downloaded_files

def create_synthetic_samples():
    """Create synthetic audio samples for testing when downloads fail."""
    import numpy as np
    import soundfile as sf
    
    sample_dir = Path(__file__).parent / "sample_music"
    sample_dir.mkdir(exist_ok=True)
    
    # Define some musical pieces with different characteristics
    synthetic_pieces = [
        {
            'filename': 'synthetic_classical_440hz.wav',
            'title': 'Synthetic Classical A440',
            'artist': 'Test Generator',
            'frequencies': [440, 523.25, 659.25],  # A4, C5, E5 (A major chord)
            'duration': 15.0
        },
        {
            'filename': 'synthetic_jazz_progression.wav', 
            'title': 'Synthetic Jazz Progression',
            'artist': 'Test Generator',
            'frequencies': [261.63, 329.63, 392.00, 523.25],  # C4, E4, G4, C5
            'duration': 20.0
        },
        {
            'filename': 'synthetic_rock_power_chord.wav',
            'title': 'Synthetic Rock Power Chord',
            'artist': 'Test Generator', 
            'frequencies': [82.41, 164.81, 246.94],  # E2, E3, B3 (E5 power chord)
            'duration': 12.0
        },
        {
            'filename': 'synthetic_ambient_drone.wav',
            'title': 'Synthetic Ambient Drone',
            'artist': 'Test Generator',
            'frequencies': [110.00, 146.83, 220.00],  # A2, D3, A3
            'duration': 25.0
        }
    ]
    
    created_files = []
    sample_rate = 22050
    
    print("\n🎵 Creating synthetic music samples...")
    print("=" * 50)
    
    for piece_info in synthetic_pieces:
        filepath = sample_dir / piece_info['filename']
        
        if filepath.exists():
            print(f"✅ Already exists: {piece_info['filename']}")
            created_files.append((filepath, piece_info))
            continue
        
        try:
            # Generate synthetic audio
            duration = piece_info['duration']
            frequencies = piece_info['frequencies']
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio = np.zeros_like(t)
            
            # Create complex harmonic content
            for i, freq in enumerate(frequencies):
                # Base frequency
                audio += np.sin(2 * np.pi * freq * t) * (0.8 / (i + 1))
                
                # Add some harmonics for richness
                audio += 0.3 * np.sin(2 * np.pi * freq * 2 * t) * (0.4 / (i + 1))
                audio += 0.2 * np.sin(2 * np.pi * freq * 3 * t) * (0.2 / (i + 1))
            
            # Add some rhythmic variation
            rhythm_freq = 2.0  # 2 Hz rhythm
            rhythm_envelope = 0.5 + 0.5 * np.sin(2 * np.pi * rhythm_freq * t)
            audio *= rhythm_envelope
            
            # Add slight noise for realism
            noise = np.random.normal(0, 0.02, len(audio))
            audio += noise
            
            # Apply fade in/out
            fade_samples = int(0.5 * sample_rate)  # 0.5 second fade
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            # Normalize
            audio = audio / np.max(np.abs(audio)) * 0.8
            
            # Save to file
            sf.write(str(filepath), audio, sample_rate)
            
            print(f"✅ Created: {piece_info['title']} ({duration}s)")
            created_files.append((filepath, piece_info))
            
        except Exception as e:
            print(f"❌ Failed to create {piece_info['filename']}: {e}")
            continue
    
    return created_files

def build_test_database():
    """Build the database with sample music."""
    try:
        from shazam_system import create_shazam_system
        
        # Get music files
        print("\n🎵 Getting sample music files...")
        
        # Try downloading first, then create synthetic samples
        downloaded_files = []
        try:
            downloaded_files = download_sample_music()
        except Exception as e:
            print(f"Download failed: {e}")
        
        # Create synthetic samples
        synthetic_files = create_synthetic_samples()
        
        # Combine all files
        all_files = []
        
        # Add downloaded files
        for filepath in downloaded_files:
            # Extract metadata from filename
            name = filepath.stem
            parts = name.split('_')
            if len(parts) >= 2:
                title = ' '.join(parts[:-2]).title()
                artist = ' '.join(parts[-2:]).title()
            else:
                title = name.title()
                artist = "Unknown Artist"
            
            all_files.append((filepath, {'title': title, 'artist': artist}))
        
        # Add synthetic files
        for filepath, piece_info in synthetic_files:
            all_files.append((filepath, piece_info))
        
        if not all_files:
            print("❌ No music files available for testing")
            return False
        
        print(f"\n🔨 Building database with {len(all_files)} songs...")
        print("=" * 50)
        
        # Initialize Shazam system
        shazam = create_shazam_system()
        
        # Add each song to database
        added_count = 0
        for filepath, metadata in all_files:
            try:
                print(f"Processing: {metadata['title']} by {metadata['artist']}")
                
                song_id = shazam.add_song_to_database(
                    audio_file=str(filepath),
                    title=metadata['title'],
                    artist=metadata['artist']
                )
                
                if song_id:
                    added_count += 1
                    print(f"✅ Added to database (ID: {song_id})")
                else:
                    print(f"❌ Failed to add to database")
                    
            except Exception as e:
                print(f"❌ Error processing {filepath}: {e}")
                continue
        
        # Show database stats
        print(f"\n📊 Database Statistics:")
        print("=" * 30)
        stats = shazam.get_database_stats()
        print(f"Total songs: {stats['total_songs']}")
        print(f"Total fingerprints: {stats['total_fingerprints']}")
        print(f"Total duration: {stats['total_duration_hours']:.2f} hours")
        
        shazam.close()
        
        if added_count > 0:
            print(f"\n✅ Successfully built test database with {added_count} songs!")
            return True
        else:
            print("\n❌ Failed to add any songs to database")
            return False
            
    except Exception as e:
        print(f"❌ Error building database: {e}")
        return False

def test_identification():
    """Test song identification with the database."""
    try:
        from shazam_system import create_shazam_system
        
        print("\n🔍 Testing song identification...")
        print("=" * 40)
        
        # Get available music files
        sample_dir = Path(__file__).parent / "sample_music"
        music_files = list(sample_dir.glob("*.wav")) + list(sample_dir.glob("*.mp3"))
        
        if not music_files:
            print("❌ No music files found for testing")
            return False
        
        # Initialize Shazam system
        shazam = create_shazam_system()
        
        # Test identification with first file
        test_file = music_files[0]
        print(f"Testing identification with: {test_file.name}")
        
        result = shazam.identify_audio_file(test_file)
        
        if result:
            print(f"🎵 SUCCESS! Identified: '{result.title}' by {result.artist}")
            print(f"   Confidence: {result.confidence:.3f}")
            print(f"   Matching hashes: {result.matching_hashes}")
            print(f"   Alignment strength: {result.alignment_strength:.3f}")
            
            if result.confidence >= 0.5:
                print("🟢 High confidence identification!")
            elif result.confidence >= 0.2:
                print("🟡 Medium confidence identification")
            else:
                print("🔴 Low confidence identification")
        else:
            print("❌ No match found")
            print("This could be normal for synthetic audio or if fingerprinting needs tuning")
        
        shazam.close()
        return result is not None
        
    except Exception as e:
        print(f"❌ Error during identification test: {e}")
        return False

def main():
    """Main function to set up test database and run tests."""
    print("🚀 SHAZAM TEST DATABASE SETUP")
    print("=" * 60)
    print("This script will:")
    print("1. Download/create copyright-free music samples")
    print("2. Build the fingerprint database")
    print("3. Test song identification")
    print()
    
    try:
        # Build database
        success = build_test_database()
        
        if success:
            print("\n" + "="*60)
            print("🎉 TEST DATABASE READY!")
            print("="*60)
            
            # Test identification
            test_identification()
            
            print("\n📝 Next steps:")
            print("- Run: python main.py stats (to see database stats)")
            print("- Run: python main.py identify sample_music/filename.wav")
            print("- Run: python main.py live (for microphone recognition)")
            print("- Run: python main.py api (to start REST API server)")
            
        else:
            print("\n❌ Failed to set up test database")
            
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
    except Exception as e:
        print(f"Setup failed: {e}")

if __name__ == "__main__":
    main()
