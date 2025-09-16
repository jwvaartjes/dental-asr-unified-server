#!/usr/bin/env python3
"""
Debug TokenAwareReplacer to see exactly what's happening with circa
"""

import asyncio
import sys
import os
import re

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def debug_token_replacer():
    print("🔍 Debugging TokenAwareReplacer for 'circa'...")
    print("=" * 70)

    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)

    # Create pipeline
    pipeline = await NormalizationFactory.create_for_admin(data_registry)

    # Access the custom pattern normalizer
    custom_patterns = pipeline.custom_patterns
    print(f"🔧 Custom patterns found: {custom_patterns is not None}")

    if custom_patterns and hasattr(custom_patterns, '_replacer'):
        custom_replacer = custom_patterns._replacer
        print(f"🔧 Internal TokenAwareReplacer found: {custom_replacer is not None}")

        if custom_replacer and hasattr(custom_replacer, 'compiled'):
            print(f"🔧 Custom replacer has {len(custom_replacer.compiled)} compiled rules")

            # Find the circa rule
            circa_rule = None
            for i, (rx, dst, preserve) in enumerate(custom_replacer.compiled):
                pattern = rx.pattern
                if 'circa' in pattern.lower():
                    circa_rule = (rx, dst, preserve, i)
                    print(f"📏 Found circa rule #{i}:")
                    print(f"   Pattern: {pattern}")
                    print(f"   Destination: '{dst}'")
                    print(f"   Preserve: {preserve}")
                    break

            if circa_rule:
                rx, dst, preserve, rule_idx = circa_rule

                # Test the regex directly
                test_cases = ["circa", "circa.", "circa,", "circa test", "test circa", "test circa."]
                print(f"\n🧪 Testing regex pattern directly:")
                for test in test_cases:
                    match = rx.search(test)
                    if match:
                        print(f"   '{test}' -> Match: groups={match.groups()}")
                        print(f"     Full match: '{match.group(0)}'")
                        if match.groups():
                            print(f"     Group 1 (punctuation): '{match.group(1) if match.lastindex else 'None'}'")
                    else:
                        print(f"   '{test}' -> No match")

                # Test the replacer apply method
                print(f"\n🧪 Testing TokenAwareReplacer.apply():")
                for test in test_cases:
                    result = custom_replacer.apply(test)
                    print(f"   '{test}' -> '{result}'")

                # Test custom patterns apply method
                print(f"\n🧪 Testing DefaultCustomPatternNormalizer.apply():")
                for test in test_cases:
                    result = custom_patterns.apply(test)
                    print(f"   '{test}' -> '{result}'")

            else:
                print("❌ No circa rule found in compiled rules")
                print("🔍 Available patterns (first 10):")
                for i, (rx, dst, preserve) in enumerate(custom_replacer.compiled[:10]):
                    print(f"   #{i}: '{rx.pattern}' -> '{dst}' (preserve: {preserve})")

    else:
        print("❌ Could not find internal TokenAwareReplacer")

        # Try to access the pipeline internals differently
        print("🔍 Looking for pipeline attributes:")
        for attr in dir(pipeline):
            if not attr.startswith('_'):
                value = getattr(pipeline, attr)
                if hasattr(value, 'apply') or 'replacer' in attr.lower():
                    print(f"   {attr}: {type(value)}")

if __name__ == "__main__":
    asyncio.run(debug_token_replacer())