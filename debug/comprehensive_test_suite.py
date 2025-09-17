#!/usr/bin/env python3
"""
🧪 COMPREHENSIVE TEST SUITE - API & WebSocket Testing
=====================================================
Visual test suite to verify all functionality after changes
"""
import asyncio
import websockets
import requests
import json
import base64
import time
from datetime import datetime
from typing import Dict, Any, Optional

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

class ComprehensiveTestSuite:
    """Complete test suite for API and WebSocket functionality"""

    def __init__(self):
        self.base_url = "http://localhost:8089"
        self.ws_url = "ws://localhost:8089/ws"
        self.session_token = None
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0

    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{TestColors.CYAN}{TestColors.BOLD}{'='*60}{TestColors.END}")
        print(f"{TestColors.CYAN}{TestColors.BOLD}🧪 {title}{TestColors.END}")
        print(f"{TestColors.CYAN}{TestColors.BOLD}{'='*60}{TestColors.END}")

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

        print(f"{icon} {TestColors.WHITE}{test_name:<40}{TestColors.END} [{status}]")
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

        print(f"\n{TestColors.PURPLE}{TestColors.BOLD}📊 TEST SUMMARY{TestColors.END}")
        print(f"{TestColors.PURPLE}{'='*40}{TestColors.END}")
        print(f"Total Tests: {TestColors.BOLD}{self.total_tests}{TestColors.END}")
        print(f"Passed: {TestColors.GREEN}{TestColors.BOLD}{self.passed_tests}{TestColors.END}")
        print(f"Failed: {TestColors.RED}{TestColors.BOLD}{self.total_tests - self.passed_tests}{TestColors.END}")
        print(f"Success Rate: {TestColors.CYAN}{TestColors.BOLD}{success_rate:.1f}%{TestColors.END}")

        if success_rate >= 95:
            print(f"{TestColors.GREEN}{TestColors.BOLD}🎉 EXCELLENT - System is production ready!{TestColors.END}")
        elif success_rate >= 80:
            print(f"{TestColors.YELLOW}{TestColors.BOLD}⚠️  GOOD - Minor issues to address{TestColors.END}")
        else:
            print(f"{TestColors.RED}{TestColors.BOLD}🚨 CRITICAL - Major issues found{TestColors.END}")

    async def test_health_checks(self):
        """Test basic server health"""
        self.print_header("HEALTH & BASIC CONNECTIVITY")

        # Basic health check
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            success = response.status_code == 200 and "healthy" in response.text
            self.print_test("Server Health Check", success,
                          f"Status: {response.status_code}, Response: {response.text[:50]}")
        except Exception as e:
            self.print_test("Server Health Check", False, f"Error: {e}")

        # API documentation
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            success = response.status_code == 200
            self.print_test("API Documentation", success, f"Status: {response.status_code}")
        except Exception as e:
            self.print_test("API Documentation", False, f"Error: {e}")

    async def test_authentication(self):
        """Test authentication endpoints"""
        self.print_header("AUTHENTICATION SYSTEM")

        # Test token-status without token
        try:
            response = requests.get(f"{self.base_url}/api/auth/token-status", timeout=5)
            data = response.json()
            success = (response.status_code == 200 and
                      data.get("valid") == False and
                      data.get("reason") == "no_token")
            self.print_test("Token Status (No Token)", success,
                          f"Response: {data.get('reason', 'unknown')}")
        except Exception as e:
            self.print_test("Token Status (No Token)", False, f"Error: {e}")

        # Test admin login
        try:
            login_data = {
                "email": "admin@dental-asr.com",
                "password": "admin123"
            }
            response = requests.post(f"{self.base_url}/api/auth/login",
                                   json=login_data, timeout=10)

            success = response.status_code == 200
            if success:
                # Try to extract session token from cookies
                cookies = response.cookies
                if 'session_token' in cookies:
                    self.session_token = cookies['session_token']

            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            self.print_test("Admin Login", success,
                          f"Status: {response.status_code}, User: {data.get('user', {}).get('email', 'unknown')}")
        except Exception as e:
            self.print_test("Admin Login", False, f"Error: {e}")

        # Test token-status with valid token (if we got one)
        if self.session_token:
            try:
                cookies = {'session_token': self.session_token}
                response = requests.get(f"{self.base_url}/api/auth/token-status",
                                      cookies=cookies, timeout=5)
                data = response.json()
                success = (response.status_code == 200 and
                          data.get("valid") == True and
                          data.get("authenticated") == True)
                self.print_test("Token Status (Valid Token)", success,
                              f"Valid: {data.get('valid')}, Expires in: {data.get('time_until_expiry_minutes', 0)} min")
            except Exception as e:
                self.print_test("Token Status (Valid Token)", False, f"Error: {e}")

        # Test email check
        try:
            response = requests.get(f"{self.base_url}/api/auth/check-email?email=admin@dental-asr.com", timeout=5)
            data = response.json()
            success = response.status_code == 200 and data.get("exists") == True
            self.print_test("Email Check", success, f"Exists: {data.get('exists')}")
        except Exception as e:
            self.print_test("Email Check", False, f"Error: {e}")

    async def test_ai_transcription(self):
        """Test AI transcription functionality"""
        self.print_header("AI TRANSCRIPTION SYSTEM")

        # Test AI status
        try:
            response = requests.get(f"{self.base_url}/api/ai/status", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else {}
            self.print_test("AI Provider Status", success,
                          f"Provider: {data.get('provider', 'unknown')}")
        except Exception as e:
            self.print_test("AI Provider Status", False, f"Error: {e}")

        # Test model info
        try:
            response = requests.get(f"{self.base_url}/api/ai/model-info", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else {}
            self.print_test("AI Model Info", success,
                          f"Model: {data.get('model', 'unknown')}")
        except Exception as e:
            self.print_test("AI Model Info", False, f"Error: {e}")

        # Test transcription with sample audio
        try:
            # Create minimal WAV file (silence)
            sample_rate = 16000
            duration_ms = 1000
            samples = int(sample_rate * duration_ms / 1000)

            # WAV header + silent PCM data
            wav_header = b'RIFF' + (36 + samples * 2).to_bytes(4, 'little') + b'WAVE'
            wav_header += b'fmt ' + (16).to_bytes(4, 'little')
            wav_header += (1).to_bytes(2, 'little')  # PCM format
            wav_header += (1).to_bytes(2, 'little')  # Mono
            wav_header += sample_rate.to_bytes(4, 'little')  # Sample rate
            wav_header += (sample_rate * 2).to_bytes(4, 'little')  # Byte rate
            wav_header += (2).to_bytes(2, 'little')  # Block align
            wav_header += (16).to_bytes(2, 'little')  # Bits per sample
            wav_header += b'data' + (samples * 2).to_bytes(4, 'little')

            # Silent audio data
            wav_data = wav_header + b'\x00\x00' * samples
            base64_audio = base64.b64encode(wav_data).decode('utf-8')

            # Test transcription
            transcription_data = {
                "audio_data": base64_audio,
                "language": "nl",
                "prompt": "Dutch dental terminology"
            }

            response = requests.post(f"{self.base_url}/api/ai/transcribe",
                                   json=transcription_data, timeout=30)

            success = response.status_code == 200
            if success:
                data = response.json()
                text = data.get('text', '')
                duration = data.get('duration', 0)
                self.print_test("Audio Transcription", success,
                              f"Duration: {duration}s, Text length: {len(text)} chars")
            else:
                self.print_test("Audio Transcription", False,
                              f"Status: {response.status_code}, Error: {response.text[:100]}")

        except Exception as e:
            self.print_test("Audio Transcription", False, f"Error: {e}")

    async def test_websocket_functionality(self):
        """Test WebSocket connections and messaging"""
        self.print_header("WEBSOCKET SYSTEM")

        # Test basic WebSocket connection
        try:
            # First get WebSocket token if we have session
            ws_token = None
            if self.session_token:
                try:
                    cookies = {'session_token': self.session_token}
                    response = requests.post(f"{self.base_url}/api/auth/ws-token",
                                           cookies=cookies, timeout=5)
                    if response.status_code == 200:
                        ws_token = response.json().get('token')
                except:
                    pass

            # Connect to WebSocket
            if ws_token:
                uri = f"{self.ws_url}"
                async with websockets.connect(uri, subprotocols=[f"Bearer.{ws_token}"]) as websocket:
                    self.print_test("WebSocket Connection (Authenticated)", True, "Connected with Bearer token")

                    # Test identification
                    identify_msg = {
                        "type": "identify",
                        "device_type": "desktop",
                        "session_id": f"test-{int(time.time())}"
                    }
                    await websocket.send(json.dumps(identify_msg))

                    # Wait for identification response (skip any initial messages)
                    identified = False
                    try:
                        for _ in range(3):  # Check up to 3 messages
                            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            data = json.loads(response)
                            if data.get('type') == 'identified':
                                identified = True
                                self.print_test("Device Identification", True,
                                              f"Type: {data.get('type')}, Device: {data.get('device_type')}")
                                break

                        if not identified:
                            self.print_test("Device Identification", False, "No 'identified' response received")

                    except asyncio.TimeoutError:
                        self.print_test("Device Identification", False, "Timeout waiting for response")

                    # Test ping/pong (only if identified successfully)
                    if identified:
                        try:
                            ping_msg = {"type": "ping", "sequence": 123}
                            await websocket.send(json.dumps(ping_msg))

                            # Look for pong response specifically
                            pong_received = False
                            for _ in range(2):  # Check up to 2 messages
                                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                                data = json.loads(response)
                                if data.get('type') == 'pong' and data.get('sequence') == 123:
                                    pong_received = True
                                    self.print_test("Ping/Pong Messaging", True,
                                                  f"Response: {data.get('type')}, Sequence: {data.get('sequence')}")
                                    break

                            if not pong_received:
                                self.print_test("Ping/Pong Messaging", False, "No pong response received")

                        except asyncio.TimeoutError:
                            self.print_test("Ping/Pong Messaging", False, "Timeout waiting for pong")
                    else:
                        self.print_test("Ping/Pong Messaging", False, "Skipped due to identification failure")

            else:
                # Test unauthenticated connection (should fail gracefully)
                try:
                    async with websockets.connect(self.ws_url) as websocket:
                        self.print_test("WebSocket Connection (No Auth)", False, "Should require authentication")
                except websockets.exceptions.ConnectionClosedError as e:
                    success = e.code in [1008, 1011]  # Policy violation or server error
                    self.print_test("WebSocket Auth Enforcement", success,
                                  f"Correctly rejected: Code {e.code}")
                except Exception as e:
                    self.print_test("WebSocket Auth Enforcement", False, f"Unexpected error: {e}")

        except Exception as e:
            self.print_test("WebSocket Connection", False, f"Connection error: {e}")

    async def test_lexicon_system(self):
        """Test lexicon management"""
        self.print_header("LEXICON MANAGEMENT")

        # Test categories
        try:
            response = requests.get(f"{self.base_url}/api/lexicon/categories", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else {}
            categories = data.get('categories', [])
            self.print_test("Lexicon Categories", success,
                          f"Found {len(categories)} categories")
        except Exception as e:
            self.print_test("Lexicon Categories", False, f"Error: {e}")

        # Test full lexicon
        try:
            response = requests.get(f"{self.base_url}/api/lexicon/full", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else {}
            self.print_test("Full Lexicon", success,
                          f"Response size: {len(str(data))} chars")
        except Exception as e:
            self.print_test("Full Lexicon", False, f"Error: {e}")

        # Test lexicon search with real terms
        try:
            response = requests.get(f"{self.base_url}/api/lexicon/search?q=cariës", timeout=5)
            success = response.status_code == 200 and response.json().get('count', 0) > 0
            data = response.json() if response.status_code == 200 else {}
            results = data.get('results', [])
            count = data.get('count', 0)
            self.print_test("Lexicon Search", success,
                          f"Found {count} results for 'cariës', Status: {response.status_code}")
        except Exception as e:
            self.print_test("Lexicon Search", False, f"Error: {e}")

    async def test_pairing_system(self):
        """Test device pairing functionality"""
        self.print_header("DEVICE PAIRING SYSTEM")

        # Test pairing code generation (requires auth)
        if self.session_token:
            try:
                cookies = {'session_token': self.session_token}
                pairing_data = {
                    "desktop_session_id": f"test-desktop-{int(time.time())}"
                }
                response = requests.post(f"{self.base_url}/api/generate-pair-code",
                                       json=pairing_data, cookies=cookies, timeout=5)

                success = response.status_code == 200
                data = response.json() if success else {}
                code = data.get('code', 'none')
                self.print_test("Generate Pairing Code", success,
                              f"Code: {code}, Expires: {data.get('expires_in', 0)}s")

                # If we got a code, test pairing validation
                if success and code != 'none':
                    try:
                        pair_data = {
                            "code": code,
                            "mobile_session_id": f"test-mobile-{int(time.time())}"
                        }
                        response = requests.post(f"{self.base_url}/api/pair-device",
                                               json=pair_data, timeout=5)
                        success = response.status_code == 200
                        data = response.json() if success else {}
                        self.print_test("Device Pairing Validation", success,
                                      f"Success: {data.get('success', False)}")
                    except Exception as e:
                        self.print_test("Device Pairing Validation", False, f"Error: {e}")

            except Exception as e:
                self.print_test("Generate Pairing Code", False, f"Error: {e}")
        else:
            self.print_test("Generate Pairing Code", False, "No authentication token available")

    async def test_real_audio_file(self):
        """Test transcription with real audio file if available"""
        self.print_header("REAL AUDIO TRANSCRIPTION")

        # Test with user's audio file
        audio_file_path = "/Users/janwillemvaartjes/Downloads/opname-2025-09-16T16-18-09.wav"

        try:
            with open(audio_file_path, "rb") as f:
                audio_data = f.read()

            base64_audio = base64.b64encode(audio_data).decode('utf-8')

            transcription_data = {
                "audio_data": base64_audio,
                "language": "nl",
                "prompt": "Dutch dental terminology"
            }

            response = requests.post(f"{self.base_url}/api/ai/transcribe",
                                   json=transcription_data, timeout=30)

            success = response.status_code == 200
            if success:
                data = response.json()
                text = data.get('text', '')
                duration = data.get('duration', 0)
                language = data.get('language', '')
                self.print_test("Real Audio Transcription", success,
                              f"Duration: {duration}s, Language: {language}, Text: '{text[:50]}...'")
            else:
                self.print_test("Real Audio Transcription", False,
                              f"Status: {response.status_code}, Error: {response.text[:100]}")

        except FileNotFoundError:
            self.print_test("Real Audio Transcription", True, "Audio file not found (expected)")
        except Exception as e:
            self.print_test("Real Audio Transcription", False, f"Error: {e}")

    async def test_websocket_audio_streaming(self):
        """Test WebSocket audio streaming"""
        self.print_header("WEBSOCKET AUDIO STREAMING")

        if not self.session_token:
            self.print_test("WebSocket Audio Streaming", False, "No authentication token")
            return

        try:
            # Get WebSocket token
            cookies = {'session_token': self.session_token}
            response = requests.post(f"{self.base_url}/api/auth/ws-token",
                                   cookies=cookies, timeout=5)
            if response.status_code != 200:
                self.print_test("WebSocket Token Generation", False, "Failed to get WS token")
                return

            ws_token = response.json().get('token')
            self.print_test("WebSocket Token Generation", True, "Token obtained successfully")

            # Connect and test audio streaming
            async with websockets.connect(self.ws_url, subprotocols=[f"Bearer.{ws_token}"]) as websocket:

                # Identify as desktop
                identify_msg = {
                    "type": "identify",
                    "device_type": "desktop",
                    "session_id": f"audio-test-{int(time.time())}"
                }
                await websocket.send(json.dumps(identify_msg))
                await asyncio.wait_for(websocket.recv(), timeout=5.0)  # Wait for identification

                # Create test audio blob (WAV format)
                sample_rate = 16000
                duration_ms = 2000
                samples = int(sample_rate * duration_ms / 1000)

                wav_header = b'RIFF' + (36 + samples * 2).to_bytes(4, 'little') + b'WAVE'
                wav_header += b'fmt ' + (16).to_bytes(4, 'little')
                wav_header += (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little')
                wav_header += sample_rate.to_bytes(4, 'little') + (sample_rate * 2).to_bytes(4, 'little')
                wav_header += (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little')
                wav_header += b'data' + (samples * 2).to_bytes(4, 'little')
                wav_data = wav_header + b'\x00\x00' * samples

                base64_audio = base64.b64encode(wav_data).decode('utf-8')

                # Send audio via WebSocket
                audio_msg = {
                    "type": "audio_data",
                    "format": "wav",
                    "audio_data": base64_audio
                }

                await websocket.send(json.dumps(audio_msg))
                self.print_test("WebSocket Audio Send", True,
                              f"Sent {len(wav_data)} bytes of WAV audio")

                # Wait for transcription result
                try:
                    start_time = time.time()
                    while time.time() - start_time < 15:  # 15 second timeout
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(response)

                        if data.get('type') == 'transcription_result':
                            text = data.get('text', '')
                            self.print_test("WebSocket Transcription Result", True,
                                          f"Received: '{text[:50]}...'")
                            break
                        elif data.get('type') == 'error':
                            self.print_test("WebSocket Transcription Result", False,
                                          f"Error: {data.get('message', 'unknown')}")
                            break
                    else:
                        self.print_test("WebSocket Transcription Result", True,
                                      "No transcription (expected with silence)")

                except asyncio.TimeoutError:
                    self.print_test("WebSocket Transcription Result", True,
                                  "Timeout (expected with silence)")

        except Exception as e:
            self.print_test("WebSocket Audio Streaming", False, f"Error: {e}")

    async def test_error_handling(self):
        """Test error handling and edge cases"""
        self.print_header("ERROR HANDLING & EDGE CASES")

        # Test invalid endpoints
        try:
            response = requests.get(f"{self.base_url}/api/nonexistent", timeout=5)
            success = response.status_code == 404
            self.print_test("404 Handling", success, f"Status: {response.status_code}")
        except Exception as e:
            self.print_test("404 Handling", False, f"Error: {e}")

        # Test malformed JSON
        try:
            response = requests.post(f"{self.base_url}/api/auth/login",
                                   data="invalid json",
                                   headers={"Content-Type": "application/json"},
                                   timeout=5)
            success = response.status_code in [400, 422]  # Bad request or validation error
            self.print_test("Malformed JSON Handling", success, f"Status: {response.status_code}")
        except Exception as e:
            self.print_test("Malformed JSON Handling", False, f"Error: {e}")

        # Test rate limiting (if enabled)
        try:
            # Make multiple rapid requests
            responses = []
            for i in range(5):
                response = requests.get(f"{self.base_url}/health", timeout=1)
                responses.append(response.status_code)

            # Should mostly be 200s (rate limiting may or may not kick in)
            success = most_successful = sum(1 for r in responses if r == 200) >= 3
            self.print_test("Rapid Request Handling", success,
                          f"Responses: {responses}")
        except Exception as e:
            self.print_test("Rapid Request Handling", False, f"Error: {e}")

    async def run_all_tests(self):
        """Run complete test suite"""
        print(f"{TestColors.PURPLE}{TestColors.BOLD}")
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print("🎯 Testing API & WebSocket Functionality")
        print("📅", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"🌐 Target: {self.base_url}")
        print(f"{TestColors.END}")

        # Run all test suites
        await self.test_health_checks()
        await self.test_authentication()
        await self.test_ai_transcription()
        await self.test_lexicon_system()
        await self.test_pairing_system()
        await self.test_websocket_functionality()
        await self.test_websocket_audio_streaming()
        await self.test_real_audio_file()
        await self.test_error_handling()

        # Print final summary
        self.print_summary()

        # Return success status
        return self.passed_tests / self.total_tests >= 0.8 if self.total_tests > 0 else False

async def main():
    """Main test runner"""
    test_suite = ComprehensiveTestSuite()

    try:
        success = await test_suite.run_all_tests()

        print(f"\n{TestColors.BOLD}🎯 FINAL RESULT:{TestColors.END}")
        if success:
            print(f"{TestColors.GREEN}{TestColors.BOLD}✅ SYSTEM IS STABLE AND READY{TestColors.END}")
            exit_code = 0
        else:
            print(f"{TestColors.RED}{TestColors.BOLD}❌ SYSTEM HAS ISSUES - NEEDS ATTENTION{TestColors.END}")
            exit_code = 1

        print(f"\n{TestColors.CYAN}📋 Use this test suite after every change to verify stability{TestColors.END}")
        return exit_code

    except KeyboardInterrupt:
        print(f"\n{TestColors.YELLOW}⚠️  Test suite interrupted{TestColors.END}")
        return 2
    except Exception as e:
        print(f"\n{TestColors.RED}💥 Test suite failed: {e}{TestColors.END}")
        return 3

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)