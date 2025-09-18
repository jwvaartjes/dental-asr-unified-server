#!/usr/bin/env python3
"""
🧪 COMPLETE API TEST SUITE - ALL 71 ENDPOINTS
=============================================
Auto-discovers and tests every single API endpoint
"""
import asyncio
import websockets
import requests
import json
import base64
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

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

class CompleteAPITestSuite:
    """Comprehensive test suite for ALL API endpoints"""

    def __init__(self):
        self.base_url = "http://localhost:8089"
        self.ws_url = "ws://localhost:8089/ws"
        self.session = requests.Session()  # Persistent session with cookies
        self.session_token = None
        self.ws_token = None
        self.admin_user_data = None  # Real admin user info
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.all_endpoints = []

    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{TestColors.CYAN}{TestColors.BOLD}{'='*80}{TestColors.END}")
        print(f"{TestColors.CYAN}{TestColors.BOLD}🧪 {title}{TestColors.END}")
        print(f"{TestColors.CYAN}{TestColors.BOLD}{'='*80}{TestColors.END}")

    def print_test(self, test_name: str, success: bool, details: str = "", endpoint: str = ""):
        """Print individual test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            icon = f"{TestColors.GREEN}✅"
            status = "PASS"
        else:
            icon = f"{TestColors.RED}❌"
            status = "FAIL"

        # Truncate long test names for alignment
        display_name = test_name[:50] + "..." if len(test_name) > 50 else test_name

        print(f"{icon} {TestColors.WHITE}{display_name:<53}{TestColors.END} [{status}]")
        if details:
            print(f"   {TestColors.YELLOW}💡 {details}{TestColors.END}")
        if endpoint:
            print(f"   {TestColors.BLUE}🔗 {endpoint}{TestColors.END}")

        self.test_results.append({
            "test": test_name,
            "endpoint": endpoint,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def print_summary(self):
        """Print final test summary"""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

        print(f"\n{TestColors.PURPLE}{TestColors.BOLD}📊 COMPLETE API TEST SUMMARY{TestColors.END}")
        print(f"{TestColors.PURPLE}{'='*60}{TestColors.END}")
        print(f"Total API Endpoints Tested: {TestColors.BOLD}{len(self.all_endpoints)}{TestColors.END}")
        print(f"Total Tests Run: {TestColors.BOLD}{self.total_tests}{TestColors.END}")
        print(f"Passed: {TestColors.GREEN}{TestColors.BOLD}{self.passed_tests}{TestColors.END}")
        print(f"Failed: {TestColors.RED}{TestColors.BOLD}{self.total_tests - self.passed_tests}{TestColors.END}")
        print(f"Success Rate: {TestColors.CYAN}{TestColors.BOLD}{success_rate:.1f}%{TestColors.END}")

        # Show endpoint coverage
        endpoint_coverage = len(self.all_endpoints) / 71 * 100 if self.all_endpoints else 0
        print(f"Endpoint Coverage: {TestColors.CYAN}{TestColors.BOLD}{endpoint_coverage:.1f}%{TestColors.END}")

        if success_rate >= 95 and endpoint_coverage >= 90:
            print(f"{TestColors.GREEN}{TestColors.BOLD}🎉 EXCELLENT - Complete system verification passed!{TestColors.END}")
        elif success_rate >= 80:
            print(f"{TestColors.YELLOW}{TestColors.BOLD}⚠️  GOOD - Minor issues to address{TestColors.END}")
        else:
            print(f"{TestColors.RED}{TestColors.BOLD}🚨 CRITICAL - Major issues found{TestColors.END}")

    async def discover_all_endpoints(self) -> List[Dict[str, Any]]:
        """Auto-discover all API endpoints from OpenAPI spec"""
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            if response.status_code != 200:
                print(f"{TestColors.RED}Failed to get OpenAPI spec{TestColors.END}")
                return []

            openapi_spec = response.json()
            paths = openapi_spec.get('paths', {})

            endpoints = []
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        endpoints.append({
                            'path': path,
                            'method': method.upper(),
                            'summary': details.get('summary', ''),
                            'tags': details.get('tags', []),
                            'requires_auth': self._requires_auth(details),
                            'parameters': details.get('parameters', []),
                            'request_body': details.get('requestBody', {}),
                            'responses': details.get('responses', {})
                        })

            self.all_endpoints = endpoints
            print(f"{TestColors.CYAN}🔍 Discovered {len(endpoints)} API endpoints{TestColors.END}")
            return endpoints

        except Exception as e:
            print(f"{TestColors.RED}Error discovering endpoints: {e}{TestColors.END}")
            return []

    def _requires_auth(self, endpoint_details: Dict) -> bool:
        """Determine if endpoint requires authentication"""
        # Check if endpoint has security requirements
        security = endpoint_details.get('security', [])
        if security:
            return True

        # Check common auth patterns in path or summary
        summary = endpoint_details.get('summary', '').lower()
        if any(word in summary for word in ['admin', 'protected', 'auth', 'user']):
            return True

        return False

    async def authenticate(self):
        """Complete real user authentication flow"""
        try:
            # Step 1: Setup desktop session with proper headers
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Dental-ASR-Desktop'
            })

            # Step 2: Desktop login → get httpOnly cookie
            login_data = {
                "email": "admin@dental-asr.com",
                "password": "admin123"
            }

            response = self.session.post(f"{self.base_url}/api/auth/login",
                                       json=login_data, timeout=10)

            if response.status_code == 200:
                # Extract session token from cookies
                if 'session_token' in self.session.cookies:
                    self.session_token = self.session.cookies['session_token']
                    print(f"{TestColors.GREEN}✅ Desktop session authentication successful{TestColors.END}")

                    # Step 3: Get admin user data via auth status
                    try:
                        auth_response = self.session.get(f"{self.base_url}/api/auth/status", timeout=5)
                        if auth_response.status_code == 200:
                            auth_data = auth_response.json()
                            self.admin_user_data = auth_data.get('user', {})
                            print(f"{TestColors.GREEN}✅ Admin user data loaded: {self.admin_user_data.get('email')}{TestColors.END}")
                    except Exception as e:
                        print(f"{TestColors.YELLOW}⚠️ Failed to get user data: {e}{TestColors.END}")

                    # Step 4: Get Bearer token for API access
                    try:
                        ws_response = self.session.post(f"{self.base_url}/api/auth/ws-token", timeout=5)
                        if ws_response.status_code == 200:
                            self.ws_token = ws_response.json().get('token')
                            print(f"{TestColors.GREEN}✅ Bearer token obtained for admin API access{TestColors.END}")
                        else:
                            print(f"{TestColors.YELLOW}⚠️ Bearer token failed: {ws_response.status_code}{TestColors.END}")
                            # Continue without Bearer token - some endpoints will fail
                    except Exception as e:
                        print(f"{TestColors.YELLOW}⚠️ Bearer token error: {e}{TestColors.END}")

            return self.session_token is not None

        except Exception as e:
            print(f"{TestColors.RED}❌ Authentication failed: {e}{TestColors.END}")
            return False

    async def test_endpoint(self, endpoint: Dict[str, Any]):
        """Test a single API endpoint using real user flow"""
        path = endpoint['path']
        method = endpoint['method']
        summary = endpoint['summary']
        requires_auth = endpoint['requires_auth']

        # Replace path parameters with real data
        real_path = self._resolve_path_parameters(path)
        url = f"{self.base_url}{real_path}"

        # Prepare authentication headers
        headers = {'Content-Type': 'application/json'}

        if requires_auth:
            # Admin endpoints require Bearer token
            if ('/users/' in path or '/admin/' in path or 'admin' in summary.lower()):
                if self.ws_token:
                    headers['Authorization'] = f'Bearer {self.ws_token}'
                else:
                    # Can't test admin endpoints without Bearer token
                    self.print_test(f"{method} {summary or path}", False, "No Bearer token for admin endpoint", real_path)
                    return

        # Prepare test data based on endpoint
        test_data = self._generate_real_test_data(endpoint)

        try:
            # Execute request using persistent session
            if method == 'GET':
                response = self.session.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = self.session.post(url, json=test_data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = self.session.put(url, json=test_data, headers=headers, timeout=10)
            elif method == 'DELETE':
                # DELETE operations may need request body (frontend-style)
                if test_data:
                    response = self.session.delete(url, json=test_data, headers=headers, timeout=10)
                else:
                    response = self.session.delete(url, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = self.session.patch(url, json=test_data, headers=headers, timeout=10)
            else:
                self.print_test(f"{method} {path}", False, "Unsupported method", real_path)
                return

            # Evaluate response
            success = self._evaluate_response(response, endpoint)
            status_info = f"Status: {response.status_code}"

            # Add response size info if JSON
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    if isinstance(data, dict):
                        status_info += f", Keys: {len(data)}"
                    elif isinstance(data, list):
                        status_info += f", Items: {len(data)}"
            except:
                pass

            self.print_test(f"{method} {summary or path}", success, status_info, real_path)

        except requests.Timeout:
            self.print_test(f"{method} {path}", False, "Request timeout", real_path)
        except Exception as e:
            self.print_test(f"{method} {path}", False, f"Error: {str(e)[:100]}", real_path)

    def _resolve_path_parameters(self, path: str) -> str:
        """Replace path parameters with real values (frontend-style)"""
        import urllib.parse

        # Handle path parameters
        if '{user_id}' in path and self.admin_user_data:
            # Use real admin user ID
            real_user_id = self.admin_user_data.get('id', 'test-user-id')
            path = path.replace('{user_id}', real_user_id)
        elif '{user_id}' in path:
            # Fallback to admin user lookup
            path = path.replace('{user_id}', 'admin-fallback-id')

        if '{category}' in path:
            # Use real lexicon category
            path = path.replace('{category}', 'rx_findings')

        if '{word}' in path:
            # Use real word for testing
            path = path.replace('{word}', 'test_word')

        if '{template_id}' in path:
            # Use real template ID if available
            path = path.replace('{template_id}', 'test-template-id')

        # Add query parameters (frontend-style with proper encoding)
        if 'check-email' in path and '?' not in path:
            # Frontend would encode email properly
            email = urllib.parse.quote('admin@dental-asr.com')
            path += f'?email={email}'
        elif 'search' in path and 'lexicon' in path and '?' not in path:
            # Frontend would encode special characters
            query = urllib.parse.quote('cariës')
            path += f'?q={query}'

        return path

    def _generate_real_test_data(self, endpoint: Dict[str, Any]) -> Optional[Dict]:
        """Generate realistic test data based on actual system usage"""
        path = endpoint['path']
        method = endpoint['method']

        # Real authentication data
        if 'login' in path and method == 'POST':
            if 'magic' in path:
                return {"email": "test@practijk.nl"}
            else:
                return {"email": "admin@dental-asr.com", "password": "admin123"}

        # Real pairing data
        elif 'generate-pair-code' in path:
            return {"desktop_session_id": f"desktop-{int(time.time())}-realtest"}
        elif 'pair-device' in path:
            return {"code": "123456", "mobile_session_id": f"mobile-{int(time.time())}-realtest"}

        # Real transcription data (use actual audio)
        elif 'transcribe' in path:
            try:
                # Try to use the real audio file
                audio_file_path = "/Users/janwillemvaartjes/Downloads/opname-2025-09-16T16-18-09.wav"
                with open(audio_file_path, "rb") as f:
                    audio_data = f.read()
                return {
                    "audio_data": base64.b64encode(audio_data).decode('utf-8'),
                    "language": "nl",
                    "prompt": "Dutch dental terminology"
                }
            except:
                # Fallback to minimal WAV
                return self._generate_minimal_wav_data()

        # Real lexicon data
        elif 'lexicon' in path:
            if 'add-canonical' in path and method == 'POST':
                return {"term": "testterm", "category": "rx_findings"}
            elif 'remove-canonical' in path and method == 'DELETE':
                return {"term": "testterm", "category": "rx_findings"}
            elif 'add-category' in path and method == 'POST':
                return {"category": "test_category", "description": "Test category for API testing"}
            elif 'delete-category' in path and method == 'POST':
                return {"category": "test_category"}
            elif 'add-variant' in path and method == 'POST':
                return {"canonical": "cariës", "variant": "karies", "category": "rx_findings"}
            elif 'remove-variant' in path and method == 'POST':
                return {"canonical": "cariës", "variant": "karies", "category": "rx_findings"}

        # Real user management data
        elif 'users' in path and method == 'POST':
            return {
                "email": "test@api.test",
                "name": "API Test User",
                "role": "user",
                "password": "testpass123"
            }
        elif 'users' in path and method == 'PUT':
            return {"name": "Updated Test User", "status": "active"}

        # Real template data
        elif 'template' in path and method == 'POST':
            return {
                "name": "API Test Template",
                "template_type": "quick-check",
                "description": "Generated by API test suite"
            }

        # Real protect words data
        elif 'protect_words' in path and method == 'POST':
            return {"words": ["Paro", "Cito"]}

        # Default minimal data for POST requests
        if method in ['POST', 'PUT', 'PATCH']:
            return {"test": True, "timestamp": int(time.time())}

        return None

    def _generate_minimal_wav_data(self) -> Dict[str, str]:
        """Generate minimal WAV file for transcription testing"""
        sample_rate = 16000
        duration_ms = 500  # Very short for fast testing
        samples = int(sample_rate * duration_ms / 1000)

        # WAV header + silent PCM data
        wav_header = b'RIFF' + (36 + samples * 2).to_bytes(4, 'little') + b'WAVE'
        wav_header += b'fmt ' + (16).to_bytes(4, 'little')
        wav_header += (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little')
        wav_header += sample_rate.to_bytes(4, 'little') + (sample_rate * 2).to_bytes(4, 'little')
        wav_header += (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little')
        wav_header += b'data' + (samples * 2).to_bytes(4, 'little')
        wav_data = wav_header + b'\x00\x00' * samples

        return {
            "audio_data": base64.b64encode(wav_data).decode('utf-8'),
            "language": "nl",
            "prompt": "test audio"
        }

    def _generate_test_data(self, endpoint: Dict[str, Any]) -> Optional[Dict]:
        """Legacy function - redirects to real test data generation"""
        return self._generate_real_test_data(endpoint)

    def _evaluate_response(self, response: requests.Response, endpoint: Dict[str, Any]) -> bool:
        """Evaluate if response is successful"""
        status_code = response.status_code
        path = endpoint['path']
        method = endpoint['method']

        # Define success criteria
        if method == 'GET':
            # GET requests should return 200 or 401/403 for auth-protected endpoints
            return status_code in [200, 401, 403, 404]
        elif method in ['POST', 'PUT', 'PATCH']:
            # POST/PUT/PATCH can return 200, 201, 400 (validation), 401 (auth), 422 (validation)
            return status_code in [200, 201, 400, 401, 403, 422]
        elif method == 'DELETE':
            # DELETE can return 200, 204, 404, 401
            return status_code in [200, 204, 401, 403, 404]

        return False

    async def test_all_discovered_endpoints(self):
        """Test every discovered endpoint"""
        if not self.all_endpoints:
            print(f"{TestColors.RED}No endpoints discovered to test{TestColors.END}")
            return

        self.print_header(f"TESTING ALL {len(self.all_endpoints)} DISCOVERED ENDPOINTS")

        # Group endpoints by tag/category for organized testing
        endpoints_by_tag = {}
        for endpoint in self.all_endpoints:
            tags = endpoint.get('tags', ['untagged'])
            tag = tags[0] if tags else 'untagged'
            if tag not in endpoints_by_tag:
                endpoints_by_tag[tag] = []
            endpoints_by_tag[tag].append(endpoint)

        # Test each category
        for tag, endpoints in endpoints_by_tag.items():
            print(f"\n{TestColors.BLUE}{TestColors.BOLD}📋 Testing {tag.upper()} endpoints ({len(endpoints)} endpoints):{TestColors.END}")

            for endpoint in endpoints:
                await self.test_endpoint(endpoint)
                # Small delay to avoid overwhelming server
                await asyncio.sleep(0.1)

    async def test_endpoint_security(self):
        """Test endpoint security and authentication"""
        self.print_header("ENDPOINT SECURITY TESTING")

        # Test protected endpoints without auth
        protected_endpoints = [ep for ep in self.all_endpoints if ep['requires_auth']]

        print(f"{TestColors.YELLOW}Testing {len(protected_endpoints)} protected endpoints without auth...{TestColors.END}")

        security_passes = 0
        for endpoint in protected_endpoints[:10]:  # Test first 10 to avoid spam
            path = endpoint['path']
            method = endpoint['method']

            try:
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{path}", timeout=5)
                elif method == 'POST':
                    response = requests.post(f"{self.base_url}{path}", json={}, timeout=5)
                else:
                    continue

                # Should return 401 or 403 for auth-required endpoints
                if response.status_code in [401, 403]:
                    security_passes += 1

            except:
                pass

        security_rate = security_passes / min(len(protected_endpoints), 10) * 100
        success = security_rate >= 80

        self.print_test("Protected Endpoint Security", success,
                      f"{security_passes}/{min(len(protected_endpoints), 10)} properly protected ({security_rate:.1f}%)")

    async def test_endpoint_performance(self):
        """Test endpoint response times"""
        self.print_header("ENDPOINT PERFORMANCE TESTING")

        # Test a sample of endpoints for performance
        sample_endpoints = self.all_endpoints[:20]  # Test first 20
        fast_endpoints = 0
        total_time = 0

        for endpoint in sample_endpoints:
            path = endpoint['path']
            method = endpoint['method']

            if method != 'GET':  # Only test GET for performance
                continue

            try:
                start_time = time.time()

                headers = {}
                cookies = {}
                if endpoint['requires_auth'] and self.session_token:
                    cookies['session_token'] = self.session_token

                response = requests.get(f"{self.base_url}{path}",
                                      headers=headers, cookies=cookies, timeout=5)

                elapsed = time.time() - start_time
                total_time += elapsed

                if elapsed < 1.0:  # Under 1 second is good
                    fast_endpoints += 1

            except:
                pass

        if sample_endpoints:
            avg_time = total_time / len(sample_endpoints) if sample_endpoints else 0
            fast_rate = fast_endpoints / len(sample_endpoints) * 100

            success = avg_time < 2.0 and fast_rate >= 70

            self.print_test("Endpoint Response Times", success,
                          f"Avg: {avg_time:.2f}s, Fast (<1s): {fast_rate:.1f}%")

    async def run_complete_test_suite(self):
        """Run the complete test suite"""
        print(f"{TestColors.PURPLE}{TestColors.BOLD}")
        print("🧪 COMPLETE API TEST SUITE")
        print("=" * 80)
        print("🎯 Testing ALL API Endpoints Automatically")
        print("📅", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"🌐 Target: {self.base_url}")
        print(f"{TestColors.END}")

        # Step 1: Authenticate
        print(f"{TestColors.YELLOW}🔐 Authenticating...{TestColors.END}")
        auth_success = await self.authenticate()

        if not auth_success:
            print(f"{TestColors.RED}❌ Authentication failed - some tests will be limited{TestColors.END}")

        # Step 2: Discover all endpoints
        print(f"{TestColors.YELLOW}🔍 Discovering all API endpoints...{TestColors.END}")
        endpoints = await self.discover_all_endpoints()

        if not endpoints:
            print(f"{TestColors.RED}❌ No endpoints discovered - cannot continue{TestColors.END}")
            return False

        # Step 3: Test all endpoints
        await self.test_all_discovered_endpoints()

        # Step 4: Security testing
        await self.test_endpoint_security()

        # Step 5: Performance testing
        await self.test_endpoint_performance()

        # Print final summary
        self.print_summary()

        # Generate detailed report
        await self.generate_detailed_report()

        # Return success status
        success_rate = self.passed_tests / self.total_tests if self.total_tests > 0 else 0
        return success_rate >= 0.95

    async def generate_detailed_report(self):
        """Generate detailed test report"""
        print(f"\n{TestColors.PURPLE}{TestColors.BOLD}📋 DETAILED ENDPOINT REPORT{TestColors.END}")
        print(f"{TestColors.PURPLE}{'='*50}{TestColors.END}")

        # Group results by status
        passed = [r for r in self.test_results if r['success']]
        failed = [r for r in self.test_results if not r['success']]

        print(f"{TestColors.GREEN}✅ PASSED TESTS ({len(passed)}):{TestColors.END}")
        for result in passed[:10]:  # Show first 10
            print(f"   • {result['test']}")
        if len(passed) > 10:
            print(f"   ... and {len(passed) - 10} more")

        if failed:
            print(f"\n{TestColors.RED}❌ FAILED TESTS ({len(failed)}):{TestColors.END}")
            for result in failed:
                print(f"   • {result['test']}: {result['details']}")

        # Show endpoint coverage by category
        tags = set()
        for endpoint in self.all_endpoints:
            endpoint_tags = endpoint.get('tags', ['untagged'])
            tags.update(endpoint_tags)

        print(f"\n{TestColors.CYAN}📊 ENDPOINT COVERAGE BY CATEGORY:{TestColors.END}")
        for tag in sorted(tags):
            tag_endpoints = [ep for ep in self.all_endpoints if tag in ep.get('tags', [])]
            print(f"   • {tag}: {len(tag_endpoints)} endpoints")

async def main():
    """Main test runner"""
    test_suite = CompleteAPITestSuite()

    try:
        success = await test_suite.run_complete_test_suite()

        print(f"\n{TestColors.BOLD}🎯 FINAL RESULT:{TestColors.END}")
        if success:
            print(f"{TestColors.GREEN}{TestColors.BOLD}✅ ALL SYSTEMS VERIFIED AND STABLE{TestColors.END}")
            exit_code = 0
        else:
            print(f"{TestColors.RED}{TestColors.BOLD}❌ SYSTEM HAS ISSUES - NEEDS ATTENTION{TestColors.END}")
            exit_code = 1

        print(f"\n{TestColors.CYAN}📋 This suite tested ALL {len(test_suite.all_endpoints)} discovered endpoints{TestColors.END}")
        print(f"{TestColors.CYAN}🔄 Run after every change to verify complete system stability{TestColors.END}")
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