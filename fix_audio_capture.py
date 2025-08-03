#!/usr/bin/env python3
"""
Alternative approach: Try using MediaRecorder instead of ScriptProcessor for more reliable audio capture.
This creates a patch for the HTML file.
"""

print("🔧 Creating MediaRecorder-based Audio Capture Fix")
print("=" * 60)

# Read the current HTML file
with open('templates/index.html', 'r') as f:
    content = f.read()

# Find the problematic audio capture section and replace it
old_section_start = content.find('// Create a ScriptProcessor for raw audio data capture')
old_section_end = content.find('socket.emit(\'start_recording\');')

if old_section_start != -1 and old_section_end != -1:
    print("✅ Found problematic ScriptProcessor section")
    
    # Extract the parts before and after
    before = content[:old_section_start]
    after = content[old_section_end:]
    
    # New MediaRecorder-based implementation
    new_section = '''// Use MediaRecorder for more reliable audio capture
                let audioBuffer = [];
                const recordingStartTime = Date.now();
                let recordingComplete = false;
                let mediaRecorderInstance;

                // Ensure audio stream tracks stay active
                audioStream.getTracks().forEach(track => {
                    track.enabled = true;
                    console.log(`[STREAM] Track state: ${track.readyState}, enabled: ${track.enabled}`);
                });

                // Set up MediaRecorder for continuous audio capture
                try {
                    mediaRecorderInstance = new MediaRecorder(audioStream, {
                        mimeType: 'audio/webm;codecs=pcm',
                        audioBitsPerSecond: 128000
                    });
                } catch (e) {
                    // Fallback to default format
                    mediaRecorderInstance = new MediaRecorder(audioStream);
                }

                const audioChunks = [];

                mediaRecorderInstance.ondataavailable = function(event) {
                    const elapsed = Date.now() - recordingStartTime;
                    
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                        console.log(`[MEDIA] ${elapsed}ms: Received chunk ${audioChunks.length}, size: ${event.data.size} bytes`);
                    }
                };

                mediaRecorderInstance.onstop = function() {
                    console.log('[MEDIA] Recording stopped, processing chunks...');
                    
                    if (audioChunks.length > 0) {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        console.log(`[MEDIA] Created blob: ${audioBlob.size} bytes`);
                        
                        // Convert blob to audio buffer for processing
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const arrayBuffer = e.target.result;
                            audioContext.decodeAudioData(arrayBuffer)
                                .then(decodedData => {
                                    const audioData = decodedData.getChannelData(0);
                                    console.log(`[MEDIA] Decoded ${audioData.length} samples, duration: ${decodedData.duration.toFixed(3)}s`);
                                    
                                    // Send this audio data for processing
                                    processMediaRecorderAudio(audioData);
                                })
                                .catch(err => {
                                    console.error('[MEDIA] Error decoding audio:', err);
                                    // Fallback to timer-based capture if MediaRecorder fails
                                    fallbackToTimerCapture();
                                });
                        };
                        reader.readAsArrayBuffer(audioBlob);
                    }
                };

                // Start MediaRecorder with frequent data events
                mediaRecorderInstance.start(100); // Request data every 100ms
                
                // Backup timer to ensure we stop after 5 seconds
                setTimeout(() => {
                    if (mediaRecorderInstance && mediaRecorderInstance.state === 'recording') {
                        console.log('[TIMER] 5 seconds reached, stopping MediaRecorder');
                        mediaRecorderInstance.stop();
                    }
                }, 5200); // 5.2 seconds to ensure we get full 5 seconds

                // Fallback function using analyser if MediaRecorder fails
                function fallbackToTimerCapture() {
                    console.log('[FALLBACK] Using timer-based audio capture');
                    
                    let audioBuffer = [];
                    let captureInterval;
                    
                    function captureAudioChunk() {
                        if (!isListening) return;
                        
                        const bufferLength = analyser.frequencyBinCount;
                        const dataArray = new Float32Array(bufferLength);
                        analyser.getFloatTimeDomainData(dataArray);
                        
                        audioBuffer.push(new Float32Array(dataArray));
                        
                        const elapsed = Date.now() - recordingStartTime;
                        if (elapsed >= 5000) {
                            clearInterval(captureInterval);
                            processTimerAudio(audioBuffer);
                        }
                    }
                    
                    captureInterval = setInterval(captureAudioChunk, 20); // 50Hz
                }

                function processMediaRecorderAudio(audioData) {
                    console.log('Processing MediaRecorder audio data');
                    sendRawAudioData(audioData);
                }

                function processTimerAudio(audioBuffer) {
                    console.log('Processing timer-captured audio data');
                    // Concatenate audio chunks
                    const totalLength = audioBuffer.reduce((sum, chunk) => sum + chunk.length, 0);
                    const concatenated = new Float32Array(totalLength);
                    let offset = 0;
                    for (const chunk of audioBuffer) {
                        concatenated.set(chunk, offset);
                        offset += chunk.length;
                    }
                    sendRawAudioData(concatenated);
                }

                '''
    
    # Combine the parts
    new_content = before + new_section + after
    
    # Write the updated file
    with open('templates/index.html', 'w') as f:
        f.write(new_content)
    
    print("✅ Updated HTML file with MediaRecorder-based audio capture")
    print("📊 Changes made:")
    print("   - Replaced deprecated ScriptProcessor with MediaRecorder")
    print("   - Added fallback timer-based capture")
    print("   - Improved audio data handling")
    print("   - Better error handling and logging")
    
else:
    print("❌ Could not find the section to replace")
    print("   Manual editing may be required")

print("\n🧪 Testing Instructions:")
print("1. Start web interface: python web_interface.py")
print("2. Test recording - should now capture full 5 seconds")
print("3. Check browser console for [MEDIA] messages")
print("4. Run: python debug_audio_capture.py to verify")
