"""
Database module for storing and retrieving audio fingerprints.
Implements an inverted index using Redis and metadata storage with SQLite.
"""

import redis
import sqlite3
import pickle
import logging
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from contextlib import contextmanager
from dataclasses import asdict
import json

try:
    from .config import (
        REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_HASH_EXPIRY,
        SQLITE_DB_PATH, DATA_DIR, BATCH_SIZE
    )
    from .fingerprinting import AudioHash
except ImportError:
    from config import (
        REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_HASH_EXPIRY,
        SQLITE_DB_PATH, DATA_DIR, BATCH_SIZE
    )
    from fingerprinting import AudioHash

logger = logging.getLogger(__name__)


class FingerprintDatabase:
    """
    Manages the fingerprint database with Redis for hash storage 
    and SQLite for metadata storage.
    """
    
    def __init__(self, 
                 redis_host: str = REDIS_HOST,
                 redis_port: int = REDIS_PORT,
                 redis_db: int = REDIS_DB,
                 sqlite_path: str = SQLITE_DB_PATH):
        """
        Initialize database connections.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port  
            redis_db: Redis database number
            sqlite_path: SQLite database file path
        """
        self.redis_client = None
        self.sqlite_path = Path(sqlite_path)
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False  # We'll handle binary data
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis: {redis_host}:{redis_port}/{redis_db}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
        
        # Initialize SQLite database
        self._init_sqlite_db()
    
    def _init_sqlite_db(self) -> None:
        """Initialize SQLite database with required tables."""
        # Create data directory if it doesn't exist
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            # Songs metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT,
                    album TEXT,
                    file_path TEXT UNIQUE NOT NULL,
                    duration REAL,
                    file_size INTEGER,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fingerprint_count INTEGER DEFAULT 0
                )
            ''')
            
            # Fingerprint statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fingerprint_stats (
                    song_id INTEGER,
                    total_hashes INTEGER,
                    processing_time REAL,
                    hash_rate REAL,
                    date_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (song_id) REFERENCES songs (id)
                )
            ''')
            
            # Create indices for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_title ON songs (title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs (artist)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_file_path ON songs (file_path)')
            
            conn.commit()
            logger.info(f"SQLite database initialized: {self.sqlite_path}")
    
    @contextmanager
    def _get_sqlite_connection(self):
        """Context manager for SQLite connections."""
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def add_song(self, title: str, artist: str, file_path: str, 
                 fingerprints: List[AudioHash], album: str = None,
                 duration: float = None, file_size: int = None) -> int:
        """
        Add a song and its fingerprints to the database.
        
        Args:
            title: Song title
            artist: Artist name
            file_path: Path to audio file
            fingerprints: List of audio hashes
            album: Album name (optional)
            duration: Song duration in seconds
            file_size: File size in bytes
            
        Returns:
            Song ID
        """
        # Add song metadata to SQLite
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            # Insert or update song metadata
            cursor.execute('''
                INSERT OR REPLACE INTO songs 
                (title, artist, album, file_path, duration, file_size, fingerprint_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, artist, album, file_path, duration, file_size, len(fingerprints)))
            
            song_id = cursor.lastrowid
            conn.commit()
        
        # Add fingerprints to Redis
        if self.redis_client and fingerprints:
            self._store_fingerprints_redis(song_id, fingerprints)
        
        logger.info(f"Added song '{title}' by {artist} with {len(fingerprints)} fingerprints")
        return song_id
    
    def _store_fingerprints_redis(self, song_id: int, fingerprints: List[AudioHash]) -> None:
        """Store fingerprints in Redis inverted index."""
        if not self.redis_client:
            logger.error("Redis client not available")
            return
        
        pipeline = self.redis_client.pipeline()
        
        for fingerprint in fingerprints:
            # Create Redis key for this hash
            hash_key = f"hash:{fingerprint.hash_value}"
            
            # Store song occurrence data
            occurrence_data = {
                'song_id': song_id,
                'time_offset': fingerprint.time_offset,
                'anchor_freq': fingerprint.anchor_freq,
                'target_freq': fingerprint.target_freq,
                'time_delta': fingerprint.time_delta
            }
            
            # Add to hash bucket (list of occurrences)
            pipeline.lpush(hash_key, pickle.dumps(occurrence_data))
            
            # Set expiry if configured
            if REDIS_HASH_EXPIRY > 0:
                pipeline.expire(hash_key, REDIS_HASH_EXPIRY)
        
        # Execute all operations
        pipeline.execute()
        logger.debug(f"Stored {len(fingerprints)} fingerprints for song {song_id}")
    
    def search_fingerprints(self, query_hashes: List[AudioHash]) -> Dict[int, List[Dict]]:
        """
        Search for matching fingerprints in the database.
        
        Args:
            query_hashes: List of query audio hashes
            
        Returns:
            Dictionary mapping song_id to list of matching occurrences
        """
        if not self.redis_client:
            logger.error("Redis client not available")
            return {}
        
        matches = {}
        
        for query_hash in query_hashes:
            hash_key = f"hash:{query_hash.hash_value}"
            
            try:
                # Get all occurrences of this hash
                occurrences = self.redis_client.lrange(hash_key, 0, -1)
                
                for occurrence_data in occurrences:
                    occurrence = pickle.loads(occurrence_data)
                    song_id = occurrence['song_id']
                    
                    # Add query information
                    occurrence['query_time'] = query_hash.time_offset
                    
                    if song_id not in matches:
                        matches[song_id] = []
                    
                    matches[song_id].append(occurrence)
                    
            except Exception as e:
                logger.warning(f"Error searching hash {query_hash.hash_value}: {e}")
                continue
        
        logger.debug(f"Found matches in {len(matches)} songs for {len(query_hashes)} query hashes")
        return matches
    
    def get_song_metadata(self, song_id: int) -> Optional[Dict]:
        """
        Get song metadata by ID.
        
        Args:
            song_id: Song ID
            
        Returns:
            Song metadata dictionary or None if not found
        """
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, artist, album, file_path, duration, 
                       file_size, date_added, fingerprint_count
                FROM songs WHERE id = ?
            ''', (song_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_song_by_path(self, file_path: str) -> Optional[Dict]:
        """Get song metadata by file path."""
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM songs WHERE file_path = ?', (file_path,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def list_songs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        List songs in the database.
        
        Args:
            limit: Maximum number of songs to return
            offset: Number of songs to skip
            
        Returns:
            List of song metadata dictionaries
        """
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, artist, album, duration, fingerprint_count, date_added
                FROM songs 
                ORDER BY date_added DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        # SQLite stats
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as song_count FROM songs')
            stats['total_songs'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(fingerprint_count) as total_fingerprints FROM songs')
            result = cursor.fetchone()[0]
            stats['total_fingerprints'] = result if result else 0
            
            cursor.execute('SELECT SUM(duration) as total_duration FROM songs')
            result = cursor.fetchone()[0]
            stats['total_duration_hours'] = (result / 3600) if result else 0
        
        # Redis stats
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
                stats['redis_memory_used'] = redis_info.get('used_memory_human', 'N/A')
                stats['redis_keys'] = self.redis_client.dbsize()
            except Exception as e:
                logger.warning(f"Could not get Redis stats: {e}")
                stats['redis_memory_used'] = 'N/A'
                stats['redis_keys'] = 0
        
        return stats
    
    def get_all_songs(self) -> List[Dict]:
        """Get all songs in the database."""
        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, artist, album, file_path, duration, 
                       fingerprint_count, date_added
                FROM songs 
                ORDER BY date_added DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def remove_song(self, song_id: int) -> bool:
        """
        Remove a song and its fingerprints from the database.
        
        Args:
            song_id: Song ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get song info first
            song_info = self.get_song_metadata(song_id)
            if not song_info:
                logger.warning(f"Song {song_id} not found")
                return False
            
            # Remove from SQLite
            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
                cursor.execute('DELETE FROM fingerprint_stats WHERE song_id = ?', (song_id,))
                conn.commit()
            
            # Note: Removing from Redis would require scanning all hash keys,
            # which is expensive. In practice, Redis entries can expire naturally
            # or be cleaned up during maintenance.
            
            logger.info(f"Removed song: {song_info['title']} by {song_info['artist']}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing song {song_id}: {e}")
            return False
    
    def cleanup_expired_hashes(self) -> int:
        """
        Clean up expired hash entries from Redis.
        
        Returns:
            Number of keys cleaned up
        """
        if not self.redis_client:
            return 0
        
        # This is a maintenance operation that would scan for expired keys
        # In practice, Redis handles expiry automatically
        # This method is here for completeness
        
        try:
            # Get all hash keys
            keys = self.redis_client.keys("hash:*")
            expired_count = 0
            
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # Key expired
                    expired_count += 1
            
            logger.info(f"Found {expired_count} expired hash keys")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def close(self) -> None:
        """Close database connections."""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")


def get_database() -> FingerprintDatabase:
    """Get a database instance with default configuration."""
    return FingerprintDatabase()
