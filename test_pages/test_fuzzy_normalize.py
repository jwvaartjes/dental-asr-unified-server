#!/usr/bin/env python3
"""
Test the DutchPhoneticMatcher normalize() method directly with actual canonicals
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

async def test_fuzzy_normalize():
    print("🔍 Testing DutchPhoneticMatcher.normalize() method directly")
    print("=" * 70)
    
    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    # Get data
    lexicon_data = await data_registry.get_lexicon(admin_id)
    config_data = await data_registry.get_config(admin_id)
    
    # Create phonetic matcher
    matcher = DutchPhoneticMatcher(config_data=config_data)
    
    # Extract all canonical terms from lexicon
    canonicals = []
    for category, items in lexicon_data.items():
        if isinstance(items, list):
            canonicals.extend(items)
        elif isinstance(items, dict):
            canonicals.extend(items.keys())
    
    # Filter to valid strings only
    canonicals = [c for c in canonicals if isinstance(c, str) and c.strip()]
    print(f"📝 Total canonical terms: {len(canonicals)}")
    
    # Get fuzzy threshold
    fuzzy_threshold = config_data.get("phonetic", {}).get("threshold", 0.8)
    print(f"🎯 Fuzzy threshold: {fuzzy_threshold}")
    
    # Test problematic cases
    test_cases = [
        "lich-mucosaal",
        "lich",
        "mucosaal", 
        "mesio-occlusaal",
        "mesio",
        "interproximaal"
    ]
    
    print(f"\n🧪 Testing normalize() method with {len(canonicals)} canonicals:")
    print("-" * 70)
    
    for test_input in test_cases:
        print(f"\n🔍 Input: '{test_input}'")
        
        # Use the normalize method that's actually called in the pipeline
        result = matcher.normalize(test_input, canonicals)
        
        print(f"   Output: '{result}'")
        
        if result != test_input:
            print(f"   🔥 CHANGED: '{test_input}' → '{result}'")
            
            # Find what it matched to
            words = test_input.split()
            result_words = result.split()
            
            for i, (orig_word, new_word) in enumerate(zip(words, result_words)):
                if orig_word != new_word:
                    print(f"      Word {i+1}: '{orig_word}' → '{new_word}'")
                    
                    # Test this word individually
                    match_result = matcher.match(orig_word.lower(), canonicals)
                    if match_result and len(match_result) >= 2:
                        matched_word, score = match_result[0], match_result[1]
                        if score >= fuzzy_threshold:
                            print(f"         Match: '{matched_word}' (score: {score:.3f})")
        else:
            print(f"   ✅ UNCHANGED")

if __name__ == "__main__":
    asyncio.run(test_fuzzy_normalize())