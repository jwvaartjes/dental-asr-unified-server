#!/usr/bin/env python3
"""
Debug script to show normalization steps
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
    
    # Test case that's failing
    test_input = "een twee weken"
    result = pipeline.normalize(test_input, debug=True)
    
    print(f"Input: '{test_input}'")
    print("=" * 50)
    print("Normalization steps:")
    for step_name, step_result in result.debug.items():
        print(f"  {step_name}: '{step_result}'")
    print("=" * 50)
    print(f"Final result: '{result.normalized_text}'")
    print(f"Expected: 'een twee weken'")

asyncio.run(test())