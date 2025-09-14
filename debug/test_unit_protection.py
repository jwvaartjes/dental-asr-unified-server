#!/usr/bin/env python3
"""
Test that temporal units are now properly protected from element parsing
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
        # Temporal units should NOT become elements
        ('12 weken', '12 weken'),
        ('14 dagen', '14 dagen'),
        ('24 uur', '24 uur'),
        ('3 maanden', '3 maanden'),
        ('2 jaar', '2 jaar'),
        
        # Measurement units are protected from element parsing AND compacted
        ('15 mm', '15mm'),  # Postprocessing compacts units
        ('30 %', '30%'),    # Postprocessing compacts units
        ('12 cm', '12cm'),  # Postprocessing compacts units
        
        # Decimal numbers with units
        ('1,5 jaar', '1,5 jaar'),
        ('2,5 mm', '2,5mm'),  # Postprocessing compacts units
        
        # Element parsing should still work when no units
        ('1 4', 'element 14'),
        ('2 3', 'element 23'),
        ('element 1 4', 'element 14'),
        ('tand 2 3', 'tand 23'),
        
        # Mixed cases
        ('element 14 en 12 weken', 'element 14 en 12 weken'),
        ('15 mm diep en element 16', '15mm diep en element 16'),  # Postprocessing compacts units
    ]
    
    print("Testing unit protection with FULL list (measurement + temporal)")
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
        print("✅ ALL TESTS PASS - Units properly protected from element parsing!")
    else:
        print("❌ SOME TESTS FAILED")
    
asyncio.run(test())