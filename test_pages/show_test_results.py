#!/usr/bin/env python3
"""
Show detailed test results - what our new system produces vs what was expected
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization.factory import NormalizationFactory

async def show_all_test_results():
    print("🔄 Initializing system...")
    
    # Initialize the data registry and pipeline
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(cache=cache, loader=loader)
    
    pipeline = await NormalizationFactory.create_for_admin(data_registry)
    
    print("✅ System initialized! Running test cases...\n")
    print("=" * 80)
    print("DETAILED TEST RESULTS - NEW SYSTEM vs EXPECTED")
    print("=" * 80)
    
    # Test cases from the basic element parsing test
    basic_test_cases = [
        ("cariës distaal van de 1-4", "cariës distaal van element 14"),
        ("cariës op 1 2", "cariës op element 12"),
        ("prothese op 1-3", "prothese op element 13"),
        ("13 14 15", "element 13 element 14 element 15"),
        ("21 22 23", "element 21 element 22 element 23"),
        ("27 28", "element 27 element 28"),
        ("37 38", "element 37 element 38"),
        ("44 45 46", "element 44 element 45 element 46"),
    ]
    
    print("\n📋 BASIC ELEMENT PARSING TESTS:")
    print("-" * 50)
    
    for i, (input_text, expected) in enumerate(basic_test_cases, 1):
        result = pipeline.normalize(input_text)
        actual = result.normalized_text
        
        status = "✅ PASS" if actual.lower() == expected.lower() else "❌ FAIL"
        
        print(f"\nTest {i}:")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Actual:   '{actual}'")
        print(f"  Status:   {status}")
        
        if actual.lower() != expected.lower():
            print(f"  Difference: Expected '{expected}' but got '{actual}'")
    
    # Dutch number words tests
    dutch_number_tests = [
        ("cariës op een vier", "cariës op element 14"),
        ("element twee drie", "element 23"),
        ("tand één acht", "tand 18"),
        ("twee vier en drie vijf", "element 24 en element 35"),
        ("één twee drie", "element 123"),
        ("vier vijf zes", "element 456"),
    ]
    
    print(f"\n\n📋 DUTCH NUMBER WORDS TESTS:")
    print("-" * 50)
    
    for i, (input_text, expected) in enumerate(dutch_number_tests, 1):
        result = pipeline.normalize(input_text)
        actual = result.normalized_text
        
        status = "✅ PASS" if actual.lower() == expected.lower() else "❌ FAIL"
        
        print(f"\nTest {i}:")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Actual:   '{actual}'")
        print(f"  Status:   {status}")
        
        if actual.lower() != expected.lower():
            print(f"  Difference: Expected '{expected}' but got '{actual}'")
    
    # Context triggers tests
    context_tests = [
        ("pijn bij tand 14", "pijn bij tand 14"),
        ("vulling in kies 47", "vulling in kies 47"),
        ("molaar 37", "molaar 37"),
        ("premolaar 15", "premolaar 15"),
        ("element 25", "element 25"),
        ("tand 11 heeft cariës", "tand 11 heeft cariës"),
    ]
    
    print(f"\n\n📋 DENTAL CONTEXT TESTS:")
    print("-" * 50)
    
    for i, (input_text, expected) in enumerate(context_tests, 1):
        result = pipeline.normalize(input_text)
        actual = result.normalized_text
        
        status = "✅ PASS" if actual.lower() == expected.lower() else "❌ FAIL"
        
        print(f"\nTest {i}:")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Actual:   '{actual}'")
        print(f"  Status:   {status}")
        
        if actual.lower() != expected.lower():
            print(f"  Difference: Expected '{expected}' but got '{actual}'")
    
    # Comma-separated tests (these should NOT be combined)
    comma_tests = [
        ("1, 2", "1, 2"),  # Should NOT become "element 12"
        ("2, 3", "2, 3"),  # Should NOT become "element 23"
        ("element 1, 2", "element 1, 2"),  # Should NOT become "element 12"
        ("1, 2, 3", "1, 2, 3"),  # Should NOT combine
    ]
    
    print(f"\n\n📋 COMMA-SEPARATED TESTS (should NOT combine):")
    print("-" * 50)
    
    for i, (input_text, expected) in enumerate(comma_tests, 1):
        result = pipeline.normalize(input_text)
        actual = result.normalized_text
        
        # For comma tests, we check that it does NOT contain combined elements
        contains_element_12 = "element 12" in actual
        contains_element_23 = "element 23" in actual
        contains_element_123 = "element 123" in actual
        
        has_incorrect_combination = contains_element_12 or contains_element_23 or contains_element_123
        status = "❌ FAIL" if has_incorrect_combination else "✅ PASS"
        
        print(f"\nTest {i}:")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}' (should NOT combine numbers)")
        print(f"  Actual:   '{actual}'")
        print(f"  Status:   {status}")
        
        if has_incorrect_combination:
            print(f"  Problem:  Incorrectly combined comma-separated numbers!")
            if contains_element_12:
                print(f"    - Found 'element 12' when it should be separate")
            if contains_element_23:
                print(f"    - Found 'element 23' when it should be separate")
            if contains_element_123:
                print(f"    - Found 'element 123' when it should be separate")
    
    # Hyphenated ranges (these SHOULD be combined)
    hyphen_tests = [
        ("1-4", "element 14"),
        ("2-6", "element 26"),
        ("element 1-4", "element 14"),
        ("tand 2-6", "tand 26"),
    ]
    
    print(f"\n\n📋 HYPHENATED RANGE TESTS (should combine):")
    print("-" * 50)
    
    for i, (input_text, expected) in enumerate(hyphen_tests, 1):
        result = pipeline.normalize(input_text)
        actual = result.normalized_text
        
        status = "✅ PASS" if actual.lower() == expected.lower() else "❌ FAIL"
        
        print(f"\nTest {i}:")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Actual:   '{actual}'")
        print(f"  Status:   {status}")
        
        if actual.lower() != expected.lower():
            print(f"  Difference: Expected '{expected}' but got '{actual}'")

    print(f"\n\n" + "=" * 80)
    print("TEST SUMMARY COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(show_all_test_results())