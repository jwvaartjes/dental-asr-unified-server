#!/usr/bin/env python3
"""
Trace normalization step by step to see where 'ca.' gets changed back to 'ca'
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def trace_normalization_steps():
    print("🔍 Tracing 'circa' normalization step by step...")
    print("=" * 70)

    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)

    # Create pipeline
    pipeline = await NormalizationFactory.create_for_admin(data_registry)

    print("\n🧪 Running full normalization with debug info...")
    test_input = "circa"
    result = pipeline.normalize(test_input)

    print(f"Input: '{test_input}'")
    print(f"Final Output: '{result.normalized_text}'")

    if hasattr(result, 'debug') and result.debug:
        print(f"\n📊 Step-by-step trace:")
        steps = [
            "input",
            "protected_wrap",
            "elements",
            "learnable",
            "custom_patterns",
            "hyphen_split",
            "variants",
            "phonetic",
            "diacritics_safety_net",
            "post",
            "unwrapped"
        ]

        for step in steps:
            if step in result.debug:
                value = result.debug[step]
                print(f"  {step:20} : '{value}'")

    # Also test some variations
    print(f"\n🧪 Testing variations:")
    test_cases = ["circa", "ca.", "ca", "Ca.", "Ca"]

    for test_case in test_cases:
        result = pipeline.normalize(test_case)
        print(f"  '{test_case}' -> '{result.normalized_text}'")

if __name__ == "__main__":
    asyncio.run(trace_normalization_steps())