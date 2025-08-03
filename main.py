#!/usr/bin/env python3
"""
Main CLI entry point for the Shazam system.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shazam_system import create_shazam_system


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Shazam-style audio recognition system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build database from music folder
  python main.py build /path/to/music/library

  # Identify song from audio file  
  python main.py identify song.wav

  # Live recognition from microphone
  python main.py live

  # Start REST API server
  python main.py api

  # Show database statistics
  python main.py stats
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build database command
    build_parser = subparsers.add_parser('build', help='Build fingerprint database')
    build_parser.add_argument('music_folder', help='Path to music library folder')
    build_parser.add_argument('--recursive', action='store_true', default=True,
                             help='Search subdirectories recursively')
    
    # Identify command
    identify_parser = subparsers.add_parser('identify', help='Identify song from audio file')
    identify_parser.add_argument('audio_file', help='Path to audio file')
    
    # Live recognition command
    live_parser = subparsers.add_parser('live', help='Live recognition from microphone')
    live_parser.add_argument('--duration', type=float, default=10.0,
                            help='Recording duration in seconds (default: 10)')
    
    # API server command
    api_parser = subparsers.add_parser('api', help='Start REST API server')
    api_parser.add_argument('--host', default='localhost', help='Host to bind to')
    api_parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    api_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Run performance benchmarks')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        if args.command == 'build':
            build_database(args.music_folder, args.recursive)
        elif args.command == 'identify':
            identify_song(args.audio_file)
        elif args.command == 'live':
            live_recognition(args.duration)
        elif args.command == 'api':
            start_api_server(args.host, args.port, args.debug)
        elif args.command == 'stats':
            show_stats()
        elif args.command == 'benchmark':
            run_benchmark()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def build_database(music_folder: str, recursive: bool):
    """Build fingerprint database from music folder."""
    music_path = Path(music_folder)
    
    if not music_path.exists():
        print(f"Error: Music folder does not exist: {music_folder}")
        sys.exit(1)
    
    print(f"Building database from: {music_path}")
    print("This may take a while for large music libraries...")
    
    shazam = create_shazam_system()
    
    try:
        stats = shazam.build_database_from_folder(music_path, recursive=recursive)
        
        print("\n" + "="*50)
        print("DATABASE BUILD COMPLETE")
        print("="*50)
        print(f"Processed: {stats['processed']} songs")
        print(f"Failed: {stats['failed']} songs")
        print(f"Skipped: {stats['skipped']} songs")
        
        db_stats = shazam.get_database_stats()
        print(f"\nTotal songs: {db_stats['total_songs']}")
        print(f"Total fingerprints: {db_stats['total_fingerprints']}")
        print(f"Total duration: {db_stats['total_duration_hours']:.1f} hours")
        
    finally:
        shazam.close()


def identify_song(audio_file: str):
    """Identify song from audio file."""
    audio_path = Path(audio_file)
    
    if not audio_path.exists():
        print(f"Error: Audio file does not exist: {audio_file}")
        sys.exit(1)
    
    print(f"Identifying: {audio_path}")
    
    shazam = create_shazam_system()
    
    try:
        result = shazam.identify_audio_file(audio_path)
        
        if result:
            print(f"\n🎵 MATCH FOUND!")
            print(f"Title: {result.title}")
            print(f"Artist: {result.artist}")
            if result.album:
                print(f"Album: {result.album}")
            print(f"Confidence: {result.confidence:.3f}")
        else:
            print(f"\n❌ No match found")
            
    finally:
        shazam.close()


def live_recognition(duration: float):
    """Live recognition from microphone."""
    print(f"🎤 Live recognition (recording {duration}s)")
    
    shazam = create_shazam_system()
    
    try:
        result = shazam.identify_from_microphone(duration=duration)
        
        if result:
            print(f"\n🎵 IDENTIFIED: '{result.title}' by {result.artist}")
            print(f"Confidence: {result.confidence:.3f}")
        else:
            print(f"\n❌ No match found")
            
    finally:
        shazam.close()


def start_api_server(host: str, port: int, debug: bool):
    """Start REST API server."""
    print(f"Starting API server on {host}:{port}")
    
    from api import run_api_server
    run_api_server(host=host, port=port, debug=debug)


def show_stats():
    """Show database statistics."""
    shazam = create_shazam_system()
    
    try:
        stats = shazam.get_database_stats()
        system_info = shazam.get_system_info()
        
        print("📊 SHAZAM DATABASE STATISTICS")
        print("=" * 40)
        print(f"Total songs: {stats['total_songs']}")
        print(f"Total fingerprints: {stats['total_fingerprints']}")
        print(f"Total duration: {stats['total_duration_hours']:.1f} hours")
        print(f"Redis memory used: {stats.get('redis_memory_used', 'N/A')}")
        print(f"Redis keys: {stats.get('redis_keys', 0)}")
        
        print("\n🔧 SYSTEM CONFIGURATION")
        print("=" * 40)
        print(f"Sample rate: {system_info['sample_rate']} Hz")
        print(f"FFT window: {system_info['fingerprinter']['n_fft']}")
        print(f"Hop length: {system_info['fingerprinter']['hop_length']}")
        print(f"Frequency bands: {system_info['fingerprinter']['freq_bands']}")
        
    finally:
        shazam.close()


def run_benchmark():
    """Run performance benchmarks."""
    from tests.benchmark import main as benchmark_main
    benchmark_main()


if __name__ == "__main__":
    main()
