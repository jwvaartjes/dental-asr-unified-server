#!/usr/bin/env python3
"""
Diagnose differences between file upload vs streaming audio processing
"""

import asyncio
import io
import wave
import numpy as np
from pathlib import Path

async def analyze_audio_processing():
    """Analyze the differences between file and streaming audio processing"""

    print("🔍 AUDIO PROCESSING ANALYSIS")
    print("=" * 50)

    # Create test PCM data (what streaming would get)
    sample_rate = 16000
    duration = 2.0
    frames = int(duration * sample_rate)

    # Generate test audio similar to what microphone would capture
    t = np.linspace(0, duration, frames)
    audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
    pcm_data = (audio * 32767).astype(np.int16).tobytes()

    print(f"📊 Test Audio Properties:")
    print(f"   Sample rate: {sample_rate} Hz")
    print(f"   Duration: {duration}s")
    print(f"   PCM data size: {len(pcm_data)} bytes")

    # Method 1: Direct WAV creation (like file upload)
    direct_wav_buffer = io.BytesIO()
    with wave.open(direct_wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    direct_wav_data = direct_wav_buffer.getvalue()

    # Method 2: Streaming conversion (like AudioBuffer.convert_to_wav)
    streaming_wav_buffer = io.BytesIO()
    with wave.open(streaming_wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)      # 1 = mono
        wav_file.setsampwidth(2)      # 2 = 16-bit
        wav_file.setframerate(16000)  # 16000 Hz
        wav_file.writeframes(pcm_data) # Write PCM data
    streaming_wav_data = streaming_wav_buffer.getvalue()

    print(f"\n🔄 WAV Generation Comparison:")
    print(f"   Direct WAV size: {len(direct_wav_data)} bytes")
    print(f"   Streaming WAV size: {len(streaming_wav_data)} bytes")
    print(f"   Data identical: {direct_wav_data == streaming_wav_data}")

    if direct_wav_data == streaming_wav_data:
        print("   ✅ WAV generation is identical!")
    else:
        print("   ❌ WAV generation differs!")

    # Save both for manual inspection
    Path("/tmp/direct_test.wav").write_bytes(direct_wav_data)
    Path("/tmp/streaming_test.wav").write_bytes(streaming_wav_data)

    # Check potential issues with chunking
    print(f"\n📦 Chunk Size Analysis:")
    chunk_sizes = [2048, 4096, 8192, 16000]  # Different chunk sizes

    for chunk_size in chunk_sizes:
        # Simulate chunked processing
        chunks = []
        for i in range(0, len(pcm_data), chunk_size):
            chunk = pcm_data[i:i + chunk_size]
            chunks.append(chunk)

        # Recombine chunks (what streaming does)
        recombined = b''.join(chunks)

        chunk_duration_ms = (chunk_size / 2) / (sample_rate / 1000)
        print(f"   Chunk size: {chunk_size} bytes ({chunk_duration_ms:.1f}ms)")
        print(f"   Number of chunks: {len(chunks)}")
        print(f"   Recombined size: {len(recombined)} bytes")
        print(f"   Data preserved: {recombined == pcm_data}")

    print(f"\n💡 Potential Issues:")
    print(f"   1. Audio chunking causing boundary artifacts")
    print(f"   2. Frontend VAD removing speech portions")
    print(f"   3. Different OpenAI prompts being used")
    print(f"   4. Network timing affecting chunk assembly")

if __name__ == "__main__":
    asyncio.run(analyze_audio_processing())