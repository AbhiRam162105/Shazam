#!/usr/bin/env python3
"""
Quick test to verify song identification works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shazam_system import ShazamSystem

def test_identification():
    """Test song identification."""
    
    print("🎵 Quick Identification Test")
    print("=" * 40)
    
    # Initialize system
    shazam = ShazamSystem()
    
    # Test files
    test_files = [
        "sample_music/test_song_major_chord.wav",
        "sample_music/test_song_minor_chord.wav", 
        "sample_music/test_song_blues_scale.wav",
        "sample_music/test_song_arpeggio.wav"
    ]
    
    for audio_file in test_files:
        if Path(audio_file).exists():
            print(f"\n🔍 Testing: {Path(audio_file).stem}")
            
            try:
                result = shazam.identify_audio_file(audio_file)
                
                if result:
                    print(f"✅ MATCH: {result.title} by {result.artist}")
                    print(f"   Confidence: {result.confidence:.3f}")
                    print(f"   Match offset: {result.time_offset:.2f}s")
                else:
                    print("❌ No match found")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"❌ File not found: {audio_file}")
    
    # Close system
    shazam.close()
    print(f"\n✅ Test completed!")

if __name__ == "__main__":
    test_identification()
