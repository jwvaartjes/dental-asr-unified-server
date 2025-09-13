#!/usr/bin/env python3
"""
Debug script to see why both phonetic steps are running
"""

import asyncio
import sys
import os
from difflib import SequenceMatcher

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def debug_both_steps():
    print("🔍 Debug: Why both phonetic steps are running")
    print("=" * 60)
    
    # Initialize DataRegistry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Get the pipeline
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully")
    print(f"📊 enable_phonetic_matching flag: {pipeline.flags.get('enable_phonetic_matching')}")
    
    # Test the specific case that was problematic
    test_input = "radiaal"
    
    print(f"\n🧪 Testing: '{test_input}'")
    
    # Get detailed debug info
    result = pipeline.normalize(test_input)
    
    print(f"📊 Final result: '{result.normalized_text}'")
    print(f"📊 Changed: {'YES' if test_input != result.normalized_text else 'NO'}")
    
    if result.debug:
        print("\n🔍 Debug steps:")
        for step, value in result.debug.items():
            print(f"   {step}: '{value}'")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_both_steps())