"""
Main Shazam system orchestrator.
Coordinates all components for audio recognition functionality.
"""

import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
import os

try:
    from .audio_processing import AudioProcessor, preprocess_for_fingerprinting
    from .fingerprinting import AudioFingerprinter, create_fingerprint
    from .database import FingerprintDatabase, get_database
    from .matching import AudioMatcher, create_matcher, MatchResult
    from .config import AUDIO_FORMATS, MAX_WORKERS, DATA_DIR
except ImportError:
    from audio_processing import AudioProcessor, preprocess_for_fingerprinting
    from fingerprinting import AudioFingerprinter, create_fingerprint
    from database import FingerprintDatabase, get_database
    from matching import AudioMatcher, create_matcher, MatchResult
    from config import AUDIO_FORMATS, MAX_WORKERS, DATA_DIR

logger = logging.getLogger(__name__)


class ShazamSystem:
    """
    Main Shazam audio recognition system.
    
    Coordinates audio processing, fingerprinting, database storage,
    and matching to provide complete audio recognition functionality.
    """
    
    def __init__(self, 
                 sample_rate: int = 22050,
                 db_config: Optional[Dict] = None):
        """
        Initialize the Shazam system.
        
        Args:
            sample_rate: Target audio sample rate
            db_config: Database configuration overrides
        """
        self.sample_rate = sample_rate
        
        # Initialize components
        self.audio_processor = AudioProcessor(sample_rate=sample_rate)
        self.fingerprinter = AudioFingerprinter(sample_rate=sample_rate)
        
        # Initialize database
        if db_config:
            self.database = FingerprintDatabase(**db_config)
        else:
            self.database = get_database()
        
        self.matcher = create_matcher(self.database)
        
        logger.info("Shazam system initialized")
    
    def add_song_to_database(self, audio_file: Union[str, Path], 
                           title: str, artist: str, album: str = None) -> Optional[int]:
        """
        Add a song to the fingerprint database.
        
        Args:
            audio_file: Path to audio file
            title: Song title
            artist: Artist name
            album: Album name (optional)
            
        Returns:
            Song ID if successful, None otherwise
        """
        try:
            start_time = time.time()
            
            # Load and preprocess audio
            logger.info(f"Processing: {title} by {artist}")
            audio, sr = preprocess_for_fingerprinting(audio_file)
            
            # Generate fingerprints
            fingerprints = self.fingerprinter.fingerprint_audio(audio)
            
            if not fingerprints:
                logger.error(f"No fingerprints generated for {title}")
                return None
            
            # Get file info
            file_path = str(Path(audio_file).resolve())
            duration = len(audio) / sr
            file_size = os.path.getsize(audio_file) if os.path.exists(audio_file) else None
            
            # Add to database
            song_id = self.database.add_song(
                title=title,
                artist=artist,
                album=album,
                file_path=file_path,
                fingerprints=fingerprints,
                duration=duration,
                file_size=file_size
            )
            
            processing_time = time.time() - start_time
            hash_rate = len(fingerprints) / duration if duration > 0 else 0
            
            logger.info(f"Added '{title}' - {len(fingerprints)} hashes "
                       f"({processing_time:.2f}s, {hash_rate:.1f} hashes/sec)")
            
            return song_id
            
        except Exception as e:
            logger.error(f"Failed to add song '{title}': {e}")
            return None
    
    def identify_audio_file(self, audio_file: Union[str, Path]) -> Optional[MatchResult]:
        """
        Identify a song from an audio file.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Match result if found, None otherwise
        """
        try:
            start_time = time.time()
            
            # Load and preprocess audio
            audio, sr = preprocess_for_fingerprinting(audio_file)
            
            # Generate query fingerprints
            query_hashes = self.fingerprinter.fingerprint_audio(audio)
            
            if not query_hashes:
                logger.warning("No fingerprints generated from query audio")
                return None
            
            # Find best match
            best_match = self.matcher.identify_best_match(query_hashes)
            
            processing_time = time.time() - start_time
            
            if best_match:
                logger.info(f"Identified: '{best_match.title}' by {best_match.artist} "
                           f"in {processing_time:.2f}s")
            else:
                logger.info(f"No match found for audio file in {processing_time:.2f}s")
            
            return best_match
            
        except Exception as e:
            logger.error(f"Audio identification failed: {e}")
            return None
    
    def identify_from_microphone(self, duration: float = 10.0) -> Optional[MatchResult]:
        """
        Record audio from microphone and identify the song.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Match result if found, None otherwise
        """
        try:
            logger.info(f"Recording from microphone for {duration}s...")
            
            # Record audio
            audio, sr = self.audio_processor.record_audio(duration=duration)
            
            # Preprocess
            audio = self.audio_processor.preprocess_audio(audio, sr)
            
            # Generate fingerprints
            query_hashes = self.fingerprinter.fingerprint_audio(audio)
            
            if not query_hashes:
                logger.warning("No fingerprints generated from microphone audio")
                return None
            
            # Find best match
            best_match = self.matcher.identify_best_match(query_hashes)
            
            if best_match:
                logger.info(f"Microphone identification: '{best_match.title}' by {best_match.artist}")
            else:
                logger.info("No match found for microphone audio")
            
            return best_match
            
        except Exception as e:
            logger.error(f"Microphone identification failed: {e}")
            return None
    
    def build_database_from_folder(self, music_folder: Union[str, Path], 
                                  recursive: bool = True) -> Dict[str, int]:
        """
        Build fingerprint database from a folder of audio files.
        
        Args:
            music_folder: Path to folder containing audio files
            recursive: Whether to search subdirectories
            
        Returns:
            Dictionary with processing statistics
        """
        music_folder = Path(music_folder)
        
        if not music_folder.exists():
            raise FileNotFoundError(f"Music folder not found: {music_folder}")
        
        # Find audio files
        if recursive:
            audio_files = []
            for ext in AUDIO_FORMATS:
                audio_files.extend(music_folder.rglob(f"*{ext}"))
        else:
            audio_files = []
            for ext in AUDIO_FORMATS:
                audio_files.extend(music_folder.glob(f"*{ext}"))
        
        if not audio_files:
            logger.warning(f"No audio files found in {music_folder}")
            return {'processed': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"Found {len(audio_files)} audio files to process")
        
        # Process files
        stats = {'processed': 0, 'failed': 0, 'skipped': 0}
        
        for audio_file in audio_files:
            try:
                # Extract metadata from filename (basic approach)
                title = audio_file.stem
                artist = "Unknown Artist"
                
                # Try to extract artist from filename patterns
                if " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                
                # Check if already in database
                existing_song = self.database.get_song_by_path(str(audio_file))
                if existing_song:
                    logger.info(f"Skipping existing song: {title}")
                    stats['skipped'] += 1
                    continue
                
                # Add to database
                song_id = self.add_song_to_database(
                    audio_file=audio_file,
                    title=title,
                    artist=artist
                )
                
                if song_id:
                    stats['processed'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process {audio_file}: {e}")
                stats['failed'] += 1
        
        logger.info(f"Database building complete: {stats}")
        return stats
    
    def search_songs(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for songs in the database by title or artist.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching songs
        """
        # This is a simple implementation - could be enhanced with full-text search
        all_songs = self.database.list_songs(limit=1000)  # Get a larger set
        
        query_lower = query.lower()
        matches = []
        
        for song in all_songs:
            title_match = query_lower in song['title'].lower()
            artist_match = query_lower in song['artist'].lower()
            album_match = song.get('album') and query_lower in song['album'].lower()
            
            if title_match or artist_match or album_match:
                matches.append(song)
                if len(matches) >= limit:
                    break
        
        return matches
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        return self.database.get_database_stats()
    
    def get_system_info(self) -> Dict:
        """Get system information and configuration."""
        return {
            'sample_rate': self.sample_rate,
            'fingerprinter': {
                'n_fft': self.fingerprinter.n_fft,
                'hop_length': self.fingerprinter.hop_length,
                'freq_bands': len(self.fingerprinter.band_indices)
            },
            'database_stats': self.get_database_stats(),
            'supported_formats': AUDIO_FORMATS
        }
    
    def close(self) -> None:
        """Close system and cleanup resources."""
        if hasattr(self, 'database'):
            self.database.close()
        logger.info("Shazam system closed")


def create_shazam_system(**kwargs) -> ShazamSystem:
    """
    Create a Shazam system with default configuration.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        ShazamSystem instance
    """
    return ShazamSystem(**kwargs)
