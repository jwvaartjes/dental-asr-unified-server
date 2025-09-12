#!/usr/bin/env python3
"""
Test specific failing test cases to understand what's happening
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
    
    # Test cases from failing tests
    test_cases = [
        # Hyphen handling
        ("licht-mucosale", "should become: licht mucosale"),
        ("voor-operatief", "should become: voor operatief"),
        ("db-radix", "should become: DB-radix (canonical term)"),
        ("mb-radix", "should become: MB-radix (canonical term)"),
        
        # Surface normalization  
        ("element 14 distaal", "should contain: distaal"),
        
        # Unit normalization
        ("5 mm", "should keep: 5mm or 5 mm"),
        ("2 procent", "should become: 2%"),
        
        # Phonetic variations
        ("elemet 14", "should become: element 14"),
        ("elemetn 16", "should become: element 16"),
    ]
    
    print("Testing specific failing cases:")
    print("=" * 60)
    
    for test_input, description in test_cases:
        result = pipeline.normalize(test_input)
        print(f"Input:       '{test_input}'")
        print(f"Output:      '{result.normalized_text}'") 
        print(f"Expected:    {description}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())