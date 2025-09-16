#!/usr/bin/env python3
"""
Test template service to verify the Supabase fix is working
"""
import asyncio
import requests
import websockets
import json

async def test_websocket_connection():
    """Test WebSocket connection to see if template service errors occur"""
    try:
        print('🔄 Testing WebSocket connection...')

        # Generate a token first
        print('🔄 Getting authentication token...')
        login_response = requests.post('http://localhost:8089/api/auth/login-magic', json={'email': 'test@example.com'})
        print(f'📋 Login response: {login_response.status_code}')

        if login_response.status_code == 200:
            token_response = requests.post('http://localhost:8089/api/auth/ws-token',
                                         cookies=login_response.cookies,
                                         json={'device_type': 'desktop'})
            print(f'📋 Token response: {token_response.status_code}')

            if token_response.status_code == 200:
                token = token_response.json()['token']
                print(f'✅ Got token: {token[:20]}...')

                # Test WebSocket connection
                uri = f'ws://localhost:8089/ws?token={token}'
                print(f'🔄 Connecting to WebSocket: {uri}')

                async with websockets.connect(uri) as websocket:
                    print('✅ WebSocket connected successfully!')
                    print('🔄 Sending identify message...')

                    # Send identify message
                    identify_msg = {
                        'type': 'identify',
                        'data': {'device_type': 'desktop'}
                    }
                    await websocket.send(json.dumps(identify_msg))
                    print('✅ Identify message sent')

                    # Wait for response
                    print('🔄 Waiting for response...')
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f'✅ Received response: {response[:100]}...')

                    print('✅ WebSocket test completed successfully!')
                    print('✅ Template service appears to be working (no errors in WebSocket connection)')

            else:
                print(f'❌ Failed to get token: {token_response.text}')

        else:
            print(f'❌ Failed to login: {login_response.text}')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

        # Check if it's a template service error
        if "supabase" in str(e).lower() or "template" in str(e).lower():
            print('❌ This appears to be a template service error - fix may not have taken effect')
        else:
            print('❓ This appears to be a different error')

if __name__ == "__main__":
    print('🧪 Testing Template Service Fix')
    print('=' * 50)
    asyncio.run(test_websocket_connection())