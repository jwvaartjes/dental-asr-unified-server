#!/usr/bin/env python3
"""
Test mobile auth inheritance from desktop via pairing
"""

import asyncio
import json
import requests
import sys
from datetime import datetime

def test_mobile_auth_inheritance():
    """Test complete flow: desktop generates code -> mobile inherits auth"""

    print("🧪 Testing Mobile Auth Inheritance Flow")
    print("=" * 50)

    base_url = "http://localhost:8089"

    # Step 1: Desktop generates WebSocket token
    print("\n📱 Step 1: Desktop gets WebSocket token...")
    try:
        desktop_token_response = requests.post(
            f"{base_url}/api/auth/ws-token",
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:5173"
            },
            json={"username": "desktop_user_123"}
        )

        if desktop_token_response.status_code == 200:
            desktop_token_data = desktop_token_response.json()
            print(f"✅ Desktop token received for user: desktop_user_123")
        else:
            print(f"❌ Desktop token failed: {desktop_token_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Desktop token error: {e}")
        return

    # Step 2: Desktop generates pairing code
    print("\n🔐 Step 2: Desktop generates pairing code...")
    try:
        pairing_response = requests.post(
            f"{base_url}/api/generate-pair-code",
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:5173",
                # Try with Authorization header to pass desktop auth
                "Authorization": f"Bearer {desktop_token_data['token']}"
            },
            json={"desktop_session_id": "desktop-session-inheritance-test"}
        )

        if pairing_response.status_code == 200:
            pairing_data = pairing_response.json()
            pair_code = pairing_data["code"]
            print(f"✅ Pairing code generated: {pair_code}")
            print(f"   Channel: {pairing_data['channel_id']}")
            print(f"   Expires: {pairing_data['expires_at']}")
        else:
            print(f"❌ Pairing code generation failed: {pairing_response.status_code}")
            print(f"   Response: {pairing_response.text}")
            return
    except Exception as e:
        print(f"❌ Pairing code error: {e}")
        return

    # Step 3: Mobile tries to inherit auth via pairing code
    print("\n📲 Step 3: Mobile tries to inherit desktop auth...")
    try:
        mobile_token_response = requests.post(
            f"{base_url}/api/auth/ws-token-mobile",
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:5173"
            },
            json={
                "pair_code": pair_code,
                "username": "fallback_mobile_user"
            }
        )

        if mobile_token_response.status_code == 200:
            mobile_token_data = mobile_token_response.json()
            print(f"✅ Mobile token received!")
            print(f"   Token expires in: {mobile_token_data.get('expires_in', 'unknown')} seconds")

            # Check if auth was inherited
            if "inherited_from" in mobile_token_data:
                print(f"🎉 SUCCESS: Mobile inherited auth from: {mobile_token_data['inherited_from']}")
                print(f"   Pairing code used: {mobile_token_data.get('pairing_code', 'unknown')}")

                # Verify token contents
                import jwt
                try:
                    # Decode without verification to see contents (for testing only)
                    payload = jwt.decode(mobile_token_data['token'], options={"verify_signature": False})
                    print(f"   Mobile token user: {payload.get('user', 'unknown')}")
                    print(f"   Mobile token device_type: {payload.get('device_type', 'unknown')}")

                    if payload.get('user') == 'desktop_user_123':
                        print("✅ PERFECT: Mobile token contains desktop user info!")
                    else:
                        print(f"⚠️  Mobile token user ({payload.get('user')}) != desktop user (desktop_user_123)")

                except Exception as decode_error:
                    print(f"⚠️  Could not decode mobile token: {decode_error}")

            else:
                print("⚠️  Mobile did not inherit desktop auth (using fallback)")
                print(f"   Mobile token data: {mobile_token_data}")
        else:
            print(f"❌ Mobile token failed: {mobile_token_response.status_code}")
            print(f"   Response: {mobile_token_response.text}")
            return
    except Exception as e:
        print(f"❌ Mobile token error: {e}")
        return

    # Step 4: Test mobile token with WebSocket
    print("\n🔌 Step 4: Test mobile token with WebSocket...")
    try:
        import websockets

        async def test_mobile_websocket():
            mobile_token = mobile_token_data['token']
            ws_url = "ws://localhost:8089/ws"
            subprotocol = f"Bearer.{mobile_token}"

            try:
                async with websockets.connect(
                    ws_url,
                    subprotocols=[subprotocol]
                ) as websocket:
                    print("✅ Mobile WebSocket connected successfully!")

                    # Send identify message
                    identify_msg = {
                        "type": "identify",
                        "device_type": "mobile",
                        "session_id": "mobile-inheritance-test"
                    }
                    await websocket.send(json.dumps(identify_msg))

                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"📥 WebSocket response: {response}")

                    return True

            except Exception as ws_error:
                print(f"❌ Mobile WebSocket failed: {ws_error}")
                return False

        # Run WebSocket test
        websocket_success = asyncio.run(test_mobile_websocket())
        if websocket_success:
            print("✅ Mobile WebSocket test passed!")

    except ImportError:
        print("⚠️  WebSocket test skipped (websockets module not available)")
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")

    print("\n" + "=" * 50)
    print("🏁 Mobile Auth Inheritance Test Completed")

    # Summary
    if mobile_token_data.get("inherited_from") == "desktop_user_123":
        print("🎉 RESULT: SUCCESS - Mobile successfully inherited desktop auth!")
        return True
    else:
        print("❌ RESULT: FAILED - Mobile did not inherit desktop auth")
        return False

if __name__ == "__main__":
    # Check if server is running
    try:
        health_response = requests.get("http://localhost:8089/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Backend server is running")
        else:
            print(f"⚠️  Backend server returned: {health_response.status_code}")
    except Exception as e:
        print(f"❌ Backend server not accessible: {e}")
        print("🔧 Make sure server is running on port 8089")
        sys.exit(1)

    # Run the test
    success = test_mobile_auth_inheritance()
    sys.exit(0 if success else 1)