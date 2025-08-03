#!/usr/bin/env python3
"""
Example: Live audio recognition from microphone
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shazam_system import create_shazam_system

def main():
    """Live audio recognition from microphone."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎤 SHAZAM LIVE RECOGNITION")
    print("=" * 50)
    print("This will record audio from your microphone and identify songs.")
    print("Make sure your microphone is working and music is playing nearby.")
    print("Press Ctrl+C to stop.\n")
    
    # Create Shazam system
    shazam = create_shazam_system()
    
    # Check database
    db_stats = shazam.get_database_stats()
    if db_stats['total_songs'] == 0:
        print("❌ ERROR: No songs in database!")
        print("Please build the database first:")
        print("  python examples/build_database.py <music_folder>")
        sys.exit(1)
    
    print(f"Database ready: {db_stats['total_songs']} songs available\n")
    
    try:
        session_count = 0
        
        while True:
            session_count += 1
            print(f"🔍 Recognition Session #{session_count}")
            print("Recording audio for 10 seconds...")
            
            try:
                # Record and identify
                result = shazam.identify_from_microphone(duration=10.0)
                
                if result:
                    print(f"🎵 IDENTIFIED: '{result.title}' by {result.artist}")
                    print(f"   Confidence: {result.confidence:.3f}")
                    if result.album:
                        print(f"   Album: {result.album}")
                else:
                    print("❌ No match found")
                
            except Exception as e:
                print(f"❌ Recognition failed: {e}")
            
            print("-" * 30)
            
            # Wait before next session
            print("Waiting 5 seconds before next session...")
            time.sleep(5)
            print()
            
    except KeyboardInterrupt:
        print("\n👋 Live recognition stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        shazam.close()

if __name__ == "__main__":
    main()
