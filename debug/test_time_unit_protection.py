#!/usr/bin/env python3
"""
Debug script to test that time units prevent element conversion
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.ai.normalization.factory import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.loader_supabase import SupabaseLoader
from app.data.cache.cache_memory import InMemoryCache

async def test():
    # Initialize data registry and pipeline
    loader = SupabaseLoader()
    cache = InMemoryCache()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    pipeline = await NormalizationFactory.create_for_admin(data_registry)
    
    # Test cases for time unit protection
    test_cases = [
        ("een twee weken", "een twee weken"),  # Should NOT become "element 12 weken"
        ("twee drie dagen", "twee drie dagen"),  # Should NOT become "element 23 dagen"
        ("drie vier maanden", "drie vier maanden"),  # Should NOT become "element 34 maanden"
        ("vijf zes jaar", "vijf zes jaar"),  # Should NOT become "element 56 jaar"
        ("een vier uur", "een vier uur"),  # Should NOT become "element 14 uur"
        
        # These should still convert to elements (no time units)
        ("een vier", "element 14"),
        ("twee drie", "element 23"),
        ("drie vier", "element 34"),
        ("element een vier", "element 14"),
        ("tand twee drie", "tand 23"),
        
        # Test with digits (already protected)
        ("15 weken", "15 weken"),  # Should stay as is
        ("12 dagen", "12 dagen"),  # Should stay as is
    ]
    
    print("Testing TIME UNIT PROTECTION")
    print("=" * 70)
    
    all_pass = True
    for input_text, expected in test_cases:
        result = pipeline.normalize(input_text)
        status = '✅' if result.normalized_text == expected else '❌'
        if status == '❌':
            all_pass = False
        print(f'{status} "{input_text}" → "{result.normalized_text}" (expected: "{expected}")')
    
    print("=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASS - Time units properly prevent element conversion!")
    else:
        print("❌ SOME TESTS FAILED - Time unit protection needs fixing")

asyncio.run(test())