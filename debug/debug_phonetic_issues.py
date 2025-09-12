#!/usr/bin/env python3
"""
Debug phonetic matching issues for specific failing test cases
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

async def debug_phonetic_matching():
    print("🔍 Debugging phonetic matching issues...")
    print("=" * 70)
    
    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    # Get lexicon data
    lexicon_data = await data_registry.get_lexicon(admin_id)
    print(f"📚 Loaded lexicon with {len(lexicon_data)} categories")
    
    # Get configuration
    config_data = await data_registry.get_config(admin_id)
    phonetic_config = config_data.get("phonetic", {})
    fuzzy_threshold = phonetic_config.get("threshold", 0.8)
    print(f"🎯 Fuzzy threshold: {fuzzy_threshold}")
    
    # Create phonetic matcher
    matcher = DutchPhoneticMatcher(config_data=config_data)
    
    # Extract all canonical terms from lexicon
    canonicals = []
    for category, items in lexicon_data.items():
        if isinstance(items, list):
            canonicals.extend(items)
        elif isinstance(items, dict):
            canonicals.extend(items.keys())
    
    print(f"📝 Total canonical terms: {len(canonicals)}")
    
    # Test problematic words
    test_cases = [
        "lich",
        "mesio", 
        "interproximaal",
        "frameprothese",
        "circa",
        "tandsteen",
        "fractuur"
    ]
    
    print("\n🧪 Testing problematic phonetic matches:")
    print("-" * 70)
    
    for test_word in test_cases:
        print(f"\n🔍 Testing: '{test_word}'")
        
        # Get top 5 matches
        matches = []
        for canonical in canonicals:
            if not canonical or not isinstance(canonical, str):
                continue
                
            match_result = matcher.match(test_word.lower(), [canonical])
            if match_result and len(match_result) >= 2:
                matched_word, score = match_result[0], match_result[1]
                if score >= 0.5:  # Show lower threshold matches for debugging
                    matches.append((matched_word, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        print(f"   Top matches (threshold={fuzzy_threshold}):")
        for i, (match, score) in enumerate(matches[:5]):
            indicator = "✅" if score >= fuzzy_threshold else "❌"
            print(f"      {i+1}. {indicator} {match} (score: {score:.3f})")
        
        if matches and matches[0][1] >= fuzzy_threshold:
            best_match, best_score = matches[0]
            print(f"   🎯 CHOSEN: '{test_word}' → '{best_match}' (score: {best_score:.3f})")
        else:
            print(f"   ⏭️  NO MATCH: '{test_word}' stays unchanged")
    
    print("\n" + "=" * 70)
    
    # Also test the compound issue
    print("\n🔍 Testing compound word matching:")
    compound_tests = ["lich-mucosaal", "mesio-occlusaal", "mesio-buccaal"]
    
    for compound in compound_tests:
        print(f"\n🧩 Testing compound: '{compound}'")
        
        # Test each part
        parts = compound.split('-')
        for part in parts:
            matches = []
            for canonical in canonicals:
                if not canonical or not isinstance(canonical, str):
                    continue
                    
                match_result = matcher.match(part.lower(), [canonical])
                if match_result and len(match_result) >= 2:
                    matched_word, score = match_result[0], match_result[1]
                    if score >= fuzzy_threshold:
                        matches.append((matched_word, score))
            
            matches.sort(key=lambda x: x[1], reverse=True)
            
            if matches:
                best_match, best_score = matches[0]
                print(f"      '{part}' → '{best_match}' (score: {best_score:.3f})")
            else:
                print(f"      '{part}' → no match")

if __name__ == "__main__":
    asyncio.run(debug_phonetic_matching())