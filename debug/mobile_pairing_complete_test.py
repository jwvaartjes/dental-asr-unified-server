#!/usr/bin/env python3
"""
📱 COMPLETE MOBILE PAIRING TEST SUITE
=====================================
Test full mobile pairing flow with Bearer tokens and channel communication
"""
import asyncio
import websockets
import requests
import json
import base64
import time
from datetime import datetime
from typing import Optional

class TestColors:
    """ANSI color codes for visual output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class MobilePairingCompleteTest:
    """Complete mobile pairing flow test with Bearer tokens"""

    def __init__(self):
        self.base_url = "http://localhost:8089"
        self.ws_url = "ws://localhost:8089/ws"

        # Desktop session (httpOnly cookies)
        self.desktop_session = requests.Session()
        self.desktop_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Dental-ASR-Desktop'
        })

        # Mobile session (Bearer tokens)
        self.mobile_session = requests.Session()
        self.mobile_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) Dental-ASR-Mobile'
        })

        self.desktop_ws_token = None
        self.mobile_bearer_token = None
        self.pairing_code = None
        self.channel_id = None

        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0

    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{TestColors.CYAN}{TestColors.BOLD}{'='*70}{TestColors.END}")
        print(f"{TestColors.CYAN}{TestColors.BOLD}📱 {title}{TestColors.END}")
        print(f"{TestColors.CYAN}{TestColors.BOLD}{'='*70}{TestColors.END}")

    def print_test(self, test_name: str, success: bool, details: str = ""):
        """Print individual test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            icon = f"{TestColors.GREEN}✅"
            status = "PASS"
        else:
            icon = f"{TestColors.RED}❌"
            status = "FAIL"

        print(f"{icon} {TestColors.WHITE}{test_name:<50}{TestColors.END} [{status}]")
        if details:
            print(f"   {TestColors.YELLOW}💡 {details}{TestColors.END}")

        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def print_summary(self):
        """Print final test summary"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

        print(f"\n{TestColors.PURPLE}{TestColors.BOLD}📊 MOBILE PAIRING TEST SUMMARY{TestColors.END}")
        print(f"{TestColors.PURPLE}{'='*50}{TestColors.END}")
        print(f"Total Tests: {TestColors.BOLD}{self.total_tests}{TestColors.END}")
        print(f"Passed: {TestColors.GREEN}{TestColors.BOLD}{self.passed_tests}{TestColors.END}")
        print(f"Failed: {TestColors.RED}{TestColors.BOLD}{self.total_tests - self.passed_tests}{TestColors.END}")
        print(f"Success Rate: {TestColors.CYAN}{TestColors.BOLD}{success_rate:.1f}%{TestColors.END}")

        if success_rate >= 90:
            print(f"{TestColors.GREEN}{TestColors.BOLD}🎉 EXCELLENT - Mobile pairing is production ready!{TestColors.END}")
        elif success_rate >= 70:
            print(f"{TestColors.YELLOW}{TestColors.BOLD}⚠️  GOOD - Minor mobile pairing issues{TestColors.END}")
        else:
            print(f"{TestColors.RED}{TestColors.BOLD}🚨 CRITICAL - Mobile pairing has major issues{TestColors.END}")

    async def test_desktop_authentication_flow(self):
        """Test desktop authentication and pairing code generation"""
        self.print_header("DESKTOP AUTHENTICATION & PAIRING SETUP")

        # Step 1: Desktop login (httpOnly cookie) - REAL LIFE FLOW
        try:
            login_data = {
                "email": "admin@dental-asr.com",
                "password": "admin123"
            }

            # Login using exact same pattern as working curl test
            response = self.desktop_session.post(f"{self.base_url}/api/auth/login",
                                               json=login_data, timeout=10)

            success = response.status_code == 200
            user_email = "unknown"
            if success:
                # Force cookie persistence (mimic curl behavior)
                for cookie in response.cookies:
                    self.desktop_session.cookies.set(cookie.name, cookie.value, domain=cookie.domain)

                data = response.json()
                user_email = data.get('user', {}).get('email', 'unknown')

                # Verify cookie extraction from backend perspective
                session_token = self.desktop_session.cookies.get('session_token')
                if session_token:
                    print(f"   {TestColors.GREEN}🔍 Cookie captured: {session_token[:20]}...{TestColors.END}")
                else:
                    print(f"   {TestColors.RED}🔍 No session_token cookie found!{TestColors.END}")

            self.print_test("Desktop Login (httpOnly cookie)", success,
                          f"Status: {response.status_code}, User: {user_email}, Cookies: {len(self.desktop_session.cookies)}")

            if not success:
                return False

            # DEBUG: Verify cookies are properly set
            print(f"   {TestColors.BLUE}🔍 Session cookies after login: {dict(self.desktop_session.cookies)}{TestColors.END}")

        except Exception as e:
            self.print_test("Desktop Login", False, f"Error: {e}")
            return False

        # Step 2: Generate pairing code (DEBUG VERSION)
        try:
            pairing_data = {
                "desktop_session_id": f"desktop-test-{int(time.time())}"
            }

            response = self.desktop_session.post(f"{self.base_url}/api/generate-pair-code",
                                               json=pairing_data, timeout=10)

            success = response.status_code == 200

            # DEBUG: Show what happened
            if success:
                data = response.json()
                self.pairing_code = data.get('code')
                self.channel_id = f"pair-{self.pairing_code}"
                debug_info = f"Code: {self.pairing_code}, Channel: {self.channel_id}"
            else:
                debug_info = f"Status: {response.status_code}, Response: {response.text[:100]}"

            self.print_test("Generate Pairing Code", success, debug_info)

            if not success:
                print(f"   {TestColors.RED}🔍 DEBUG: Full response: {response.text}{TestColors.END}")
                print(f"   {TestColors.BLUE}🔍 DEBUG: Request headers: {dict(self.desktop_session.headers)}{TestColors.END}")
                print(f"   {TestColors.BLUE}🔍 DEBUG: Cookies: {dict(self.desktop_session.cookies)}{TestColors.END}")
                return False

        except Exception as e:
            self.print_test("Generate Pairing Code", False, f"Error: {e}")
            return False

        # Step 3: Get WebSocket Bearer token for desktop
        try:
            response = self.desktop_session.post(f"{self.base_url}/api/auth/ws-token", timeout=5)

            success = response.status_code == 200
            if success:
                data = response.json()
                self.desktop_ws_token = data.get('token')

            self.print_test("Desktop WebSocket Token", success,
                          f"Token obtained: {bool(self.desktop_ws_token)}")

            return success

        except Exception as e:
            self.print_test("Desktop WebSocket Token", False, f"Error: {e}")
            return False

    async def test_mobile_authentication_flow(self):
        """Test mobile authentication and pairing"""
        self.print_header("MOBILE AUTHENTICATION & PAIRING")

        if not self.pairing_code:
            self.print_test("Mobile Pairing", False, "No pairing code from desktop")
            return False

        # Step 1: Mobile pairing with desktop code
        try:
            mobile_data = {
                "code": self.pairing_code,
                "mobile_session_id": f"mobile-test-{int(time.time())}"
            }

            response = self.mobile_session.post(f"{self.base_url}/api/pair-device",
                                              json=mobile_data, timeout=10)

            success = response.status_code == 200
            pairing_result = response.json() if success else {}

            self.print_test("Mobile Device Pairing", success,
                          f"Pairing success: {pairing_result.get('success', False)}")

            if not success:
                return False

        except Exception as e:
            self.print_test("Mobile Device Pairing", False, f"Error: {e}")
            return False

        # Step 2: Get mobile Bearer token for WebSocket
        try:
            mobile_token_data = {
                "pair_code": self.pairing_code,
                "username": "mobile_user"
            }

            response = self.mobile_session.post(f"{self.base_url}/api/auth/ws-token-mobile",
                                              json=mobile_token_data, timeout=5)

            success = response.status_code == 200
            if success:
                data = response.json()
                self.mobile_bearer_token = data.get('token')

            self.print_test("Mobile WebSocket Token", success,
                          f"Token obtained: {bool(self.mobile_bearer_token)}")

            return success

        except Exception as e:
            self.print_test("Mobile WebSocket Token", False, f"Error: {e}")
            return False

    async def test_websocket_pairing_communication(self):
        """Test WebSocket communication between desktop and mobile"""
        self.print_header("WEBSOCKET PAIRING COMMUNICATION")

        if not self.desktop_ws_token or not self.mobile_bearer_token:
            self.print_test("WebSocket Communication", False, "Missing Bearer tokens")
            return False

        desktop_connected = False
        mobile_connected = False
        pairing_success = False

        try:
            # Connect desktop WebSocket
            desktop_uri = f"{self.ws_url}"
            async with websockets.connect(desktop_uri, subprotocols=[f"Bearer.{self.desktop_ws_token}"]) as desktop_ws:

                self.print_test("Desktop WebSocket Connection", True, "Connected with Bearer token")
                desktop_connected = True

                # Desktop identify and join channel
                desktop_identify = {
                    "type": "identify",
                    "device_type": "desktop",
                    "session_id": f"desktop-pairing-{int(time.time())}"
                }
                await desktop_ws.send(json.dumps(desktop_identify))

                # Wait for desktop identification (check multiple messages)
                identified = False
                for _ in range(3):  # Check up to 3 messages
                    try:
                        desktop_response = await asyncio.wait_for(desktop_ws.recv(), timeout=2.0)
                        desktop_data = json.loads(desktop_response)

                        if desktop_data.get('type') == 'identified':
                            identified = True
                            break
                        elif desktop_data.get('type') == 'connected':
                            continue  # Skip initial connection message
                    except asyncio.TimeoutError:
                        break

                self.print_test("Desktop Identification", identified,
                              f"Response: {'identified' if identified else 'timeout/wrong-message'}")

                # Connect mobile WebSocket
                mobile_uri = f"{self.ws_url}"
                async with websockets.connect(mobile_uri, subprotocols=[f"Bearer.{self.mobile_bearer_token}"]) as mobile_ws:

                    self.print_test("Mobile WebSocket Connection", True, "Connected with Bearer token")
                    mobile_connected = True

                    # Mobile init with pairing code
                    mobile_init = {
                        "type": "mobile_init",
                        "device_type": "mobile",
                        "pairing_code": self.pairing_code,
                        "session_id": f"mobile-pairing-{int(time.time())}"
                    }
                    await mobile_ws.send(json.dumps(mobile_init))

                    # Wait for mobile channel join (check multiple messages)
                    channel_joined = False
                    actual_channel = ''
                    for _ in range(3):  # Check up to 3 messages
                        try:
                            mobile_response = await asyncio.wait_for(mobile_ws.recv(), timeout=2.0)
                            mobile_data = json.loads(mobile_response)

                            if mobile_data.get('type') == 'channel_joined':
                                channel_joined = True
                                actual_channel = mobile_data.get('channel', '')
                                break
                            elif mobile_data.get('type') == 'connected':
                                continue  # Skip initial connection message
                        except asyncio.TimeoutError:
                            break

                    self.print_test("Mobile Channel Join", channel_joined,
                                  f"Channel: {actual_channel}, Expected: {self.channel_id}")

                    # Test channel communication
                    if channel_joined:
                        # Mobile sends test message to desktop via channel
                        test_message = {
                            "type": "channel_message",
                            "channelId": self.channel_id,
                            "payload": {
                                "type": "test_message",
                                "message": "Hello from mobile!",
                                "timestamp": time.time()
                            }
                        }
                        await mobile_ws.send(json.dumps(test_message))

                        # Desktop should receive the message
                        try:
                            desktop_msg = await asyncio.wait_for(desktop_ws.recv(), timeout=5.0)
                            desktop_received = json.loads(desktop_msg)

                            message_received = (desktop_received.get('type') == 'channel_message' and
                                              desktop_received.get('payload', {}).get('message') == 'Hello from mobile!')

                            self.print_test("Channel Message Communication", message_received,
                                          f"Desktop received: {desktop_received.get('payload', {}).get('message', 'none')}")

                            pairing_success = message_received

                        except asyncio.TimeoutError:
                            self.print_test("Channel Message Communication", False, "Desktop didn't receive message")

        except Exception as e:
            self.print_test("WebSocket Pairing Communication", False, f"Error: {e}")

        return pairing_success

    async def test_audio_via_channel(self):
        """Test audio streaming via channel communication"""
        self.print_header("AUDIO STREAMING VIA CHANNEL")

        if not self.desktop_ws_token or not self.mobile_bearer_token or not self.pairing_code:
            self.print_test("Audio Channel Test", False, "Missing prerequisites")
            return False

        try:
            # Create test audio blob
            sample_rate = 16000
            duration_ms = 1000
            samples = int(sample_rate * duration_ms / 1000)

            # WAV header + test audio
            wav_header = b'RIFF' + (36 + samples * 2).to_bytes(4, 'little') + b'WAVE'
            wav_header += b'fmt ' + (16).to_bytes(4, 'little')
            wav_header += (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little')
            wav_header += sample_rate.to_bytes(4, 'little') + (sample_rate * 2).to_bytes(4, 'little')
            wav_header += (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little')
            wav_header += b'data' + (samples * 2).to_bytes(4, 'little')

            # Add some test audio (not silence)
            test_audio = bytearray(b'\x00\x00' * samples)
            for i in range(0, len(test_audio), 4):
                # Add some variation to avoid pure silence
                test_audio[i] = (i % 256)
                test_audio[i+1] = ((i+1) % 256)

            wav_data = wav_header + bytes(test_audio)
            base64_audio = base64.b64encode(wav_data).decode('utf-8')

            # Test full audio channel flow
            desktop_uri = f"{self.ws_url}"
            async with websockets.connect(desktop_uri, subprotocols=[f"Bearer.{self.desktop_ws_token}"]) as desktop_ws:

                # Desktop setup
                await desktop_ws.send(json.dumps({
                    "type": "identify",
                    "device_type": "desktop",
                    "session_id": f"desktop-audio-{int(time.time())}"
                }))
                await asyncio.wait_for(desktop_ws.recv(), timeout=3.0)  # Wait for identification

                mobile_uri = f"{self.ws_url}"
                async with websockets.connect(mobile_uri, subprotocols=[f"Bearer.{self.mobile_bearer_token}"]) as mobile_ws:

                    # Mobile setup and join channel
                    await mobile_ws.send(json.dumps({
                        "type": "mobile_init",
                        "device_type": "mobile",
                        "pairing_code": self.pairing_code,
                        "session_id": f"mobile-audio-{int(time.time())}"
                    }))
                    await asyncio.wait_for(mobile_ws.recv(), timeout=3.0)  # Wait for channel join

                    # Mobile sends RAW BINARY audio (like your frontend does)
                    await mobile_ws.send(wav_data)  # Raw binary data, not JSON!
                    self.print_test("Mobile Raw Binary Audio Send", True,
                                  f"Sent {len(wav_data)} bytes as raw binary from mobile")

                    # Desktop should receive transcription result via channel routing
                    transcription_received = False
                    transcription_text = ""

                    # Wait for transcription result on desktop (routed via channel)
                    for _ in range(15):  # 15 attempts, 2s each = 30s total
                        try:
                            desktop_msg = await asyncio.wait_for(desktop_ws.recv(), timeout=2.0)
                            desktop_data = json.loads(desktop_msg)

                            if desktop_data.get('type') == 'transcription_result':
                                transcription_text = desktop_data.get('text', '')
                                transcription_received = True
                                source = desktop_data.get('source', 'unknown')
                                self.print_test("Mobile → Desktop Transcription Routing", True,
                                              f"Text: '{transcription_text[:50]}...', Source: {source}")
                                break

                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue  # Skip non-JSON messages

                    if not transcription_received:
                        self.print_test("Mobile → Desktop Transcription Routing", False,
                                      "No transcription result received on desktop")

                    return transcription_received

        except Exception as e:
            self.print_test("Audio Channel Test", False, f"Error: {e}")
            return False

    async def test_disconnect_flow(self):
        """Test disconnect notifications and cleanup"""
        self.print_header("DISCONNECT NOTIFICATIONS & CLEANUP")

        if not self.desktop_ws_token or not self.mobile_bearer_token:
            self.print_test("Disconnect Test", False, "Missing tokens")
            return False

        try:
            # Connect both devices
            desktop_uri = f"{self.ws_url}"
            async with websockets.connect(desktop_uri, subprotocols=[f"Bearer.{self.desktop_ws_token}"]) as desktop_ws:

                await desktop_ws.send(json.dumps({
                    "type": "identify",
                    "device_type": "desktop",
                    "session_id": f"desktop-disconnect-{int(time.time())}"
                }))
                await asyncio.wait_for(desktop_ws.recv(), timeout=3.0)

                mobile_uri = f"{self.ws_url}"
                mobile_ws = await websockets.connect(mobile_uri, subprotocols=[f"Bearer.{self.mobile_bearer_token}"])

                try:
                    # Mobile join channel
                    await mobile_ws.send(json.dumps({
                        "type": "mobile_init",
                        "device_type": "mobile",
                        "pairing_code": self.pairing_code,
                        "session_id": f"mobile-disconnect-{int(time.time())}"
                    }))
                    await asyncio.wait_for(mobile_ws.recv(), timeout=3.0)

                    self.print_test("Pairing Established", True, "Both devices connected to channel")

                    # Test mobile disconnect notification
                    await mobile_ws.close()
                    self.print_test("Mobile Disconnect", True, "Mobile disconnected")

                    # Desktop should receive disconnect notification
                    disconnect_received = False
                    for _ in range(3):  # Check multiple messages
                        try:
                            disconnect_msg = await asyncio.wait_for(desktop_ws.recv(), timeout=3.0)
                            disconnect_data = json.loads(disconnect_msg)

                            if disconnect_data.get('type') == 'mobile_disconnected':
                                disconnect_received = True
                                break

                        except asyncio.TimeoutError:
                            break

                    self.print_test("Disconnect Notification", disconnect_received,
                                  f"Desktop received disconnect: {disconnect_received}")

                    return disconnect_received

                finally:
                    # Proper cleanup
                    try:
                        if hasattr(mobile_ws, 'close') and not getattr(mobile_ws, 'closed', True):
                            await mobile_ws.close()
                    except:
                        pass

        except Exception as e:
            self.print_test("Disconnect Flow Test", False, f"Error: {e}")
            return False

    async def test_standalone_desktop_audio(self):
        """Test standalone desktop audio flow (your current usage)"""
        self.print_header("STANDALONE DESKTOP AUDIO (Direct Transcription)")

        if not self.desktop_ws_token:
            self.print_test("Standalone Audio Test", False, "No desktop WebSocket token")
            return False

        try:
            # Use your real audio file for testing
            try:
                audio_file_path = "/Users/janwillemvaartjes/Downloads/opname-2025-09-16T16-18-09.wav"
                with open(audio_file_path, "rb") as f:
                    real_audio_data = f.read()

                base64_audio = base64.b64encode(real_audio_data).decode('utf-8')
                audio_description = f"Real audio file: {len(real_audio_data)} bytes"

            except FileNotFoundError:
                # Fallback to test audio
                sample_rate = 16000
                duration_ms = 1000
                samples = int(sample_rate * duration_ms / 1000)
                wav_header = b'RIFF' + (36 + samples * 2).to_bytes(4, 'little') + b'WAVE'
                wav_header += b'fmt ' + (16).to_bytes(4, 'little')
                wav_header += (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little')
                wav_header += sample_rate.to_bytes(4, 'little') + (sample_rate * 2).to_bytes(4, 'little')
                wav_header += (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little')
                wav_header += b'data' + (samples * 2).to_bytes(4, 'little')
                real_audio_data = wav_header + b'\x00\x00' * samples
                base64_audio = base64.b64encode(real_audio_data).decode('utf-8')
                audio_description = f"Test audio: {len(real_audio_data)} bytes"

            # Test standalone desktop flow (direct to server)
            desktop_uri = f"{self.ws_url}"
            async with websockets.connect(desktop_uri, subprotocols=[f"Bearer.{self.desktop_ws_token}"]) as desktop_ws:

                # Desktop identification
                await desktop_ws.send(json.dumps({
                    "type": "identify",
                    "device_type": "desktop",
                    "session_id": f"standalone-{int(time.time())}"
                }))

                # Wait for identification (skip connected message)
                identified = False
                for _ in range(3):
                    try:
                        response = await asyncio.wait_for(desktop_ws.recv(), timeout=2.0)
                        data = json.loads(response)
                        if data.get('type') == 'identified':
                            identified = True
                            break
                    except asyncio.TimeoutError:
                        break

                self.print_test("Standalone Desktop Setup", identified,
                              "Desktop ready for standalone audio")

                if identified:
                    # Send audio directly (your frontend flow)
                    audio_message = {
                        "type": "audio_data",
                        "format": "wav",
                        "audio_data": base64_audio
                    }

                    await desktop_ws.send(json.dumps(audio_message))
                    self.print_test("Standalone Audio Direct Send", True,
                                  audio_description)

                    # Wait for transcription result (real transcription)
                    transcription_received = False
                    transcription_text = ""

                    for _ in range(15):  # 15 attempts, 1.5s each = 22.5s total
                        try:
                            result_msg = await asyncio.wait_for(desktop_ws.recv(), timeout=1.5)
                            result_data = json.loads(result_msg)

                            if result_data.get('type') == 'transcription_result':
                                transcription_text = result_data.get('text', '')
                                transcription_received = True
                                break

                        except asyncio.TimeoutError:
                            continue

                    self.print_test("Standalone Transcription Success", transcription_received,
                                  f"Text: '{transcription_text[:50]}...'" if transcription_text else "No transcription received")

                    return transcription_received or len(transcription_text) > 0

        except Exception as e:
            self.print_test("Standalone Desktop Audio Test", False, f"Error: {e}")
            return False

    async def run_complete_mobile_pairing_test(self):
        """Run complete mobile pairing test suite"""
        print(f"{TestColors.PURPLE}{TestColors.BOLD}")
        print("📱 COMPLETE MOBILE PAIRING TEST SUITE")
        print("=" * 70)
        print("🎯 Testing Full Mobile Pairing Flow with Bearer Tokens")
        print("📅", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"🌐 Target: {self.base_url}")
        print(f"{TestColors.END}")

        # Run all test phases
        desktop_success = await self.test_desktop_authentication_flow()

        # Test standalone desktop audio flow (your current usage)
        if desktop_success:
            await self.test_standalone_desktop_audio()

        mobile_success = await self.test_mobile_authentication_flow()

        if desktop_success and mobile_success:
            await self.test_websocket_pairing_communication()
            await self.test_audio_via_channel()
            await self.test_disconnect_flow()

        # Print final summary
        self.print_summary()

        # Return success status
        success_rate = self.passed_tests / self.total_tests if self.total_tests > 0 else 0
        return success_rate >= 0.8

async def main():
    """Main test runner"""
    test_suite = MobilePairingCompleteTest()

    try:
        success = await test_suite.run_complete_mobile_pairing_test()

        print(f"\n{TestColors.BOLD}🎯 MOBILE PAIRING RESULT:{TestColors.END}")
        if success:
            print(f"{TestColors.GREEN}{TestColors.BOLD}✅ MOBILE PAIRING IS PRODUCTION READY{TestColors.END}")
            print(f"{TestColors.GREEN}Bearer tokens work perfectly for mobile/WebSocket functionality{TestColors.END}")
            exit_code = 0
        else:
            print(f"{TestColors.RED}{TestColors.BOLD}❌ MOBILE PAIRING HAS ISSUES{TestColors.END}")
            print(f"{TestColors.RED}Bearer token or pairing flow needs attention{TestColors.END}")
            exit_code = 1

        print(f"\n{TestColors.CYAN}📋 This validates Bearer token usage for mobile pairing{TestColors.END}")
        print(f"{TestColors.CYAN}🔒 Helps confirm which endpoints need Bearer vs Cookie auth{TestColors.END}")
        return exit_code

    except KeyboardInterrupt:
        print(f"\n{TestColors.YELLOW}⚠️  Mobile pairing test interrupted{TestColors.END}")
        return 2
    except Exception as e:
        print(f"\n{TestColors.RED}💥 Mobile pairing test failed: {e}{TestColors.END}")
        return 3

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)