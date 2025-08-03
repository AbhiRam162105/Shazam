#!/usr/bin/env python3
"""
Example: Build fingerprint database from a music library
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shazam_system import create_shazam_system

def main():
    """Build database from music folder."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get music folder from command line
    if len(sys.argv) != 2:
        print("Usage: python build_database.py <music_folder>")
        print("Example: python build_database.py /path/to/music/library")
        sys.exit(1)
    
    music_folder = Path(sys.argv[1])
    
    if not music_folder.exists():
        print(f"Error: Music folder does not exist: {music_folder}")
        sys.exit(1)
    
    print(f"Building Shazam database from: {music_folder}")
    print("This may take a while for large music libraries...")
    
    # Create Shazam system
    shazam = create_shazam_system()
    
    try:
        # Build database
        stats = shazam.build_database_from_folder(music_folder, recursive=True)
        
        print("\n" + "="*50)
        print("DATABASE BUILD COMPLETE")
        print("="*50)
        print(f"Processed: {stats['processed']} songs")
        print(f"Failed: {stats['failed']} songs") 
        print(f"Skipped: {stats['skipped']} songs (already in database)")
        
        # Show database stats
        db_stats = shazam.get_database_stats()
        print(f"\nDatabase Statistics:")
        print(f"Total songs: {db_stats['total_songs']}")
        print(f"Total fingerprints: {db_stats['total_fingerprints']}")
        print(f"Total duration: {db_stats['total_duration_hours']:.1f} hours")
        
        if stats['processed'] > 0:
            print(f"\nDatabase is ready for audio recognition!")
            print(f"You can now identify songs using:")
            print(f"  python examples/identify_song.py <audio_file>")
            print(f"  python examples/live_recognition.py")
        
    except KeyboardInterrupt:
        print("\nBuild interrupted by user")
    except Exception as e:
        print(f"Error building database: {e}")
        sys.exit(1)
    finally:
        shazam.close()

if __name__ == "__main__":
    main()
