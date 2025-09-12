#!/usr/bin/env python3
"""
Quick test script for Dutch number word pairs
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def main():
    # Setup
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    # Test cases
    test_cases = [
        "cariës op een vier",
        "twee vier en drie vijf", 
        "een vierkant",
        "1 4",
        "element 14",
        "1, 2",  # Should NOT become element 12
        "element 1, 2"  # Should NOT become element 12
    ]
    
    print("Testing Dutch word pairs:")
    print("=" * 50)
    
    for test_input in test_cases:
        result = pipeline.normalize(test_input)
        print(f"Input:  '{test_input}'")
        print(f"Output: '{result.normalized_text}'")
        print()

if __name__ == "__main__":
    asyncio.run(main())