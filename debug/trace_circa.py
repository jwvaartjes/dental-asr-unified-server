#!/usr/bin/env python3
"""
Trace exactly what happens to 'circa' during normalization
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

async def trace_circa():
    print("🔍 Tracing 'circa' normalization step by step...")
    print("=" * 70)

    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)

    # Create pipeline
    pipeline = await NormalizationFactory.create_for_admin(data_registry)

    print("\n📚 Checking loaded lexicon data for 'circa'...")
    admin_id = data_registry.loader.get_admin_id()
    lexicon_data = await data_registry.get_lexicon(admin_id)

    # Find all 'circa' entries
    def find_circa_entries(data, path=""):
        entries = []
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                if "circa" in key.lower():
                    entries.append(f"{current_path}: {value}")
                if isinstance(value, str) and "circa" in value.lower():
                    entries.append(f"{current_path} = '{value}' (contains circa)")
                entries.extend(find_circa_entries(value, current_path))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                entries.extend(find_circa_entries(item, f"{path}[{i}]"))
        return entries

    circa_entries = find_circa_entries(lexicon_data)
    print(f"Found {len(circa_entries)} entries containing 'circa':")
    for entry in circa_entries:
        print(f"  {entry}")

    print("\n🧪 Testing normalization of 'circa'...")
    test_input = "circa"
    result = pipeline.normalize(test_input)

    print(f"Input: '{test_input}'")
    print(f"Output: '{result.normalized_text}'")
    print(f"Steps taken: {len(result.steps) if hasattr(result, 'steps') else 'N/A'}")

    # Check if we can access internal pipeline data
    print(f"\n🔧 Pipeline canonicals contain circa variations:")
    if hasattr(pipeline, 'canonicals'):
        circa_canonicals = [c for c in pipeline.canonicals if 'circa' in c.lower() or 'ca.' in c.lower()]
        for c in circa_canonicals:
            print(f"  '{c}'")

    # Test with different variations
    test_cases = ["circa", "circa ", " circa ", "circa 5mm", "circa test"]

    print(f"\n🧪 Testing multiple circa variations:")
    for test_case in test_cases:
        result = pipeline.normalize(test_case)
        print(f"  '{test_case}' -> '{result.normalized_text}'")

if __name__ == "__main__":
    asyncio.run(trace_circa())