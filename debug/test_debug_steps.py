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
    
    # Test case that's failing - periapicaal fix
    test_input = "periapicaal"
    result = pipeline.normalize(test_input)
    
    print(f"Input: '{test_input}'")
    print("=" * 50)
    print(f"Final result: '{result.normalized_text}'")
    print(f"Expected: 'peri-apicaal'")
    
    if result.normalized_text == 'peri-apicaal':
        print("✅ SUCCESS: periapicaal hyphen fix works!")
    else:
        print("❌ FAILED: periapicaal hyphen fix needs more work")

asyncio.run(test())