#!/usr/bin/env python3
"""
Test the effect of _space_separators_between_digits
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.factory import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.supabase_loader import SupabaseLoader
from app.data.cache.in_memory import InMemoryCache
import asyncio

async def test_spacing():
    # Initialize
    loader = SupabaseLoader()
    cache = InMemoryCache()
    data_registry = DataRegistry(loader=loader, cache=cache)
    await data_registry.initialize()
    
    pipeline = await NormalizationFactory.create_for_admin(data_registry)
    
    test_cases = [
        "1,5 jaar",
        "1,4",
        "element 1,4",
        "1, 2, 3",
        "15 mm",
        "2 weken",
        "3,5 maanden",
        "element 1-4",
        "tand 1,4"
    ]
    
    print("Testing with current pipeline (space_separators_between_digits ACTIVE):")
    print("=" * 70)
    
    for text in test_cases:
        result = pipeline.normalize(text, language="nl")
        print(f"'{text}' → '{result.normalized_text}'")
    
    print("\n" + "=" * 70)
    print("The _space_separators_between_digits method is in DefaultVariantGenerator")
    print("It adds spaces around commas between single digits: 1,5 → 1, 5")
    print("This affects decimal numbers incorrectly!")

if __name__ == "__main__":
    asyncio.run(test_spacing())
