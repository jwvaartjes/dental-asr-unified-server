#!/usr/bin/env python3
"""
Test that invalid tooth numbers are NOT created by the dental context regex
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
        # Invalid tooth numbers should NOT be combined
        ('molaar 6 7', 'molaar 6 7'),  # 67 is not valid
        ('tand 5 9', 'tand 5 9'),      # 59 is not valid  
        ('kies 9 1', 'kies 9 1'),      # 91 is not valid
        ('element 6 7', 'element 6 7'), # 67 is not valid
        ('element 5 9', 'element 5 9'), # 59 is not valid
        
        # Valid primary teeth SHOULD be combined
        ('molaar 7 5', 'molaar 75'),    # 75 is valid (primary)
        ('molaar 6 4', 'molaar 64'),    # 64 is valid (primary)
        ('molaar 5 3', 'molaar 53'),    # 53 is valid (primary)
        ('molaar 8 2', 'molaar 82'),    # 82 is valid (primary)
        
        # Valid permanent teeth SHOULD be combined
        ('molaar 1 6', 'molaar 16'),    # 16 is valid (permanent)
        ('molaar 2 7', 'molaar 27'),    # 27 is valid (permanent)
        ('molaar 3 8', 'molaar 38'),    # 38 is valid (permanent)
        ('molaar 4 6', 'molaar 46'),    # 46 is valid (permanent)
        
        # Element context with invalid numbers
        ('element 6 7', 'element 6 7'), # 67 is not valid
        ('element 9 9', 'element 9 9'), # 99 is not valid
        
        # Element context with valid numbers
        ('element 1 4', 'element 14'),  # 14 is valid
        ('element 7 5', 'element 75'),  # 75 is valid (primary)
    ]
    
    print("Testing INVALID TOOTH NUMBER VALIDATION")
    print("Only valid tooth numbers should be combined!")
    print("Valid ranges: 11-18, 21-28, 31-38, 41-48 (permanent)")
    print("              51-55, 61-65, 71-75, 81-85 (primary)")
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
        print("✅ ALL TESTS PASS - Invalid tooth numbers are NOT being created!")
    else:
        print("❌ SOME TESTS FAILED")
    
asyncio.run(test())