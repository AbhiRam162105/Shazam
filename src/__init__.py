"""
Shazam Audio Recognition System
"""

from .shazam_system import ShazamSystem, create_shazam_system
from .audio_processing import AudioProcessor
from .fingerprinting import AudioFingerprinter, create_fingerprint
from .database import FingerprintDatabase, get_database
from .matching import AudioMatcher, MatchResult
from .api import create_app, run_api_server

__version__ = "1.0.0"
__author__ = "Shazam Implementation"

__all__ = [
    'ShazamSystem',
    'create_shazam_system',
    'AudioProcessor', 
    'AudioFingerprinter',
    'create_fingerprint',
    'FingerprintDatabase',
    'get_database',
    'AudioMatcher',
    'MatchResult',
    'create_app',
    'run_api_server'
]
