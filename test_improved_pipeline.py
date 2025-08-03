#!/usr/bin/env python3
"""
Test the improved audio processing pipeline.
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_improved_pipeline():
    """Test the improved audio processing with gain and limiting."""
    
    print("Testing improved audio processing pipeline...")
    
    # Load the existing live_audio.wav to see current levels
    live_audio_path = "temp/live_audio.wav"
    
    if Path(live_audio_path).exists():
        original_audio, sr = sf.read(live_audio_path)
        print(f"\nOriginal audio (from live_audio.wav):")
        print(f"  RMS: {np.sqrt(np.mean(original_audio**2)):.6f}")
        print(f"  Peak: {np.max(np.abs(original_audio)):.6f}")
        
        # Simulate the improved processing pipeline
        audio_data = original_audio.copy()
        
        # Check current level and apply gain
        rms_level = np.sqrt(np.mean(audio_data**2))
        if rms_level > 0:
            target_rms = 0.15  # Target RMS level
            gain = min(target_rms / rms_level, 15.0)  # Max 15x gain
            audio_data = audio_data * gain
            print(f"\nAfter initial gain ({gain:.2f}x):")
            print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")
            print(f"  Peak: {np.max(np.abs(audio_data)):.6f}")
        
        # Apply additional boost if still too quiet
        rms = np.sqrt(np.mean(audio_data**2))
        if rms < 0.1:
            boost_gain = min(0.15 / rms, 8.0)
            audio_data = audio_data * boost_gain
            print(f"\nAfter boost gain ({boost_gain:.2f}x):")
            print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")
            print(f"  Peak: {np.max(np.abs(audio_data)):.6f}")
            rms = np.sqrt(np.mean(audio_data**2))
        
        # Apply soft limiter
        peak_level = np.max(np.abs(audio_data))
        if peak_level > 0.95:
            threshold = 0.8
            ratio = 4.0
            
            over_threshold = np.abs(audio_data) > threshold
            
            if np.any(over_threshold):
                signs = np.sign(audio_data)
                abs_audio = np.abs(audio_data)
                
                compressed = np.where(
                    over_threshold,
                    threshold + (abs_audio - threshold) / ratio,
                    abs_audio
                )
                
                audio_data = signs * compressed
                print(f"\nAfter soft limiting:")
                print(f"  RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")
                print(f"  Peak: {np.max(np.abs(audio_data)):.6f}")
                rms = np.sqrt(np.mean(audio_data**2))
        
        # Final assessment
        print(f"\n=== FINAL RESULT ===")
        print(f"RMS improvement: {rms/np.sqrt(np.mean(original_audio**2)):.1f}x")
        
        if rms >= 0.1:
            print("✅ Audio level is now excellent for recognition")
        elif rms >= 0.05:
            print("✅ Audio level is now good for recognition")
        elif rms >= 0.02:
            print("⚠️  Audio level is improved but still marginal")
        else:
            print("❌ Audio level is still too low")
        
        # Save the processed audio for comparison
        output_path = "temp/processed_live_audio.wav"
        sf.write(output_path, audio_data, sr)
        print(f"\nSaved processed audio to: {output_path}")
        
        return audio_data
    else:
        print("❌ No live_audio.wav found to test with")
        return None

if __name__ == "__main__":
    test_improved_pipeline()
