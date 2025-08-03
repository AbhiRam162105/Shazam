"""
Benchmark script for Shazam performance testing.
"""

import time
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shazam_system import create_shazam_system
from fingerprinting import AudioFingerprinter


def generate_test_audio(duration: float = 10.0, sample_rate: int = 22050) -> np.ndarray:
    """Generate test audio signal."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a complex signal with multiple frequencies
    audio = (np.sin(2 * np.pi * 440 * t) +  # A4
             0.5 * np.sin(2 * np.pi * 880 * t) +  # A5
             0.3 * np.sin(2 * np.pi * 1320 * t))  # E6
    
    # Add some noise
    noise = np.random.randn(len(audio)) * 0.05
    audio = audio + noise
    
    # Normalize
    audio = audio / np.max(np.abs(audio))
    
    return audio


def benchmark_fingerprinting():
    """Benchmark fingerprinting performance."""
    print("🔬 FINGERPRINTING BENCHMARK")
    print("=" * 50)
    
    fingerprinter = AudioFingerprinter()
    durations = [1, 5, 10, 30, 60]  # Test different durations
    
    results = []
    
    for duration in durations:
        print(f"\nTesting {duration}s audio...")
        
        # Generate test audio
        audio = generate_test_audio(duration)
        
        # Benchmark fingerprinting
        start_time = time.time()
        hashes = fingerprinter.fingerprint_audio(audio)
        end_time = time.time()
        
        processing_time = end_time - start_time
        hash_rate = len(hashes) / duration if duration > 0 else 0
        real_time_factor = duration / processing_time if processing_time > 0 else float('inf')
        
        result = {
            'duration': duration,
            'hashes': len(hashes),
            'processing_time': processing_time,
            'hash_rate': hash_rate,
            'real_time_factor': real_time_factor
        }
        results.append(result)
        
        print(f"  Generated: {len(hashes)} hashes")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Hash rate: {hash_rate:.1f} hashes/sec")
        print(f"  Real-time factor: {real_time_factor:.1f}x")
    
    # Summary
    print("\n📊 FINGERPRINTING SUMMARY")
    print("-" * 50)
    avg_hash_rate = np.mean([r['hash_rate'] for r in results])
    avg_rt_factor = np.mean([r['real_time_factor'] for r in results])
    
    print(f"Average hash rate: {avg_hash_rate:.1f} hashes/sec")
    print(f"Average real-time factor: {avg_rt_factor:.1f}x")
    
    return results


def benchmark_matching():
    """Benchmark matching performance."""
    print("\n🎯 MATCHING BENCHMARK")
    print("=" * 50)
    
    try:
        shazam = create_shazam_system()
        
        # Check if database has songs
        db_stats = shazam.get_database_stats()
        if db_stats['total_songs'] == 0:
            print("⚠️  No songs in database - skipping matching benchmark")
            print("   Run build_database.py first to add songs")
            return []
        
        print(f"Database: {db_stats['total_songs']} songs, {db_stats['total_fingerprints']} fingerprints")
        
        # Test different query lengths
        query_durations = [5, 10, 15, 20]
        results = []
        
        for duration in query_durations:
            print(f"\nTesting {duration}s query...")
            
            # Generate test query
            query_audio = generate_test_audio(duration)
            
            # Benchmark identification
            start_time = time.time()
            match_result = shazam.identify_audio_file = lambda x: shazam.matcher.identify_best_match(
                shazam.fingerprinter.fingerprint_audio(query_audio)
            )
            result = match_result(None)  # Use lambda result
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            result_data = {
                'duration': duration,
                'processing_time': processing_time,
                'found_match': result is not None,
                'confidence': result.confidence if result else 0.0
            }
            results.append(result_data)
            
            if result:
                print(f"  Match found: {result.title} (confidence: {result.confidence:.3f})")
            else:
                print(f"  No match found")
            print(f"  Search time: {processing_time:.3f}s")
        
        # Summary
        print("\n📊 MATCHING SUMMARY")
        print("-" * 50)
        avg_search_time = np.mean([r['processing_time'] for r in results])
        match_rate = np.mean([r['found_match'] for r in results]) * 100
        
        print(f"Average search time: {avg_search_time:.3f}s")
        print(f"Match rate: {match_rate:.1f}%")
        
        shazam.close()
        return results
        
    except Exception as e:
        print(f"Matching benchmark failed: {e}")
        return []


def benchmark_database_operations():
    """Benchmark database operations."""
    print("\n💾 DATABASE BENCHMARK")
    print("=" * 50)
    
    try:
        shazam = create_shazam_system()
        
        # Test adding a song
        test_audio = generate_test_audio(10.0)
        
        print("Testing song addition...")
        start_time = time.time()
        
        # Create temporary file
        import tempfile
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            sf.write(temp_file.name, test_audio, 22050)
            temp_path = temp_file.name
        
        try:
            song_id = shazam.add_song_to_database(
                audio_file=temp_path,
                title="Benchmark Test Song",
                artist="Test Artist"
            )
            end_time = time.time()
            
            if song_id:
                processing_time = end_time - start_time
                print(f"  Song added successfully in {processing_time:.3f}s")
                
                # Clean up test song
                shazam.database.remove_song(song_id)
                print(f"  Test song removed")
            else:
                print(f"  Failed to add test song")
                
        finally:
            import os
            os.unlink(temp_path)
        
        # Test database stats
        print("\nTesting database statistics...")
        start_time = time.time()
        stats = shazam.get_database_stats()
        end_time = time.time()
        
        print(f"  Stats retrieved in {(end_time - start_time)*1000:.1f}ms")
        print(f"  Total songs: {stats['total_songs']}")
        
        shazam.close()
        
    except Exception as e:
        print(f"Database benchmark failed: {e}")


def main():
    """Run all benchmarks."""
    print("🚀 SHAZAM PERFORMANCE BENCHMARK")
    print("=" * 60)
    print("This will test the performance of the Shazam system components.")
    print()
    
    # Run benchmarks
    try:
        fingerprint_results = benchmark_fingerprinting()
        matching_results = benchmark_matching()
        benchmark_database_operations()
        
        print("\n✅ BENCHMARK COMPLETE")
        print("=" * 60)
        
        # Overall assessment
        if fingerprint_results:
            avg_rt_factor = np.mean([r['real_time_factor'] for r in fingerprint_results])
            if avg_rt_factor >= 10:
                print("🟢 Fingerprinting: EXCELLENT (>10x real-time)")
            elif avg_rt_factor >= 5:
                print("🟡 Fingerprinting: GOOD (>5x real-time)")
            else:
                print("🔴 Fingerprinting: SLOW (<5x real-time)")
        
        if matching_results:
            avg_search_time = np.mean([r['processing_time'] for r in matching_results])
            if avg_search_time <= 1.0:
                print("🟢 Matching: EXCELLENT (<1s search)")
            elif avg_search_time <= 3.0:
                print("🟡 Matching: GOOD (<3s search)")
            else:
                print("🔴 Matching: SLOW (>3s search)")
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"Benchmark failed: {e}")


if __name__ == "__main__":
    main()
