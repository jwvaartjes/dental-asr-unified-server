#!/usr/bin/env python3
"""
Debug script to check what canonicals contain periapicaal variants
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.ai.normalization.factory import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.loader_supabase import SupabaseLoader
from app.data.cache.cache_memory import InMemoryCache

async def check_canonicals():
    # Initialize data registry and pipeline
    loader = SupabaseLoader()
    cache = InMemoryCache()
    data_registry = DataRegistry(loader=loader, cache=cache)

    pipeline = await NormalizationFactory.create_for_admin(data_registry)

    # Get canonicals list
    canonicals = pipeline.canonicals

    print(f"🔍 Searching canonicals for periapicaal variations...")
    print("=" * 60)

    # Find all periapicaal-related entries
    periapicaal_entries = []
    for canonical in canonicals:
        if 'periapicaal' in canonical.lower() or 'peri-apicaal' in canonical.lower():
            periapicaal_entries.append(canonical)

    print(f"📚 Found {len(periapicaal_entries)} periapicaal-related canonical entries:")
    for i, entry in enumerate(sorted(periapicaal_entries), 1):
        print(f"   {i}. '{entry}'")

    # Check if both forms exist
    has_with_hyphen = 'peri-apicaal' in canonicals
    has_without_hyphen = 'periapicaal' in canonicals

    print(f"\n🔍 Canonical form analysis:")
    print(f"   'peri-apicaal' (with hyphen) in canonicals: {has_with_hyphen}")
    print(f"   'periapicaal' (without hyphen) in canonicals: {has_without_hyphen}")

    if has_without_hyphen:
        print(f"\n🚨 PROBLEM IDENTIFIED:")
        print(f"   Both 'periapicaal' and 'peri-apicaal' are in canonicals!")
        print(f"   The phonetic matcher finds exact match with 'periapicaal' (score 1.0)")
        print(f"   and returns it instead of the preferred hyphenated form.")

        print(f"\n💡 SOLUTION:")
        print(f"   Remove 'periapicaal' from canonicals, keep only 'peri-apicaal'")
        print(f"   Or prioritize hyphenated forms in the matching logic")
    elif has_with_hyphen and not has_without_hyphen:
        print(f"\n✅ Canonicals look correct - only hyphenated form present")
        print(f"   The issue might be in the matching algorithm")
    else:
        print(f"\n❓ Neither form found in canonicals - check data loading")

if __name__ == "__main__":
    asyncio.run(check_canonicals())