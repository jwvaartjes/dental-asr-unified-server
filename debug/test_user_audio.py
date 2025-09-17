#!/usr/bin/env python3
"""
Test your specific audio file transcription
"""
import requests
import base64
import json

def test_audio_file():
    """Test transcription of user's audio file"""
    audio_file_path = "/Users/janwillemvaartjes/Downloads/opname-2025-09-16T16-18-09.wav"

    try:
        print("🎤 Testing your audio file transcription")
        print("=" * 50)

        # Read the audio file
        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()

        print(f"📁 Loaded audio file: {len(audio_data)} bytes")

        # Convert to base64
        base64_audio = base64.b64encode(audio_data).decode('utf-8')
        print(f"📤 Converted to base64: {len(base64_audio)} characters")

        # Test direct API call (no auth needed for basic transcription)
        url = "http://localhost:8089/api/ai/transcribe"
        payload = {
            "audio_data": base64_audio,
            "language": "nl",
            "prompt": "Dutch dental terminology"
        }

        print("📡 Sending to transcription API...")
        response = requests.post(url, json=payload, timeout=30)

        print(f"📊 Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"📝 Transcribed text: {result.get('text', 'No text')}")
            print(f"🎯 Raw text: {result.get('raw', 'No raw')}")
            print(f"🌍 Language: {result.get('language', 'No language')}")
            print(f"⏱️ Duration: {result.get('duration', 'No duration')}s")
        else:
            print(f"❌ Error {response.status_code}")
            print(f"📝 Response: {response.text}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_file()