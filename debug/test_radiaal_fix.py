#!/usr/bin/env python3
"""
Test to verify that the radiaal -> radiopaak issue is fixed after disabling redundant phonetic step
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

async def test_radiaal_fix():
    print("🧪 Testing radiaal -> radiopaak fix after disabling redundant phonetic step")
    print("=" * 70)
    
    # Initialize DataRegistry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Get the pipeline
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully")
    
    # Test the specific case that was problematic
    test_cases = [
        "radiaal",
        "lateraal", 
        "apicaal",
        "interproximaal",
        "licht-mucosaal"
    ]
    
    print("🔍 Testing normalization with disabled redundant phonetic step:")
    print()
    
    for test_input in test_cases:
        try:
            result = pipeline.normalize(test_input)
            normalized = result.normalized_text
            
            # Check if input was changed
            is_changed = test_input != normalized
            status = "🔄 CHANGED" if is_changed else "✅ UNCHANGED"
            
            print(f"Input: '{test_input:15}' → Output: '{normalized:15}' {status}")
            
            # Special check for radiaal
            if test_input == "radiaal":
                if normalized == "radiaal":
                    print("   ✅ SUCCESS: radiaal is no longer mapped to radiopaak!")
                elif normalized == "radiopaak":
                    print("   ❌ STILL BROKEN: radiaal is still mapped to radiopaak")
                else:
                    print(f"   ⚠️  UNEXPECTED: radiaal mapped to '{normalized}' (not radiopaak)")
        
        except Exception as e:
            print(f"Input: '{test_input:15}' → ERROR: {str(e)}")
    
    print("\n" + "=" * 70)
    
    # Additional test: Verify pipeline flags
    print("\n🔧 Pipeline configuration check:")
    print(f"   enable_phonetic_matching: {pipeline.flags.get('enable_phonetic_matching')}")
    print(f"   enable_learnable: {pipeline.flags.get('enable_learnable')}")
    
    if not pipeline.flags.get('enable_phonetic_matching'):
        print("   ✅ Redundant phonetic step is DISABLED (correct)")
    else:
        print("   ❌ Redundant phonetic step is still ENABLED (incorrect)")
    
    print("\n🎯 Expected behavior:")
    print("   - 'radiaal' should remain as 'radiaal' (no phonetic matching)")
    print("   - Learnable normalizer still provides phonetic matching when appropriate")
    print("   - Other dental terms should work normally")

if __name__ == "__main__":
    asyncio.run(test_radiaal_fix())