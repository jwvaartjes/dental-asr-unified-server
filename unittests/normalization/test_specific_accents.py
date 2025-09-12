#!/usr/bin/env python3
"""
Test the specific accent cases mentioned by the user
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ai.normalization.pipeline import NormalizationPipeline
from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader

async def test_specific_accent_cases():
    print("🧪 Testing specific accent normalization cases...")
    print("=" * 70)
    
    # Initialize data registry with proper Supabase connection
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    # Load admin components (contains the lexicon with diacritics)
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    lexicon_data = await data_registry.get_lexicon(admin_id)
    config_data = await data_registry.get_config(admin_id)
    protected_words = await data_registry.get_protected_words(admin_id)
    custom_patterns = await data_registry.get_custom_patterns(admin_id)
    
    # Create normalization pipeline
    pipeline = NormalizationPipeline(
        lexicon_data=lexicon_data or {},
        config=config_data or {}
    )
    
    print("✅ Pipeline initialized with diacritics restoration")
    print(f"✅ Restoration map has {len(pipeline._diacritics_restore_map)} entries")
    print()
    
    # The 3 specific test cases from the user
    test_cases = [
        {
            "input": "cariës distaal van de 1-4",
            "expected": "cariës distaal van element 14",
            "description": "Accent preservation with element parsing"
        },
        {
            "input": "cariës op 1 2", 
            "expected": "cariës op element 12",
            "description": "Accent preservation with comma-less element parsing"
        },
        {
            "input": "tand 11 heeft cariës",
            "expected": "tand 11 heeft cariës", 
            "description": "Simple accent preservation"
        }
    ]
    
    print("🔍 Testing specific accent preservation cases:")
    print("-" * 70)
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        input_text = case["input"]
        expected = case["expected"]
        description = case["description"]
        
        result = pipeline.normalize(input_text)
        actual = result.normalized_text
        
        # Check if the result matches expected
        success = actual == expected
        
        # Specifically check if cariës is preserved
        has_accent = "cariës" in actual
        loses_accent = "caries" in actual and "cariës" not in actual
        
        if success:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
            
        print(f"{status} Test {i}: {description}")
        print(f"    Input:    '{input_text}'")
        print(f"    Expected: '{expected}'")
        print(f"    Actual:   '{actual}'")
        
        if has_accent:
            print(f"    ✅ Accent preserved: 'cariës' found")
        elif loses_accent:
            print(f"    ❌ Accent lost: 'cariës' → 'caries'")
        
        # Show debug info
        debug = result.debug
        if 'diacritics_safety_net' in debug:
            print(f"    Debug - Safety Net: '{debug['diacritics_safety_net']}'")
        if 'phonetic' in debug:
            print(f"    Debug - Phonetic:   '{debug['phonetic']}'")
        
        print()
    
    print("=" * 70)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL accent preservation tests PASSED!")
        print("✅ The Dutch 'cariës' accent is properly preserved!")
    else:
        print("⚠️  Some accent preservation tests FAILED")
        print("❌ The Dutch 'cariës' accent issue still needs attention")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_specific_accent_cases())