#!/usr/bin/env python3
"""
Test streaming transcription functionality
"""
import asyncio
import websockets
import json
import base64
import os

async def test_streaming_transcription():
    """Test WebSocket streaming transcription"""
    try:
        print('🔄 Testing streaming transcription via WebSocket...')

        # Connect to WebSocket
        uri = 'ws://localhost:8089/ws'
        print(f'🔄 Connecting to WebSocket: {uri}')

        async with websockets.connect(uri) as websocket:
            print('✅ WebSocket connected successfully!')

            # Send identify message
            identify_msg = {
                'type': 'identify',
                'device_type': 'mobile'
            }
            await websocket.send(json.dumps(identify_msg))
            print('✅ Identify message sent')

            # Wait for identify response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f'✅ Received response: {response[:100]}...')

            # Create some dummy audio data (silence)
            sample_rate = 16000  # 16kHz
            duration_ms = 2000   # 2 seconds
            samples = int(sample_rate * duration_ms / 1000)

            # Create 16-bit PCM data (silence)
            audio_data = b'\\x00\\x00' * samples
            base64_audio = base64.b64encode(audio_data).decode('utf-8')

            print(f'🎵 Generated {len(audio_data)} bytes of test audio data')

            # Send audio chunk message
            audio_msg = {
                'type': 'audio_chunk',
                'audio_data': base64_audio,
                'format': 'pcm',
                'sample_rate': sample_rate,
                'channels': 1,
                'timestamp': asyncio.get_event_loop().time() * 1000
            }

            print('🎵 Sending audio chunk...')
            await websocket.send(json.dumps(audio_msg))
            print('✅ Audio chunk sent')

            # Wait for transcription result
            print('🔄 Waiting for transcription result...')
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    msg = json.loads(response)
                    print(f'📨 Received message: {msg.get("type")}')

                    if msg.get('type') == 'transcription_result':
                        print(f'🎯 Transcription result: {msg.get("text")}')
                        print(f'🎯 Raw text: {msg.get("raw")}')
                        print(f'🎯 Language: {msg.get("language")}')
                        print('✅ Streaming transcription test completed successfully!')
                        break
                    elif msg.get('type') == 'transcription_error':
                        print(f'❌ Transcription error: {msg.get("error")}')
                        break
                    elif msg.get('type') == 'error':
                        print(f'❌ WebSocket error: {msg.get("message")}')
                        break

            except asyncio.TimeoutError:
                print('⏰ Timeout waiting for transcription result')
                print('ℹ️  This might be expected with silence/dummy audio')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print('🧪 Testing Streaming Transcription')
    print('=' * 50)
    asyncio.run(test_streaming_transcription())