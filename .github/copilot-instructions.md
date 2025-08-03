<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Shazam Audio Fingerprinting System

This is a Python implementation of the Wang 2003 "Industrial-Strength Audio Search Algorithm" used by Shazam for audio recognition.

## Key Technical Concepts:

### Audio Fingerprinting Algorithm (Wang 2003)
- **Constellation Mapping**: Extract spectral peaks from spectrogram to create sparse feature points
- **Combinatorial Hashing**: Generate hashes from anchor-target peak pairs with time deltas
- **Inverted Index**: Map each hash to list of (song_id, time_offset) tuples for fast lookup
- **Time-Offset Clustering**: Match queries by finding consistent time alignment patterns

### System Architecture
- **Audio Processing**: librosa for loading, NumPy/SciPy for signal processing
- **Fingerprint Database**: Redis for hash index, SQLite for metadata
- **Matching Pipeline**: Real-time query processing with sub-second response
- **Scalability**: Designed for millions of tracks with horizontal scaling

### Performance Targets
- **Speed**: <1 second identification time
- **Accuracy**: >95% clean audio, >85% with noise/distortion
- **Robustness**: Handle compression, EQ, background noise, pitch shifts
- **Throughput**: ~20-50 fingerprint hashes per second of audio

## Code Style Guidelines:
- Use type hints for all function signatures
- Document complex algorithms with references to Wang paper
- Optimize for both accuracy and performance
- Include comprehensive error handling
- Write unit tests for core fingerprinting functions

## Key Files:
- `fingerprinting.py`: Core peak detection and hashing algorithms
- `matching.py`: Time-offset clustering and confidence scoring
- `database.py`: Redis/SQLite interfaces with proper indexing
- `shazam_system.py`: Main orchestrator tying all components together
