#!/usr/bin/env python3
"""
Debug script to check if the issue is in audio padding vs actual silent audio received.
"""

import numpy as np
import soundfile as sf
import sys
sys.path.append('src')

print("🔍 Debugging Audio Capture Issue")
print("=" * 50)

# Check the live_audio.wav file more thoroughly
audio_file = 'temp/live_audio.wav'

try:
    data, sr = sf.read(audio_file)
    print(f"📊 File: {audio_file}")
    print(f"   Duration: {len(data)/sr:.3f}s")
    print(f"   Samples: {len(data)}")
    print(f"   Sample Rate: {sr}")
    print()
    
    # Check for exactly where audio starts being silent
    print("🔍 Finding exact silent transitions:")
    
    chunk_size = sr // 10  # 0.1 second chunks
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        chunk_time = i / sr
        chunk_rms = np.sqrt(np.mean(chunk**2))
        
        if chunk_rms < 0.001:  # Very quiet
            print(f"   {chunk_time:.1f}s: RMS={chunk_rms:.6f} ❌ SILENT")
        else:
            print(f"   {chunk_time:.1f}s: RMS={chunk_rms:.6f} ✅")
    
    print()
    
    # Check if padding was applied (look for sudden drop to exactly zero)
    print("🧪 Checking for zero-padding pattern:")
    
    # Find first zero value
    zero_indices = np.where(data == 0.0)[0]
    if len(zero_indices) > 0:
        first_zero = zero_indices[0]
        first_zero_time = first_zero / sr
        
        print(f"   First zero at sample {first_zero} ({first_zero_time:.3f}s)")
        
        # Check if all values after first zero are also zero
        after_first_zero = data[first_zero:]
        all_zeros_after = np.all(after_first_zero == 0.0)
        
        if all_zeros_after:
            print(f"   ❌ ZERO PADDING detected from {first_zero_time:.3f}s onwards")
            print(f"   📏 Actual audio duration: {first_zero_time:.3f}s")
            print(f"   📏 Padded duration: {(len(data) - first_zero)/sr:.3f}s")
        else:
            print(f"   ✅ No systematic padding (zeros scattered throughout)")
    else:
        print(f"   ✅ No exact zeros found in audio")
    
    print()
    print("💡 Diagnosis:")
    if len(zero_indices) > 0 and first_zero_time < 4.5:
        print("   🔍 LIKELY CAUSE: Frontend not capturing full 5 seconds")
        print("   🔧 SOLUTION: Fix JavaScript audio collection timing")
    elif len(zero_indices) > 0:
        print("   🔍 LIKELY CAUSE: Minor timing issue in final audio chunks")
        print("   🔧 SOLUTION: Adjust frontend capture delay")
    else:
        print("   🔍 CAUSE: Audio present but very quiet")
        print("   🔧 SOLUTION: Check microphone or gain settings")

except Exception as e:
    print(f"❌ Error: {e}")
