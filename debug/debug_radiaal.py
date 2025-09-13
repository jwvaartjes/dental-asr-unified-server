#!/usr/bin/env python3
"""
Debug script to trace what happens to 'radiaal' through the normalization pipeline
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

async def debug_radiaal():
    print("🔍 Debug: Tracing 'radiaal' through normalization pipeline")
    print("=" * 60)
    
    # Initialize DataRegistry exactly like the test script
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Create pipeline for admin user
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully")
    
    # Test the specific case
    test_input = "radiaal"
    print(f"\n🔍 Testing input: '{test_input}'")
    
    # Run normalization with debug info
    result = pipeline.normalize(test_input, language="nl")
    
    print(f"📥 Input: '{test_input}'")
    print(f"📤 Output: '{result.normalized_text}'")
    print(f"🔢 Steps taken: {len(result.debug)}")
    
    # Show debug steps
    for i, step in enumerate(result.debug, 1):
        print(f"Step {i}: {step}")
    
    print("\n" + "=" * 60)
    
    # Test if it passes any specific step
    print("🔍 Let's check the learnable normalizer directly:")
    
    # Get the learnable normalizer
    learnable_normalizer = None
    for step in pipeline.steps:
        if hasattr(step, 'normalize_dynamic'):
            learnable_normalizer = step
            break
    
    if learnable_normalizer:
        print("✅ Found learnable normalizer")
        
        # Test direct call
        match_result = learnable_normalizer.normalize_dynamic(test_input)
        if match_result:
            matched_term, category, match_type = match_result
            print(f"🎯 Direct match found: '{matched_term}' (category: {category}, type: {match_type})")
            
            # Check each matcher
            print("\n🔍 Checking individual matchers:")
            for category, matcher in learnable_normalizer.matchers.items():
                if hasattr(matcher, 'match_with_info'):
                    result = matcher.match_with_info(test_input)
                    if result:
                        matched_term, info = result
                        score = info.get('confidence', info.get('score', 0))
                        match_type = info.get('match_type', 'unknown')
                        print(f"  {category}: '{matched_term}' (score: {score:.3f}, type: {match_type})")
                    else:
                        print(f"  {category}: No match")
                elif hasattr(matcher, 'match'):
                    result = matcher.match(test_input)
                    if result:
                        if isinstance(result, tuple):
                            matched_term, score = result
                            print(f"  {category}: '{matched_term}' (score: {score:.3f})")
                        else:
                            print(f"  {category}: '{result}' (no score)")
                    else:
                        print(f"  {category}: No match")
                else:
                    print(f"  {category}: Unknown matcher type")
        else:
            print("❌ No match found in learnable normalizer")
    else:
        print("❌ Could not find learnable normalizer")

if __name__ == "__main__":
    asyncio.run(debug_radiaal())