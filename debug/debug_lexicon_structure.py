#!/usr/bin/env python3
"""
Debug the exact lexicon structure to understand where periapicaal is coming from
"""

import asyncio
import sys
import os
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader

async def debug_lexicon_structure():
    print("🔍 Debugging lexicon structure for periapicaal...")
    print("=" * 80)

    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(loader=loader, cache=cache)

    admin_id = registry.loader.get_admin_id()
    lexicon_data = await registry.get_lexicon(admin_id)

    print("📚 Full lexicon structure:")
    for category, data in lexicon_data.items():
        print(f"\n📁 Category: {category}")
        print(f"   Type: {type(data)}")

        if isinstance(data, dict):
            print(f"   Dict with {len(data)} entries:")
            # Look for periapicaal entries
            peri_entries = {}
            for key, value in data.items():
                if 'peri' in key.lower() or (isinstance(value, str) and 'peri' in value.lower()):
                    peri_entries[key] = value

            if peri_entries:
                print("   🎯 PERI entries found:")
                for key, value in peri_entries.items():
                    print(f"      {key} -> {value}")
            else:
                print("   (no peri entries)")

        elif isinstance(data, list):
            print(f"   List with {len(data)} entries:")
            peri_entries = [item for item in data if isinstance(item, str) and 'peri' in item.lower()]
            if peri_entries:
                print("   🎯 PERI entries found:")
                for item in peri_entries:
                    print(f"      {item}")
            else:
                print("   (no peri entries)")
        else:
            if isinstance(data, str) and 'peri' in data.lower():
                print(f"   🎯 PERI string: {data}")

    print(f"\n" + "=" * 80)
    print("🔧 Now tracing how canonicals are built...")

    # Simulate the canonicals building process
    canonicals = []

    # Step 1: Extract from category-based lexicon structure
    for category_name, category_data in lexicon_data.items():
        print(f"\n📂 Processing category: {category_name}")
        if isinstance(category_data, list):
            print(f"   Adding {len(category_data)} list items to canonicals")
            canonicals.extend(category_data)
            peri_items = [item for item in category_data if isinstance(item, str) and 'peri' in item.lower()]
            if peri_items:
                print(f"   🎯 PERI items added: {peri_items}")
        elif isinstance(category_data, dict):
            print(f"   Adding {len(category_data)} dict KEYS to canonicals")
            canonicals.extend(category_data.keys())
            peri_keys = [key for key in category_data.keys() if 'peri' in key.lower()]
            if peri_keys:
                print(f"   🎯 PERI keys added: {peri_keys}")
                print(f"   🔍 What they map to:")
                for key in peri_keys:
                    print(f"      {key} -> {category_data[key]}")

    # Step 2: Add variants
    if 'variants' in lexicon_data:
        print(f"\n📂 Processing variants:")
        for source, dest in lexicon_data['variants'].items():
            if isinstance(dest, str) and dest.strip():
                canonicals.append(dest.strip())
                if 'peri' in source.lower() or 'peri' in dest.lower():
                    print(f"   🎯 PERI variant: {source} -> {dest}")

    # Final canonicals list
    unique_canonicals = sorted(set(canonicals), key=str.lower)
    peri_canonicals = [c for c in unique_canonicals if 'peri' in c.lower()]

    print(f"\n🎯 Final PERI canonicals ({len(peri_canonicals)}):")
    for c in peri_canonicals:
        print(f"   {c}")

if __name__ == "__main__":
    asyncio.run(debug_lexicon_structure())