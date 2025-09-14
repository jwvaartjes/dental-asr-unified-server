#!/usr/bin/env python3
"""
Test primary teeth parsing (51-55, 61-65, 71-75, 81-85)
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
    
    tests = [
        # Primary teeth in molar context
        ('molaar 7 5', 'molaar 75'),
        ('molaar 6 4', 'molaar 64'),
        ('molaar 5 3', 'molaar 53'),
        ('molaar 8 2', 'molaar 82'),
        
        # Primary teeth in other dental contexts
        ('tand 7 5', 'tand 75'),
        ('kies 6 1', 'kies 61'),
        ('element 5 5', 'element 55'),
        
        # Make sure permanent teeth still work
        ('molaar 1 6', 'molaar 16'),
        ('molaar 2 7', 'molaar 27'),
        ('molaar 3 8', 'molaar 38'),
        ('molaar 4 6', 'molaar 46'),
        
        # Mixed cases
        ('molaar 7 5 en element 14', 'molaar 75 en element 14'),
        ('tand 8 5 distaal', 'tand 85 distaal'),
    ]
    
    print("Testing PRIMARY TEETH NUMBER PARSING")
    print("Primary teeth ranges: 51-55, 61-65, 71-75, 81-85")
    print("=" * 70)
    
    all_pass = True
    for input_text, expected in tests:
        result = pipeline.normalize(input_text)
        status = '✅' if result.normalized_text == expected else '❌'
        if status == '❌':
            all_pass = False
        print(f'{status} "{input_text}" → "{result.normalized_text}" (expected: "{expected}")')
    
    print("=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASS - Primary teeth numbers working correctly!")
    else:
        print("❌ SOME TESTS FAILED")
    
asyncio.run(test())