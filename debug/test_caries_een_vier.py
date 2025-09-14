#!/usr/bin/env python3
"""
Debug script to trace through normalization of 'cariës op een vier'
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
    
    # Test specifically "cariës op een vier"
    test_input = "cariës op een vier"
    
    print(f"Testing: '{test_input}'")
    print("=" * 70)
    
    # Enable debug mode if available
    result = pipeline.normalize(test_input)
    
    print(f"Result: '{result.normalized_text}'")
    print(f"Expected: 'cariës op element 14'")
    
    # Check debug steps
    if hasattr(result, 'debug') and result.debug:
        print("\nDebug trace:")
        for step_name, step_result in result.debug.items():
            print(f"  {step_name}: {step_result}")
    
    # Test other similar cases
    print("\n" + "=" * 70)
    print("Testing similar cases:")
    
    similar_tests = [
        ("een vier", "element 14"),
        ("twee vier", "element 24"),
        ("op een vier", "op element 14"),
        ("cariës een vier", "cariës element 14"),
        ("element een vier", "element 14"),
        ("tand een vier", "tand 14"),
    ]
    
    for test_input, expected in similar_tests:
        result = pipeline.normalize(test_input)
        status = '✅' if result.normalized_text == expected else '❌'
        print(f'{status} "{test_input}" → "{result.normalized_text}" (expected: "{expected}")')

asyncio.run(test())
