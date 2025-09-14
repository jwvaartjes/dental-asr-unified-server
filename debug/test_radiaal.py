#!/usr/bin/env python3
"""
Debug script to test why "radiaal" is incorrectly matching to "radiopaak"
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def test_radiaal():
    print("🔍 Testing 'radiaal' → 'radiopaak' issue...")
    print("=" * 70)
    
    # Initialize DataRegistry exactly like the test script
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Create pipeline for admin user
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully")
    
    # Test cases for "radiaal"
    test_cases = [
        ('radiaal', 'radiaal'),  # Should stay as is
        ('radiale', 'radiaal'),  # Should normalize to radiaal
        ('radiopaak', 'radiopaak'),  # Should stay as is
    ]
    
    print("\n🧪 Testing 'radiaal' cases:")
    print("-" * 70)
    
    all_passed = True
    for test_input, expected in test_cases:
        print(f"\n📝 Input: '{test_input}'")
        print(f"   Expected: '{expected}'")
        
        # Run normalization
        result = pipeline.normalize(test_input)
        actual = result.normalized_text
        
        # Check result
        success = actual == expected
        status = "✅ PASS" if success else "❌ FAIL"
        
        print(f"   Actual:   '{actual}'")
        print(f"   Status:   {status}")
        
        if not success:
            all_passed = False
            print(f"   💥 ERROR: Expected '{expected}' but got '{actual}'")
            
            # Show debug info
            if hasattr(result, 'debug'):
                print("\n   Debug trace:")
                for step, value in result.debug.items():
                    if value != test_input and value != actual:
                        print(f"     {step}: '{value}'")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        
        # Additional debugging: check phonetic matcher settings
        print("\n🔍 Additional debugging - checking phonetic matcher configuration:")
        
        if hasattr(pipeline, 'phonetic_matcher'):
            pm = pipeline.phonetic_matcher
            print(f"  Phonetic enabled: {pm.phonetic_enabled}")
            print(f"  Boost top epsilon: {pm.boost_top_epsilon}")
            
            # Test direct matching with verbose output
            print("\n  Direct phonetic matcher test with scoring details:")
            
            # Monkey-patch to get detailed scores
            original_method = pm._find_best_phonetic_match
            
            def debug_find_best(input_text, candidates, threshold=0.84):
                print(f"\n  >>> Testing '{input_text}' against candidates:")
                
                # Get scores for all candidates
                scores = []
                for candidate in candidates:
                    base_score = pm.fuzzy_match(input_text, candidate)
                    scores.append((candidate, base_score))
                
                # Sort by score
                scores.sort(key=lambda x: x[1], reverse=True)
                
                # Show top 10 scores
                print(f"  Top candidates by base fuzzy score:")
                for i, (cand, score) in enumerate(scores[:10]):
                    print(f"    {i+1}. '{cand}': {score:.4f}")
                    
                    # Check if phonetic boost would apply
                    if score >= 0.70 and len(input_text) >= 5 and len(cand) >= 5:
                        print(f"       -> Would get phonetic boost to 0.95")
                
                # Call original method
                return original_method(input_text, candidates, threshold)
            
            pm._find_best_phonetic_match = debug_find_best
            
            # Test radiaal
            result = pm.normalize("radiaal")
            print(f"\n  Final result: 'radiaal' → '{result}'")

if __name__ == "__main__":
    asyncio.run(test_radiaal())
