#!/usr/bin/env python3
"""
Run ALL normalization test cases from test_normalization.py via web interface
AUTOMATICALLY extracts ALL test cases from test_normalization.py each time
"""

import asyncio
import sys
import os
import time
import ast
import inspect

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

def extract_test_cases_from_file():
    """
    AUTOMATICALLY extract ALL test cases from test_normalization.py
    Dynamically reads the file and parses all test_cases arrays
    """
    print("📂 Extracting test cases from test_normalization.py...")
    
    # Path to the test_normalization.py file
    test_file_path = os.path.join(os.path.dirname(__file__), "unittests", "normalization", "test_normalization.py")
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return []
    
    all_test_cases = []
    
    try:
        # Read the test file
        with open(test_file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Parse the AST to extract test_cases arrays
        tree = ast.parse(file_content)
        
        # Find all assignments to variables named 'test_cases'
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'test_cases':
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            # Extract the test cases from this assignment
                            for item in node.value.elts:
                                if isinstance(item, (ast.List, ast.Tuple)) and len(item.elts) >= 2:
                                    # Extract the input and expected values
                                    try:
                                        input_val = ast.literal_eval(item.elts[0])
                                        expected_val = ast.literal_eval(item.elts[1])
                                        all_test_cases.append((input_val, expected_val))
                                    except (ValueError, TypeError):
                                        # Skip cases that can't be evaluated (e.g., contain variables)
                                        pass
        
        print(f"✅ Extracted {len(all_test_cases)} test cases from test_normalization.py")
        return all_test_cases
        
    except Exception as e:
        print(f"⚠️ Error extracting test cases: {e}")
        # Fallback to some basic test cases if extraction fails
        return [
            ('element een vier', 'element 14'),
            ('karius', 'cariës'),
            ('1-4', 'element 14'),
            ('licht-mucosale', 'licht mucosale'),
            ('interproximaal', 'interproximaal'),
        ]

async def run_all_comprehensive_tests():
    print("🧪 Running ALL comprehensive normalization tests from test_normalization.py")
    print("=" * 80)
    
    # Initialize DataRegistry exactly like the test script
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Create pipeline for admin user - SAME method as test script
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully using NormalizationFactory")
    
    # AUTOMATICALLY EXTRACT ALL TEST CASES from test_normalization.py
    all_test_cases = extract_test_cases_from_file()
    
    if not all_test_cases:
        print("❌ No test cases found! Check test_normalization.py")
        return
    
    print(f"\n🧪 Testing {len(all_test_cases)} comprehensive test cases:")
    print("-" * 80)
    
    passed = 0
    failed = 0
    total_time = 0
    
    for i, (test_input, expected) in enumerate(all_test_cases, 1):
        print(f"\n🔍 Test {i:2d}/{len(all_test_cases)}: '{test_input}'")
        print(f"   Expected: '{expected}'")
        
        # Time the normalization
        start_time = time.time()
        try:
            # Run normalization
            result = pipeline.normalize(test_input)
            actual = result.normalized_text
            elapsed_ms = (time.time() - start_time) * 1000
            total_time += elapsed_ms
            
            # Check result
            success = actual.lower() == expected.lower()
            status = "✅ PASS" if success else "❌ FAIL"
            
            print(f"   Actual:   '{actual}'")
            print(f"   Status:   {status} ({elapsed_ms:.1f}ms)")
            
            if success:
                passed += 1
            else:
                failed += 1
                print(f"   💥 MISMATCH: Expected '{expected}' but got '{actual}'")
                
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            total_time += elapsed_ms
            failed += 1
            print(f"   💥 ERROR ({elapsed_ms:.1f}ms): {e}")

    # Summary
    avg_time = total_time / len(all_test_cases) if all_test_cases else 0
    print(f"\n" + "=" * 80)
    print(f"📊 COMPREHENSIVE TEST SUMMARY:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Total tests: {len(all_test_cases)}")
    print(f"   ⏱️  Average time: {avg_time:.1f}ms per test")
    print(f"   ⏱️  Total time: {total_time:.1f}ms")
    print(f"   🎯 Success rate: {(passed/len(all_test_cases)*100):.1f}%")
    print("=" * 80)
    
    if failed > 0:
        print(f"\n⚠️  WARNING: {failed} test(s) failed!")
    else:
        print(f"\n🎉 ALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_all_comprehensive_tests())