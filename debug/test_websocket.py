#!/usr/bin/env python3
"""
Test WebSocket connection with Bearer token
"""
import asyncio
import websockets
import json

async def test_websocket_connection():
    """Test WebSocket connection with Bearer token"""

    # First get a token from the auth endpoint
    import urllib.request
    import urllib.parse

    print("🔄 Getting auth token...")

    # Prepare login data (correct format for ws-token endpoint)
    login_data = json.dumps({"username": "test-user"}).encode('utf-8')

    # Make login request
    req = urllib.request.Request(
        'http://localhost:8089/api/auth/ws-token',
        data=login_data,
        headers={
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:5173'
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            auth_response = json.loads(response.read().decode())
            token = auth_response['token']
            print(f"✅ Got token: {token[:20]}...")
    except Exception as e:
        print(f"❌ Failed to get token: {e}")
        return

    # Test WebSocket connection with Bearer token
    ws_url = "ws://localhost:8089/ws"
    subprotocol = f"Bearer.{token}"

    print(f"🔄 Testing WebSocket connection...")
    print(f"URL: {ws_url}")
    print(f"Subprotocol: Bearer.{token[:20]}...")

    try:
        async with websockets.connect(
            ws_url,
            subprotocols=[subprotocol]
        ) as websocket:
            print("✅ WebSocket connection established!")

            # Send a test message
            test_message = {
                "type": "ping",
                "sequence": 1
            }
            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent: {test_message}")

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"📥 Received: {response}")

            print("✅ WebSocket test successful!")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: {e}")
        print(f"Close code: {e.code}")
        print(f"Close reason: {e.reason}")
    except asyncio.TimeoutError:
        print("❌ WebSocket response timeout")
    except Exception as e:
        print(f"❌ WebSocket error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())