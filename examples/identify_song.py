#!/usr/bin/env python3
"""
Example: Identify a song from an audio file
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shazam_system import create_shazam_system

def main():
    """Identify a song from audio file."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get audio file from command line
    if len(sys.argv) != 2:
        print("Usage: python identify_song.py <audio_file>")
        print("Example: python identify_song.py mystery_song.wav")
        print("\nSupported formats: .mp3, .wav, .flac, .m4a, .ogg, .aac")
        sys.exit(1)
    
    audio_file = Path(sys.argv[1])
    
    if not audio_file.exists():
        print(f"Error: Audio file does not exist: {audio_file}")
        sys.exit(1)
    
    print(f"Identifying song: {audio_file}")
    print("Processing audio and searching database...")
    
    # Create Shazam system
    shazam = create_shazam_system()
    
    try:
        # Identify the song
        result = shazam.identify_audio_file(audio_file)
        
        print("\n" + "="*50)
        print("IDENTIFICATION RESULT")
        print("="*50)
        
        if result:
            print(f"🎵 MATCH FOUND!")
            print(f"Title: {result.title}")
            print(f"Artist: {result.artist}")
            if result.album:
                print(f"Album: {result.album}")
            print(f"Confidence: {result.confidence:.3f}")
            print(f"Matching hashes: {result.matching_hashes}")
            print(f"Alignment strength: {result.alignment_strength:.3f}")
            
            # Confidence interpretation
            if result.confidence >= 0.8:
                print("🟢 Very high confidence match!")
            elif result.confidence >= 0.6:
                print("🟡 High confidence match")
            elif result.confidence >= 0.4:
                print("🟠 Medium confidence match")
            else:
                print("🔴 Low confidence match")
        else:
            print("❌ NO MATCH FOUND")
            print("The song was not found in the database.")
            print("\nPossible reasons:")
            print("- Song not in database (add it with build_database.py)")
            print("- Audio quality too poor")
            print("- Audio too short or too noisy")
            print("- Background noise interference")
        
        # Show database stats
        db_stats = shazam.get_database_stats()
        print(f"\nDatabase contains {db_stats['total_songs']} songs")
        
    except Exception as e:
        print(f"Error during identification: {e}")
        sys.exit(1)
    finally:
        shazam.close()

if __name__ == "__main__":
    main()
