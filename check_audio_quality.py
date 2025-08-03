#!/usr/bin/env python3
"""
Analyze the live_audio.wav file to check for silent endings and verify full capture.
"""

import numpy as np
import soundfile as sf
import librosa
import os

audio_file = 'temp/live_audio.wav'

if os.path.exists(audio_file):
    print(f'🎵 Analyzing audio file: {audio_file}')
    print('=' * 60)
    
    # Load with soundfile first
    try:
        data, sr = sf.read(audio_file)
        print(f'📊 Basic Info:')
        print(f'   Duration: {len(data) / sr:.3f} seconds')
        print(f'   Sample Rate: {sr} Hz')
        print(f'   Samples: {len(data)}')
        print(f'   Channels: {data.shape[1] if len(data.shape) > 1 else 1}')
        print()
        
        # Convert to mono if needed
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Analyze audio levels throughout the recording
        print('🔊 Audio Level Analysis (RMS by second):')
        duration = len(data) / sr
        
        for second in range(int(duration) + 1):
            start_sample = int(second * sr)
            end_sample = min(int((second + 1) * sr), len(data))
            
            if start_sample < len(data):
                segment = data[start_sample:end_sample]
                if len(segment) > 0:
                    rms = np.sqrt(np.mean(segment**2))
                    peak = np.max(np.abs(segment))
                    segment_duration = len(segment) / sr
                    
                    status = '✅' if rms > 0.01 else '❌ SILENT'
                    print(f'   Second {second}: RMS={rms:.4f}, Peak={peak:.4f}, Duration={segment_duration:.3f}s {status}')
        
        print()
        
        # Check for silent endings
        print('🔍 Silent Ending Detection:')
        
        # Check last 1 second
        last_second_samples = int(sr)
        if len(data) >= last_second_samples:
            last_second = data[-last_second_samples:]
            last_rms = np.sqrt(np.mean(last_second**2))
            print(f'   Last 1 second RMS: {last_rms:.4f}')
            
            if last_rms < 0.005:  # Very quiet threshold
                print('   ❌ SILENT ENDING DETECTED in last second')
            else:
                print('   ✅ Audio present in last second')
        
        # Check last 0.5 seconds
        last_half_samples = int(sr * 0.5)
        if len(data) >= last_half_samples:
            last_half = data[-last_half_samples:]
            last_half_rms = np.sqrt(np.mean(last_half**2))
            print(f'   Last 0.5 second RMS: {last_half_rms:.4f}')
            
            if last_half_rms < 0.005:
                print('   ❌ SILENT ENDING DETECTED in last 0.5 seconds')
            else:
                print('   ✅ Audio present in last 0.5 seconds')
        
        print()
        
        # Overall statistics
        overall_rms = np.sqrt(np.mean(data**2))
        overall_peak = np.max(np.abs(data))
        
        print('📈 Overall Statistics:')
        print(f'   Overall RMS: {overall_rms:.4f}')
        print(f'   Overall Peak: {overall_peak:.4f}')
        print(f'   Dynamic Range: {20 * np.log10(overall_peak / max(overall_rms, 1e-10)):.1f} dB')
        
        # Check if audio meets quality thresholds
        print()
        print('✅ Quality Assessment:')
        if duration >= 4.8:  # At least 4.8 seconds
            print(f'   ✅ Duration OK: {duration:.3f}s (≥4.8s required)')
        else:
            print(f'   ❌ Duration too short: {duration:.3f}s (<4.8s)')
            
        if overall_rms >= 0.05:  # Decent audio level
            print(f'   ✅ Audio level OK: {overall_rms:.4f} (≥0.05 required)')
        else:
            print(f'   ⚠️  Audio level low: {overall_rms:.4f} (<0.05)')
            
        if last_rms >= 0.01:  # No silent ending
            print(f'   ✅ No silent ending: {last_rms:.4f} (≥0.01 in last second)')
        else:
            print(f'   ❌ Silent ending detected: {last_rms:.4f} (<0.01 in last second)')
        
    except Exception as e:
        print(f'❌ Error analyzing audio: {e}')
        
else:
    print(f'❌ Audio file not found: {audio_file}')
    print('   Make sure to record audio through the web interface first')
