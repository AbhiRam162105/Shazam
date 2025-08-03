"""
Matching module implementing time-offset clustering for audio recognition.
Based on the Wang 2003 algorithm for robust audio identification.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import logging
from dataclasses import dataclass

try:
    from .config import (
        MIN_MATCHING_HASHES, TIME_ALIGNMENT_TOLERANCE, 
        CONFIDENCE_THRESHOLD, HASH_TIME_DELTA_MIN, HASH_TIME_DELTA_MAX
    )
except ImportError:
    from config import (
        MIN_MATCHING_HASHES, TIME_ALIGNMENT_TOLERANCE, 
        CONFIDENCE_THRESHOLD, HASH_TIME_DELTA_MIN, HASH_TIME_DELTA_MAX
    )
from fingerprinting import AudioHash
from database import FingerprintDatabase

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Represents a song match result."""
    song_id: int
    title: str
    artist: str
    album: Optional[str]
    confidence: float
    matching_hashes: int
    total_query_hashes: int
    time_offset: float
    alignment_strength: float


class AudioMatcher:
    """
    Implements the matching algorithm for audio recognition.
    
    Uses time-offset clustering to find consistent temporal alignment
    between query fingerprints and database entries, following the
    Wang 2003 approach.
    """
    
    def __init__(self, database: FingerprintDatabase):
        """
        Initialize the matcher.
        
        Args:
            database: Fingerprint database instance
        """
        self.database = database
        
    def find_matches(self, query_hashes: List[AudioHash], 
                    min_matches: int = MIN_MATCHING_HASHES) -> List[MatchResult]:
        """
        Find matching songs for query fingerprints.
        
        Args:
            query_hashes: List of query audio hashes
            min_matches: Minimum number of matching hashes required
            
        Returns:
            List of match results sorted by confidence
        """
        if not query_hashes:
            logger.warning("No query hashes provided")
            return []
        
        # Step 1: Get raw matches from database
        raw_matches = self.database.search_fingerprints(query_hashes)
        
        if not raw_matches:
            logger.info("No raw matches found in database")
            return []
        
        # Step 2: Analyze each candidate song
        match_results = []
        
        for song_id, occurrences in raw_matches.items():
            if len(occurrences) < min_matches:
                continue
                
            # Perform time-offset analysis
            match_result = self._analyze_song_match(
                song_id, occurrences, len(query_hashes)
            )
            
            if match_result and match_result.confidence >= CONFIDENCE_THRESHOLD:
                match_results.append(match_result)
        
        # Step 3: Sort by confidence and return
        match_results.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"Found {len(match_results)} confident matches")
        return match_results
    
    def _analyze_song_match(self, song_id: int, occurrences: List[Dict], 
                           total_query_hashes: int) -> Optional[MatchResult]:
        """
        Analyze time-offset patterns for a candidate song.
        
        This implements the core Wang algorithm: find the most consistent
        time offset between query and database occurrences.
        
        Args:
            song_id: Candidate song ID
            occurrences: List of hash occurrences for this song
            total_query_hashes: Total number of query hashes
            
        Returns:
            MatchResult if confident match found, None otherwise
        """
        if len(occurrences) < MIN_MATCHING_HASHES:
            return None
        
        # Calculate time offsets between query and database
        time_offsets = []
        for occurrence in occurrences:
            # Time offset = database_time - query_time
            offset = occurrence['time_offset'] - occurrence['query_time']
            time_offsets.append(offset)
        
        # Find the most common time offset (temporal alignment)
        alignment_analysis = self._find_best_alignment(time_offsets)
        
        if not alignment_analysis:
            return None
        
        best_offset, aligned_count = alignment_analysis
        
        # Calculate confidence metrics
        confidence = self._calculate_confidence(
            aligned_count, len(occurrences), total_query_hashes
        )
        
        # Get song metadata
        song_metadata = self.database.get_song_metadata(song_id)
        if not song_metadata:
            logger.warning(f"No metadata found for song {song_id}")
            return None
        
        # Calculate alignment strength (how well aligned the matches are)
        alignment_strength = aligned_count / len(occurrences)
        
        return MatchResult(
            song_id=song_id,
            title=song_metadata['title'],
            artist=song_metadata['artist'],
            album=song_metadata.get('album'),
            confidence=confidence,
            matching_hashes=aligned_count,
            total_query_hashes=total_query_hashes,
            time_offset=best_offset,
            alignment_strength=alignment_strength
        )
    
    def _find_best_alignment(self, time_offsets: List[float]) -> Optional[Tuple[float, int]]:
        """
        Find the best temporal alignment using histogram analysis.
        
        Args:
            time_offsets: List of time offset values
            
        Returns:
            Tuple of (best_offset, count) or None if no good alignment
        """
        if not time_offsets:
            return None
        
        # Quantize time offsets to handle slight variations
        quantized_offsets = [
            round(offset / TIME_ALIGNMENT_TOLERANCE) * TIME_ALIGNMENT_TOLERANCE
            for offset in time_offsets
        ]
        
        # Count occurrences of each quantized offset
        offset_counts = Counter(quantized_offsets)
        
        # Find the most common offset
        best_offset, best_count = offset_counts.most_common(1)[0]
        
        # Require minimum alignment strength - relaxed for repetitive patterns
        alignment_ratio = best_count / len(time_offsets)
        unique_ratio = len(set(time_offsets)) / len(time_offsets)
        min_alignment = 0.05 if unique_ratio < 0.3 else 0.3  # Much lower for highly repetitive patterns
        if alignment_ratio < min_alignment:  # Adaptive threshold
            logger.debug(f"Alignment ratio {alignment_ratio:.3f} below threshold {min_alignment} (unique_ratio: {unique_ratio:.3f})")
            return None
        
        return best_offset, best_count
    
    def _calculate_confidence(self, aligned_count: int, total_matches: int, 
                             total_query_hashes: int) -> float:
        """
        Calculate confidence score for a match.
        
        Confidence combines:
        - Number of aligned hashes (strength of evidence)
        - Alignment consistency (ratio of aligned to total matches)
        - Coverage (ratio of matches to total query hashes)
        
        Args:
            aligned_count: Number of temporally aligned hashes
            total_matches: Total number of matching hashes
            total_query_hashes: Total number of query hashes
            
        Returns:
            Confidence score between 0 and 1
        """
        if total_matches == 0 or total_query_hashes == 0:
            return 0.0
        
        # Alignment strength: how well do the matches align temporally
        alignment_strength = aligned_count / total_matches
        
        # Coverage: how many query hashes found matches - but penalize over-duplication
        coverage = min(1.0, total_matches / total_query_hashes)
        
        # Raw strength: absolute number of aligned matches (log scale)
        raw_strength = min(1.0, np.log(aligned_count + 1) / np.log(20))  # Lower threshold
        
        # Bonus for having more unique hashes (reduce impact of duplication)
        unique_bonus = 1.0  # Default
        if total_matches > total_query_hashes:
            # Penalize excessive duplication
            unique_bonus = max(0.5, total_query_hashes / total_matches)
        
        # Combine metrics with weights
        confidence = (
            0.4 * alignment_strength +  # Temporal consistency
            0.3 * raw_strength +        # Absolute strength  
            0.2 * coverage +            # Query coverage
            0.1 * unique_bonus          # Uniqueness bonus
        )
        
        return min(1.0, confidence)
    
    def identify_best_match(self, query_hashes: List[AudioHash]) -> Optional[MatchResult]:
        """
        Identify the best matching song for query hashes.
        
        Args:
            query_hashes: List of query audio hashes
            
        Returns:
            Best match result or None if no confident match
        """
        matches = self.find_matches(query_hashes)
        
        if matches:
            best_match = matches[0]
            logger.info(f"Best match: '{best_match.title}' by {best_match.artist} "
                       f"(confidence: {best_match.confidence:.3f})")
            return best_match
        
        logger.info("No confident matches found")
        return None
    
    def get_match_details(self, match_result: MatchResult) -> Dict:
        """
        Get detailed information about a match result.
        
        Args:
            match_result: Match result to analyze
            
        Returns:
            Dictionary with detailed match information
        """
        return {
            'song_id': match_result.song_id,
            'title': match_result.title,
            'artist': match_result.artist,
            'album': match_result.album,
            'confidence': round(match_result.confidence, 3),
            'matching_hashes': match_result.matching_hashes,
            'total_query_hashes': match_result.total_query_hashes,
            'match_ratio': round(match_result.matching_hashes / match_result.total_query_hashes, 3),
            'time_offset': round(match_result.time_offset, 2),
            'alignment_strength': round(match_result.alignment_strength, 3),
            'confidence_level': self._get_confidence_level(match_result.confidence)
        }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get human-readable confidence level."""
        if confidence >= 0.8:
            return "Very High"
        elif confidence >= 0.6:
            return "High"
        elif confidence >= 0.4:
            return "Medium"
        elif confidence >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    def batch_identify(self, query_hash_batches: List[List[AudioHash]]) -> List[Optional[MatchResult]]:
        """
        Identify multiple queries in batch for efficiency.
        
        Args:
            query_hash_batches: List of query hash lists
            
        Returns:
            List of best match results (None for no matches)
        """
        results = []
        
        for i, query_hashes in enumerate(query_hash_batches):
            logger.debug(f"Processing batch query {i+1}/{len(query_hash_batches)}")
            best_match = self.identify_best_match(query_hashes)
            results.append(best_match)
        
        return results


def create_matcher(database: FingerprintDatabase) -> AudioMatcher:
    """
    Create an audio matcher with the given database.
    
    Args:
        database: Fingerprint database instance
        
    Returns:
        AudioMatcher instance
    """
    return AudioMatcher(database)
