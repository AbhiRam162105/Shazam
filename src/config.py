"""
Configuration settings for the Shazam audio recognition system.
Based on Wang 2003 paper parameters and optimized for performance.
"""

# Audio Processing Parameters
SAMPLE_RATE = 22050  # Target sampling rate (Hz)
MONO = True          # Convert to mono audio

# Preprocessing Parameters  
FREQ_BAND_LOW = 300   # Lower frequency bound (Hz)
FREQ_BAND_HIGH = 2000 # Upper frequency bound (Hz)

# Spectrogram Parameters
FFT_WINDOW_SIZE = 2048    # FFT window size (samples)
HOP_LENGTH = 512          # Hop length between frames (samples)
OVERLAP_RATIO = 0.5       # Frame overlap ratio

# Peak Detection Parameters
PEAK_NEIGHBORHOOD_SIZE = 5   # Local peak detection radius (reduced)
PEAK_SORT = True            # Sort peaks by magnitude
MIN_PEAK_AMPLITUDE = 0.001   # Minimum peak amplitude threshold (very low for synthetic audio)

# Frequency Band Configuration (Wang 2003 approach)
# Divide frequency spectrum into logarithmic bands
FREQ_BANDS = [
    (300, 500),    # Low frequencies
    (500, 1000),   # Low-mid frequencies  
    (1000, 1500),  # Mid frequencies
    (1500, 2000),  # High-mid frequencies
]

# Hash Generation Parameters
HASH_TIME_DELTA_MIN = 1    # Minimum time delta for hash pairs (frames)
HASH_TIME_DELTA_MAX = 200  # Maximum time delta for hash pairs (frames)
TARGET_ZONE_SIZE = 5       # Number of target peaks per anchor
HASH_FAN_VALUE = 5         # Number of hash pairs per anchor peak

# Database Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_HASH_EXPIRY = 86400 * 30  # 30 days expiry for hashes

SQLITE_DB_PATH = 'data/shazam_metadata.db'

# Matching Parameters
MIN_MATCHING_HASHES = 3      # Minimum hashes for confident match (reduced)
TIME_ALIGNMENT_TOLERANCE = 5  # Tolerance for time alignment (frames) (increased)
CONFIDENCE_THRESHOLD = 0.05   # Minimum confidence score (reduced)

# Performance Parameters
MAX_WORKERS = 4              # Number of parallel workers
BATCH_SIZE = 1000           # Batch size for database operations
MAX_QUERY_DURATION = 30     # Maximum query audio duration (seconds)

# API Configuration
API_HOST = '0.0.0.0'
API_PORT = 5000
API_DEBUG = False

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# File Paths
DATA_DIR = 'data'
TEMP_DIR = 'temp'
AUDIO_FORMATS = ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac']

# System Limits
MAX_FINGERPRINTS_PER_TRACK = 10000  # Prevent memory issues
MAX_DATABASE_SIZE_GB = 10           # Maximum database size
