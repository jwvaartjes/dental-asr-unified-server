#!/usr/bin/env python3
"""
Debug script to trace periapicaal normalization issue step by step
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.ai.normalization.factory import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.loader_supabase import SupabaseLoader
from app.data.cache.cache_memory import InMemoryCache

async def test_periapicaal_debug():
    # Initialize data registry and pipeline
    loader = SupabaseLoader()
    cache = InMemoryCache()
    data_registry = DataRegistry(loader=loader, cache=cache)

    pipeline = await NormalizationFactory.create_for_admin(data_registry)

    # Test input
    test_input = "periapicaal"

    print(f"🔍 Testing: '{test_input}'")
    print("=" * 60)

    # Check if canonical hyphenated terms are in the canonicals list
    print(f"📚 Canonical hyphenated terms in pipeline:")
    print(f"   CANONICAL_HYPHENATED set: {pipeline.CANONICAL_HYPHENATED}")

    # Check if canonicals list contains the hyphenated forms
    canonicals = pipeline.canonicals
    hyphenated_in_canonicals = [c for c in canonicals if 'peri-apicaal' in c.lower()]
    print(f"   'peri-apicaal' variations in canonicals: {hyphenated_in_canonicals}")

    # Test phonetic matcher directly
    print(f"\n🔬 Testing phonetic matcher directly:")
    phonetic_result = pipeline.phonetic_matcher.match(test_input, canonicals)
    if phonetic_result:
        matched_term, score = phonetic_result
        print(f"   ✅ Match found: '{matched_term}' (score: {score:.3f})")
    else:
        print(f"   ❌ No match found")

    # Test the normalize method specifically
    print(f"\n🧪 Testing phonetic matcher normalize method:")
    normalized = pipeline.phonetic_matcher.normalize(test_input, canonicals)
    print(f"   Result: '{normalized}'")

    # Full pipeline test
    print(f"\n🚀 Full pipeline test:")
    result = pipeline.normalize(test_input)
    print(f"   Final result: '{result.normalized_text}'")
    print(f"   Expected: 'peri-apicaal'")

    # Check if the issue is in the phonetic matcher or elsewhere
    if phonetic_result and phonetic_result[0] == 'peri-apicaal':
        if result.normalized_text != 'peri-apicaal':
            print(f"   🚨 Issue: Phonetic matcher found correct match but pipeline returned wrong result!")
        else:
            print(f"   ✅ SUCCESS: Both phonetic matcher and pipeline work correctly!")
    else:
        print(f"   🚨 Issue: Phonetic matcher is not finding the correct match")

    return result.normalized_text == 'peri-apicaal'

if __name__ == "__main__":
    success = asyncio.run(test_periapicaal_debug())
    exit(0 if success else 1)