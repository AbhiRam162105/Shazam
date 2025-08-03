#!/usr/bin/env python3
"""
Download open source music for testing the Shazam system.
Uses Free Music Archive and other legitimate sources.
"""

import os
import sys
import requests
from pathlib import Path
import logging
from typing import List, Dict
import json
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MusicDownloader:
    """Downloads open source music from legitimate sources."""
    
    def __init__(self, download_dir: str = "sample_music"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # List of curated public domain and CC0 music with verified URLs
        self.music_sources = [
            # FreePD.com - CC0 Licensed Music by Kevin MacLeod
            {
                'title': 'Fresh Focus',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Fresh%20Focus.mp3',
                'filename': 'Kevin MacLeod - Fresh Focus.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Upbeat/Positive',
                'duration': '2:04'
            },
            {
                'title': 'Pickled Pink',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Pickled%20Pink.mp3',
                'filename': 'Kevin MacLeod - Pickled Pink.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Ukulele Pop',
                'duration': '2:55'
            },
            {
                'title': 'The Entertainer',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/The%20Entertainer.mp3',
                'filename': 'Kevin MacLeod - The Entertainer.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Ragtime',
                'duration': '3:13'
            },
            {
                'title': 'Amazing Grace',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Amazing%20Grace.mp3',
                'filename': 'Kevin MacLeod - Amazing Grace.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Spiritual/Saxophone',
                'duration': '1:54'
            },
            {
                'title': 'Isolation Waltz',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Isolation%20Waltz.mp3',
                'filename': 'Kevin MacLeod - Isolation Waltz.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Indie Jazz',
                'duration': '3:25'
            },
            # Internet Archive - Historical Public Domain Recordings (1920s)
            {
                'title': 'Charleston (Fox Trot)',
                'artist': 'Golden Gate Orchestra',
                'url': 'https://archive.org/download/charleston1925/Charleston%20%28Fox%20Trot%29%20-%20Golden%20Gate%20Orchestra%20%281925%29.mp3',
                'filename': 'Golden Gate Orchestra - Charleston.mp3',
                'license': 'Public Domain (1925)',
                'genre': 'Early Jazz',
                'duration': '~3:00'
            },
            {
                'title': 'Blue Jeans',
                'artist': 'Premier Quartet',
                'url': 'https://archive.org/download/PremierQuartetAmericanQuartet/PremierQuartetAmericanQuartet-BlueJeans1921remake.mp3',
                'filename': 'Premier Quartet - Blue Jeans.mp3',
                'license': 'Public Domain (1921)',
                'genre': 'Sentimental Era',
                'duration': '~3:00'
            },
            # Additional FreePD tracks for variety
            {
                'title': 'Carefree',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Carefree.mp3',
                'filename': 'Kevin MacLeod - Carefree.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Upbeat',
                'duration': '2:30'
            },
            {
                'title': 'Folk Round',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Folk%20Round.mp3',
                'filename': 'Kevin MacLeod - Folk Round.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Folk',
                'duration': '1:45'
            },
            {
                'title': 'Bright Wish',
                'artist': 'Kevin MacLeod',
                'url': 'https://freepd.com/music/Bright%20Wish.mp3',
                'filename': 'Kevin MacLeod - Bright Wish.mp3',
                'license': 'CC0 (Public Domain)',
                'genre': 'Positive',
                'duration': '2:20'
            }
        ]
    
    def download_file(self, url: str, filename: str, max_retries: int = 3) -> bool:
        """Download a single file with retry logic."""
        file_path = self.download_dir / filename
        
        # Skip if already exists
        if file_path.exists():
            logger.info(f"✅ Already exists: {filename}")
            return True
        
        for attempt in range(max_retries):
            try:
                logger.info(f"📥 Downloading: {filename} (attempt {attempt + 1})")
                
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # Download with progress
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\r   Progress: {progress:.1f}%", end='', flush=True)
                
                print()  # New line after progress
                
                # Verify file size
                if total_size > 0 and file_path.stat().st_size < total_size * 0.9:
                    logger.warning(f"⚠️  File may be incomplete: {filename}")
                    return False
                
                logger.info(f"✅ Downloaded: {filename} ({file_path.stat().st_size} bytes)")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error downloading {filename} (attempt {attempt + 1}): {e}")
                if file_path.exists():
                    file_path.unlink()  # Remove partial file
                
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry
        
        return False
    
    def download_all(self) -> Dict[str, int]:
        """Download all open source music files."""
        logger.info(f"🎵 Starting download of {len(self.music_sources)} songs")
        logger.info(f"📁 Download directory: {self.download_dir.absolute()}")
        
        stats = {'total': len(self.music_sources), 'success': 0, 'failed': 0}
        
        for song in self.music_sources:
            success = self.download_file(song['url'], song['filename'])
            
            if success:
                stats['success'] += 1
                # Create metadata file
                self.save_metadata(song)
            else:
                stats['failed'] += 1
            
            # Small delay between downloads
            time.sleep(1)
        
        logger.info(f"\n🎯 Download complete!")
        logger.info(f"✅ Successfully downloaded: {stats['success']}/{stats['total']}")
        logger.info(f"❌ Failed: {stats['failed']}")
        
        return stats
    
    def save_metadata(self, song: Dict):
        """Save song metadata to a JSON file."""
        metadata_file = self.download_dir / "metadata.json"
        
        # Load existing metadata
        metadata = []
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            except:
                metadata = []
        
        # Add new song metadata
        song_metadata = {
            'filename': song['filename'],
            'title': song['title'],
            'artist': song['artist'],
            'license': song['license'],
            'genre': song.get('genre', 'Unknown'),
            'duration': song.get('duration', 'Unknown'),
            'source': 'Public Domain/CC0 Collection'
        }
        
        # Update if exists, otherwise add
        existing = next((m for m in metadata if m['filename'] == song['filename']), None)
        if existing:
            existing.update(song_metadata)
        else:
            metadata.append(song_metadata)
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def create_playlist(self):
        """Create a simple playlist file."""
        playlist_content = "# Public Domain & CC0 Music Playlist\n"
        playlist_content += "# Safe for algorithm development and testing\n\n"
        
        for song in self.music_sources:
            playlist_content += f"🎵 {song['title']} - {song['artist']}\n"
            playlist_content += f"   Genre: {song.get('genre', 'Unknown')}\n"
            playlist_content += f"   Duration: {song.get('duration', 'Unknown')}\n"
            playlist_content += f"   License: {song['license']}\n"
            playlist_content += f"   File: {song['filename']}\n\n"
        
        playlist_file = self.download_dir / "playlist.txt"
        with open(playlist_file, 'w') as f:
            f.write(playlist_content)
        
        logger.info(f"📝 Created playlist: {playlist_file}")

def create_sample_audio():
    """Create some additional test audio files."""
    import numpy as np
    import soundfile as sf
    
    logger.info("🎵 Creating additional test audio files...")
    
    sample_dir = Path("sample_music")
    sample_dir.mkdir(exist_ok=True)
    
    # Generate different test tones
    duration = 10  # seconds
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create various test sounds
    test_sounds = [
        {
            'name': 'Piano Melody - Test Audio.wav',
            'signal': np.sin(2 * np.pi * 440 * t) * np.exp(-t/2) +  # A4 note
                     np.sin(2 * np.pi * 523 * t) * np.exp(-t/3) +  # C5 note
                     np.sin(2 * np.pi * 659 * t) * np.exp(-t/4)    # E5 note
        },
        {
            'name': 'Guitar Chord - Test Audio.wav', 
            'signal': np.sin(2 * np.pi * 196 * t) +  # G3
                     np.sin(2 * np.pi * 247 * t) +  # B3
                     np.sin(2 * np.pi * 294 * t) +  # D4
                     np.sin(2 * np.pi * 392 * t)    # G4
        },
        {
            'name': 'Drum Beat - Test Audio.wav',
            'signal': np.random.normal(0, 0.1, len(t)) * (np.sin(2 * np.pi * 2 * t) > 0.8)
        }
    ]
    
    for sound in test_sounds:
        file_path = sample_dir / sound['name']
        if not file_path.exists():
            # Normalize and save
            audio = sound['signal'] / np.max(np.abs(sound['signal'])) * 0.7
            sf.write(str(file_path), audio, sample_rate)
            logger.info(f"✅ Created: {sound['name']}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download open source music for Shazam testing')
    parser.add_argument('--dir', default='sample_music', help='Download directory')
    parser.add_argument('--create-samples', action='store_true', help='Create additional test audio')
    parser.add_argument('--skip-download', action='store_true', help='Skip downloads, only create samples')
    
    args = parser.parse_args()
    
    if args.create_samples:
        try:
            create_sample_audio()
        except ImportError:
            logger.warning("⚠️  Cannot create samples - soundfile not installed")
    
    if not args.skip_download:
        downloader = MusicDownloader(args.dir)
        
        try:
            stats = downloader.download_all()
            downloader.create_playlist()
            
            if stats['success'] > 0:
                logger.info("\n🎉 Ready to build database!")
                logger.info("   Next steps:")
                logger.info("   1. Run: python auto_build_database.py")
                logger.info("   2. Test: python quick_test.py")
                logger.info("   3. Web interface: python web_interface.py")
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Download cancelled by user")
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
    
    logger.info(f"\n📁 Files in {args.dir}:")
    sample_dir = Path(args.dir)
    if sample_dir.exists():
        for file in sorted(sample_dir.iterdir()):
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                logger.info(f"   {file.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
