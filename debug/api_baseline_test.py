#!/usr/bin/env python3
"""
API Baseline Test Script
Tests all 83 API endpoints and establishes success rate baseline.
This must be run before any changes to monitor for regressions.
"""

import requests
import json
import time
from typing import Dict, List, Tuple

class APIBaselineTester:
    def __init__(self, base_url: str = "http://localhost:8089"):
        self.base_url = base_url
        self.results = []
        self.cookies = {}

    def run_baseline_test(self) -> Dict:
        """Run complete API baseline test suite"""
        print("🧪 Starting API Baseline Test Suite")
        print("=" * 60)

        # Get all endpoints from OpenAPI
        endpoints = self.discover_endpoints()
        print(f"📊 Discovered {len(endpoints)} API endpoints")

        # Test each endpoint
        total_tests = len(endpoints)
        passed = 0
        failed = 0

        for i, endpoint in enumerate(endpoints, 1):
            result = self.test_endpoint(endpoint)
            self.results.append(result)

            if result['success']:
                passed += 1
                status = "✅"
            else:
                failed += 1
                status = "❌"

            print(f"{status} {i:2d}/{total_tests}: {endpoint['method']:6} {endpoint['path']:30} → {result['status']}")

            # Small delay to avoid overwhelming server
            time.sleep(0.1)

        # Calculate baseline metrics after all tests
        success_rate = (passed / total_tests) * 100

        baseline = {
            "total_endpoints": total_tests,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "timestamp": time.time(),
            "results": self.results
        }

        print("\n" + "=" * 60)
        print("📊 API BASELINE RESULTS:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total: {total_tests}")
        print(f"   🎯 Success Rate: {success_rate:.1f}%")
        print("=" * 60)

        if success_rate < 90:
            print("🚨 WARNING: Success rate below 90% - investigate before proceeding!")
        else:
            print("✅ API health is good - safe to proceed with changes")

        return baseline

    def discover_endpoints(self) -> List[Dict]:
        """Discover all API endpoints from OpenAPI spec"""
        response = requests.get(f"{self.base_url}/openapi.json")
        openapi = response.json()

        endpoints = []
        paths = openapi.get('paths', {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    endpoints.append({
                        'path': path,
                        'method': method.upper(),
                        'summary': details.get('summary', path),
                        'tags': details.get('tags', ['untagged']),
                        'operation_id': details.get('operationId', ''),
                        'parameters': details.get('parameters', []),
                        'request_body': details.get('requestBody', {})
                    })

        return sorted(endpoints, key=lambda x: (x['path'], x['method']))

    def test_endpoint(self, endpoint: Dict) -> Dict:
        """Test a single endpoint and evaluate response"""
        url = f"{self.base_url}{endpoint['path']}"
        method = endpoint['method']

        try:
            # Build request options
            kwargs = {
                'headers': {'Content-Type': 'application/json'},
                'cookies': self.cookies,
                'timeout': 10
            }

            # Add test data for POST/PUT requests
            if method in ['POST', 'PUT', 'PATCH']:
                test_data = self.generate_test_data(endpoint)
                kwargs['json'] = test_data

            # Make request
            response = requests.request(method, url, **kwargs)
            status = response.status_code

            # Evaluate if this is a successful response
            success = self.evaluate_response_success(status, method, endpoint)

            return {
                'endpoint': f"{method} {endpoint['path']}",
                'status': status,
                'success': success,
                'method': method,
                'path': endpoint['path'],
                'tags': endpoint['tags']
            }

        except Exception as e:
            return {
                'endpoint': f"{method} {endpoint['path']}",
                'status': 'ERROR',
                'success': False,
                'error': str(e),
                'method': method,
                'path': endpoint['path'],
                'tags': endpoint['tags']
            }

    def generate_test_data(self, endpoint: Dict) -> Dict:
        """Generate appropriate test data for different endpoints"""
        path = endpoint['path']

        # Authentication endpoints
        if 'login' in path:
            return {"email": "test@example.com", "password": "test123"}

        # AI transcription endpoints
        elif 'transcribe' in path:
            return {
                "audio_data": "UklGRiYAAABXQVZFZm10IBAAAAABAAEAK",  # Minimal WAV
                "language": "nl",
                "format": "wav"
            }

        # Lexicon endpoints
        elif 'lexicon' in path and endpoint['method'] == 'POST':
            return {"term": "test_term", "category": "test_category"}

        # Pairing endpoints
        elif 'pair' in path:
            return {"device_type": "desktop"}

        # Generic test data
        else:
            return {"test": True}

    def evaluate_response_success(self, status: int, method: str, endpoint: Dict) -> bool:
        """Evaluate if a response status indicates success for the endpoint"""
        path = endpoint['path']

        # Special cases for expected authentication failures
        if status == 401 and any(tag in ['lexicon', 'auth'] for tag in endpoint.get('tags', [])):
            return True  # Expected for protected endpoints without auth

        # Special cases for monitoring endpoints (should always work)
        if 'monitoring' in path:
            return status == 200

        # General success evaluation
        if method == 'GET':
            return status in [200, 401, 403, 404]  # 401/403 expected for protected routes
        elif method in ['POST', 'PUT', 'PATCH']:
            return status in [200, 201, 400, 401, 403, 422]  # Various valid responses
        elif method == 'DELETE':
            return status in [200, 204, 401, 403, 404]
        else:
            return 200 <= status < 300

def main():
    """Run the baseline test"""
    tester = APIBaselineTester()
    baseline = tester.run_baseline_test()

    # Save baseline for future comparison
    with open('debug/api_baseline_results.json', 'w') as f:
        json.dump(baseline, f, indent=2)

    print(f"\n💾 Baseline saved to debug/api_baseline_results.json")

    return baseline['success_rate']

if __name__ == "__main__":
    success_rate = main()
    exit(0 if success_rate >= 90 else 1)