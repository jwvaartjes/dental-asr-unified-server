#!/usr/bin/env python3
"""
Debug script to test why "bot verlies" is not normalizing to "botverlies"
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def test_bot_verlies():
    print("🔍 Testing 'bot verlies' normalization issue...")
    print("=" * 70)
    
    # Initialize DataRegistry exactly like the test script
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Create pipeline for admin user
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully")
    
    # First, let's check what's in the lexicon variants
    print("\n📋 Checking lexicon_data variants...")
    if hasattr(pipeline, 'variant_generator'):
        vg = pipeline.variant_generator
        if hasattr(vg, '_replacer') and hasattr(vg._replacer, 'compiled'):
            print(f"Found {len(vg._replacer.compiled)} compiled variant rules")
            # Check if "bot verlies" is in there
            for pattern, replacement, preserve in vg._replacer.compiled[:20]:  # Show first 20
                if 'bot' in pattern.pattern or 'verlies' in pattern.pattern:
                    print(f"  Pattern: {pattern.pattern}")
                    print(f"  Replacement: {replacement}")
                    print(f"  Preserve punct: {preserve}")
                    print()
    
    # Test cases specifically for "bot verlies"
    test_cases = [
        ('bot verlies', 'botverlies'),
        ('bot-verlies', 'botverlies'),
        ('Bot verlies van element 16', 'botverlies van element 16'),
        ('Patient heeft bot verlies', 'Patient heeft botverlies'),
        ('30% bot verlies', '30% botverlies'),
    ]
    
    print("\n🧪 Testing specific 'bot verlies' cases:")
    print("-" * 70)
    
    all_passed = True
    for test_input, expected in test_cases:
        print(f"\n📝 Input: '{test_input}'")
        print(f"   Expected: '{expected}'")
        
        # Run normalization
        result = pipeline.normalize(test_input)
        actual = result.normalized_text
        
        # Check result
        success = actual == expected
        status = "✅ PASS" if success else "❌ FAIL"
        
        print(f"   Actual:   '{actual}'")
        print(f"   Status:   {status}")
        
        if not success:
            all_passed = False
            print(f"   💥 ERROR: Expected '{expected}' but got '{actual}'")
            
            # Show debug info
            if hasattr(result, 'debug'):
                print("\n   Debug trace:")
                for step, value in result.debug.items():
                    if value != test_input and value != actual:
                        print(f"     {step}: '{value}'")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        
        # Additional debugging: check if variants are actually loaded
        print("\n🔍 Additional debugging - checking variant configuration:")
        
        # Check if the lexicon has variants
        if hasattr(pipeline, 'lexicon'):
            variants = pipeline.lexicon.get('variants', {})
            if 'bot verlies' in variants:
                print(f"  ✅ Found 'bot verlies' → '{variants['bot verlies']}' in lexicon variants")
            else:
                print("  ❌ 'bot verlies' NOT found in lexicon variants")
                print(f"  📋 First 10 variants found:")
                for i, (k, v) in enumerate(list(variants.items())[:10]):
                    print(f"     {i+1}. '{k}' → '{v}'")

if __name__ == "__main__":
    asyncio.run(test_bot_verlies())