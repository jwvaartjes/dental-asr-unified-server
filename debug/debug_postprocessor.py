#!/usr/bin/env python3
"""
Debug postprocessor to see what config options are removing the period
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

async def debug_postprocessor():
    print("🔍 Debugging postprocessor config and behavior...")
    print("=" * 70)

    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)

    # Create pipeline
    pipeline = await NormalizationFactory.create_for_admin(data_registry)

    # Access postprocessor
    postprocessor = pipeline.postprocessor
    print(f"🔧 Postprocessor: {type(postprocessor)}")
    print(f"🔧 Config: {postprocessor.config}")

    # Test postprocessor directly
    test_cases = ["ca.", "Ca.", "ca", "ca. test", "test ca.", "test ca. more"]

    print(f"\n🧪 Testing postprocessor directly:")
    for test in test_cases:
        result = postprocessor.apply(test)
        status = "✅" if result == test else "❌"
        print(f"   '{test}' -> '{result}' {status}")

    # Test individual config options
    print(f"\n🧪 Testing specific config flags:")

    config_flags = [
        'remove_exclamations',
        'remove_question_marks',
        'remove_semicolons',
        'remove_trailing_commas_eol',
        'remove_sentence_dots',
        'remove_trailing_dots',
        'remove_trailing_word_commas'
    ]

    for flag in config_flags:
        if postprocessor.config.get(flag, False):
            print(f"   ⚠️  {flag}: {postprocessor.config[flag]} (ACTIVE)")
        else:
            print(f"   ✅ {flag}: {postprocessor.config.get(flag, False)} (inactive)")

if __name__ == "__main__":
    asyncio.run(debug_postprocessor())