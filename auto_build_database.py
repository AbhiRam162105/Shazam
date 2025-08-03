#!/usr/bin/env python3
"""
Automatic database builder that processes all audio files in sample_music folder.
Supports multiple formats and automatically adds them to the fingerprint database.
"""

import os
import sys
from pathlib import Path
import logging
from typing import List, Dict
import librosa
import soundfile as sf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shazam_system import ShazamSystem
from audio_processing import AudioProcessor
from database import FingerprintDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoDatabaseBuilder:
    """Automatically builds database from sample_music folder."""
    
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}
    
    def __init__(self, sample_music_dir: str = "sample_music"):
        self.sample_music_dir = Path(sample_music_dir)
        self.shazam_system = ShazamSystem()
        
    def scan_audio_files(self) -> List[Path]:
        """Scan sample_music directory for supported audio files."""
        audio_files = []
        
        if not self.sample_music_dir.exists():
            logger.error(f"Sample music directory not found: {self.sample_music_dir}")
            return audio_files
            
        for file_path in self.sample_music_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                audio_files.append(file_path)
                
        logger.info(f"Found {len(audio_files)} audio files")
        return sorted(audio_files)
    
    def extract_metadata_from_filename(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from filename patterns."""
        filename = file_path.stem
        
        # Try common patterns: "Artist - Title", "Title - Artist", etc.
        if " - " in filename:
            parts = filename.split(" - ", 1)
            if len(parts) == 2:
                return {
                    'title': parts[1].strip(),
                    'artist': parts[0].strip(),
                    'album': 'Unknown Album'
                }
        
        # Default fallback
        return {
            'title': filename,
            'artist': 'Unknown Artist',
            'album': 'Unknown Album'
        }
    
    def convert_to_wav_if_needed(self, file_path: Path) -> Path:
        """Convert non-WAV files to WAV format for processing."""
        if file_path.suffix.lower() == '.wav':
            return file_path
            
        # Create temp directory for converted files
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        wav_path = temp_dir / f"{file_path.stem}.wav"
        
        if wav_path.exists():
            logger.info(f"Using existing converted file: {wav_path}")
            return wav_path
            
        try:
            logger.info(f"Converting {file_path} to WAV format...")
            
            # Load audio with librosa (handles many formats)
            audio_data, sample_rate = librosa.load(str(file_path), sr=None)
            
            # Save as WAV
            sf.write(str(wav_path), audio_data, sample_rate)
            
            logger.info(f"Converted to: {wav_path}")
            return wav_path
            
        except Exception as e:
            logger.error(f"Failed to convert {file_path}: {e}")
            return None
    
    def add_song_to_database(self, file_path: Path) -> bool:
        """Add a single song to the database."""
        try:
            # Convert to WAV if needed
            wav_path = self.convert_to_wav_if_needed(file_path)
            if not wav_path:
                return False
                
            # Extract metadata
            metadata = self.extract_metadata_from_filename(file_path)
            
            logger.info(f"Adding: '{metadata['title']}' by {metadata['artist']}")
            
            # Add to database
            song_id = self.shazam_system.add_song_to_database(
                audio_file=str(wav_path),
                title=metadata['title'],
                artist=metadata['artist'],
                album=metadata['album']
            )
            
            if song_id:
                logger.info(f"✅ Successfully added song ID {song_id}")
                return True
            else:
                logger.error(f"❌ Failed to add {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing {file_path}: {e}")
            return False
    
    def build_database(self, force_rebuild: bool = False) -> Dict[str, int]:
        """Build database from all audio files in sample_music."""
        logger.info("🎵 Starting automatic database build...")
        
        if force_rebuild:
            logger.info("🔄 Force rebuild requested - clearing existing database")
            # Note: You might want to add database clearing functionality
        
        audio_files = self.scan_audio_files()
        
        if not audio_files:
            logger.warning("No audio files found to process")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        stats = {'total': len(audio_files), 'success': 0, 'failed': 0}
        
        # Check which files are already in database
        existing_songs = self.get_existing_songs()
        
        for file_path in audio_files:
            # Skip if already processed (unless force rebuild)
            if not force_rebuild and self.is_song_in_database(file_path, existing_songs):
                logger.info(f"⏭️  Skipping (already in database): {file_path.name}")
                continue
                
            if self.add_song_to_database(file_path):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"\n🎯 Database build complete!")
        logger.info(f"📊 Total files: {stats['total']}")
        logger.info(f"✅ Successfully added: {stats['success']}")
        logger.info(f"❌ Failed: {stats['failed']}")
        
        return stats
    
    def get_existing_songs(self) -> List[Dict]:
        """Get list of songs already in database."""
        try:
            # This would need to be implemented in your database class
            return self.shazam_system.database.get_all_songs()
        except:
            return []
    
    def is_song_in_database(self, file_path: Path, existing_songs: List[Dict]) -> bool:
        """Check if song is already in database based on filename."""
        filename = file_path.stem
        for song in existing_songs:
            if filename.lower() in song.get('title', '').lower():
                return True
        return False
    
    def close(self):
        """Close the system."""
        self.shazam_system.close()


def download_sample_songs():
    """Download some open source songs for testing."""
    logger.info("🌐 Downloading sample open source songs...")
    
    # Create sample_music directory
    sample_dir = Path("sample_music")
    sample_dir.mkdir(exist_ok=True)
    
    # List of open source music URLs (you can expand this)
    sample_songs = [
        {
            'url': 'https://www.soundjay.com/misc/sounds/magic-chime-02.wav',
            'filename': 'Magic Chime - Sound Jay.wav'
        },
        # Add more open source songs here
        # Note: You'll need to find legitimate open source music
    ]
    
    logger.info("ℹ️  For now, please manually add audio files to the sample_music folder")
    logger.info("📁 Supported formats: .wav, .mp3, .flac, .m4a, .ogg, .aac")
    logger.info("📝 Naming convention: 'Artist - Title.ext' for best metadata extraction")


def main():
    """Main function to build database."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build Shazam database from sample music')
    parser.add_argument('--rebuild', action='store_true', help='Force rebuild entire database')
    parser.add_argument('--download', action='store_true', help='Download sample songs first')
    parser.add_argument('--dir', default='sample_music', help='Sample music directory')
    
    args = parser.parse_args()
    
    if args.download:
        download_sample_songs()
        return
    
    # Build database
    builder = AutoDatabaseBuilder(args.dir)
    
    try:
        stats = builder.build_database(force_rebuild=args.rebuild)
        
        if stats['success'] > 0:
            logger.info("\n🎉 Database ready! You can now:")
            logger.info("   1. Test identification: python quick_test.py")
            logger.info("   2. Start web interface: python web_interface.py")
            logger.info("   3. Use live recognition: python examples/live_recognition.py")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Build cancelled by user")
    except Exception as e:
        logger.error(f"❌ Build failed: {e}")
    finally:
        builder.close()


if __name__ == "__main__":
    main()
