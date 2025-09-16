#!/usr/bin/env python3
"""
Debug script to compare file upload vs streaming transcription quality.
Tests the same audio data through both endpoints to identify quality differences.
"""

import asyncio
import base64
import io
import json
import aiohttp
import aiofiles
from pathlib import Path

async def test_transcription_quality():
    """Test identical audio through both endpoints"""

    # Test audio file (use your perfect WAV file)
    test_file = "test_audio.wav"  # Replace with your working WAV file path

    if not Path(test_file).exists():
        print("❌ Test audio file not found. Please provide the WAV file that works perfectly.")
        print("Usage: Place your working WAV file as 'test_audio.wav' in this directory")
        return

    base_url = "http://localhost:8089/api"

    async with aiohttp.ClientSession() as session:
        print("🎯 TRANSCRIPTION QUALITY COMPARISON")
        print("=" * 50)

        # Test 1: File Upload (your perfect method)
        print("\n📁 Testing FILE UPLOAD (perfect quality)...")
        async with aiofiles.open(test_file, 'rb') as f:
            file_content = await f.read()

        data = aiohttp.FormData()
        data.add_field('file', file_content, filename='test.wav', content_type='audio/wav')
        data.add_field('language', 'nl')

        async with session.post(f"{base_url}/ai/transcribe-file", data=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                file_result = result.get('text', 'No text')
                print(f"✅ File Upload Result: '{file_result}'")
                print(f"📏 Length: {len(file_result)} characters")
            else:
                print(f"❌ File upload failed: {resp.status}")
                return

        # Test 2: Streaming (base64 encoded)
        print("\n🌊 Testing STREAMING (poor quality)...")

        # Encode same audio as base64 (exactly like streaming does)
        base64_audio = base64.b64encode(file_content).decode('utf-8')

        streaming_payload = {
            "audio_data": base64_audio,
            "language": "nl",
            "format": "wav"
        }

        async with session.post(f"{base_url}/ai/transcribe",
                               json=streaming_payload,
                               headers={'Content-Type': 'application/json'}) as resp:
            if resp.status == 200:
                result = await resp.json()
                streaming_raw = result.get('raw', 'No raw')
                streaming_normalized = result.get('text', 'No text')
                print(f"✅ Streaming Raw Result: '{streaming_raw}'")
                print(f"✅ Streaming Normalized: '{streaming_normalized}'")
                print(f"📏 Raw Length: {len(streaming_raw)} characters")
                print(f"📏 Normalized Length: {len(streaming_normalized)} characters")
            else:
                error = await resp.text()
                print(f"❌ Streaming failed: {resp.status} - {error}")
                return

        # Analysis
        print("\n🔍 QUALITY ANALYSIS")
        print("=" * 30)
        print(f"File Upload (perfect): '{file_result}'")
        print(f"Streaming Raw:         '{streaming_raw}'")
        print(f"Streaming Normalized:  '{streaming_normalized}'")

        # Check if base64 encoding corrupted the audio
        print(f"\n📊 TECHNICAL DETAILS")
        print(f"Original file size: {len(file_content):,} bytes")
        print(f"Base64 encoded size: {len(base64_audio):,} characters")
        print(f"Base64 overhead: {(len(base64_audio) * 3/4 - len(file_content))} bytes")

        # Test base64 round-trip integrity
        decoded_audio = base64.b64decode(base64_audio)
        if decoded_audio == file_content:
            print("✅ Base64 encoding/decoding is perfect - no corruption")
        else:
            print("❌ Base64 corruption detected!")
            print(f"   Original: {len(file_content)} bytes")
            print(f"   Decoded:  {len(decoded_audio)} bytes")

        # Quality comparison
        if file_result.lower() == streaming_raw.lower():
            print("✅ Raw transcription quality is IDENTICAL")
            if streaming_normalized != streaming_raw:
                print("⚠️  Issue is in NORMALIZATION pipeline")
            else:
                print("✅ No normalization issues")
        else:
            print("❌ OpenAI transcription quality differs between endpoints!")
            print("   This suggests audio data corruption or different processing")

if __name__ == "__main__":
    asyncio.run(test_transcription_quality())