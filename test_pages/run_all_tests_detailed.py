#!/usr/bin/env python3
"""
Run ALL unit tests and show detailed outcomes - what our new system produces vs what was expected
This script runs the actual pytest tests and shows comprehensive results
"""

import asyncio
import sys
import os
import subprocess
import pytest
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_all_tests_detailed():
    print("🔄 Running ALL unit tests with detailed output...")
    print("=" * 80)
    print("COMPREHENSIVE TEST RESULTS - ALL 32+ TESTS")
    print("=" * 80)
    
    # Get current directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unittests", "normalization")
    
    print(f"\n📂 Test directory: {test_dir}")
    
    # First, list all test files and count tests
    test_files = []
    total_test_count = 0
    
    for file in os.listdir(test_dir):
        if file.startswith("test_") and file.endswith(".py"):
            test_files.append(file)
            
            # Count test methods in each file
            test_file_path = os.path.join(test_dir, file)
            with open(test_file_path, 'r') as f:
                content = f.read()
                test_methods = content.count("async def test_") + content.count("def test_")
                total_test_count += test_methods
                print(f"  📄 {file}: {test_methods} tests")
    
    print(f"\n📊 Total test files: {len(test_files)}")
    print(f"📊 Total test methods: {total_test_count}")
    print("\n" + "-" * 80)
    
    # Run pytest with verbose output and custom formatting
    cmd = [
        sys.executable, "-m", "pytest", 
        test_dir,
        "-v",
        "--tb=short",
        "--no-header",
        "-s"  # Don't capture output so we can see print statements
    ]
    
    print(f"🚀 Running command: {' '.join(cmd)}")
    print("-" * 80)
    
    try:
        # Run the tests and capture output
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        print("📋 PYTEST OUTPUT:")
        print("-" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  STDERR OUTPUT:")
            print("-" * 50)
            print(result.stderr)
        
        print(f"\n📊 EXIT CODE: {result.returncode}")
        
        # Parse and summarize results
        output_lines = result.stdout.split('\n')
        passed_tests = []
        failed_tests = []
        
        for line in output_lines:
            if " PASSED " in line:
                test_name = line.split("::")[1].split(" ")[0] if "::" in line else line
                passed_tests.append(test_name)
            elif " FAILED " in line:
                test_name = line.split("::")[1].split(" ")[0] if "::" in line else line
                failed_tests.append(test_name)
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL RUN: {len(passed_tests) + len(failed_tests)}")
        print(f"📊 EXPECTED: {total_test_count}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS ({len(passed_tests)}):")
            for test in passed_tests:
                print(f"  ✅ {test}")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  ❌ {test}")
        
        # Check if we got all expected tests
        actual_total = len(passed_tests) + len(failed_tests)
        if actual_total < total_test_count:
            print(f"\n⚠️  WARNING: Only {actual_total} tests ran, but {total_test_count} were expected!")
            print("   Some tests may have failed to run due to setup issues.")
        
        # Show final statistics from pytest output
        for line in output_lines[-10:]:
            if "failed" in line.lower() or "passed" in line.lower() or "error" in line.lower():
                if any(word in line for word in ["failed,", "passed,", "error", "==="]):
                    print(f"\n📊 PYTEST SUMMARY: {line.strip()}")
        
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Tests took longer than 5 minutes to complete")
    except Exception as e:
        print(f"❌ ERROR running tests: {e}")
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST RUN COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_all_tests_detailed())