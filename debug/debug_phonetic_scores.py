#!/usr/bin/env python3
"""
Debug the exact phonetic scores for radiaal -> radiopaak
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
from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

def calculate_sequence_ratio(s1, s2):
    """Calculate SequenceMatcher ratio like the phonetic matcher does"""
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

async def debug_phonetic_scores():
    print("🔍 Debug: Phonetic Scores for radiaal -> radiopaak")
    print("=" * 60)
    
    # Initialize DataRegistry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Get the phonetic matcher
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully")
    
    # Find the phonetic matcher in the pipeline
    phonetic_normalizer = None
    for step in pipeline.steps:  # Use steps instead of _steps
        if hasattr(step, 'fuzzy_threshold'):  # This should be the learnable normalizer
            # Get the phonetic matcher from the learnable normalizer
            if hasattr(step, 'matchers'):
                for category, matcher in step.matchers.items():
                    if isinstance(matcher, DutchPhoneticMatcher):
                        phonetic_normalizer = matcher
                        print(f"✅ Found phonetic matcher in category: {category}")
                        break
            break
    
    if not phonetic_normalizer:
        print("❌ Could not find phonetic matcher")
        return
    
    # Test the specific case
    input_text = "radiaal"
    target_term = "radiopaak"
    
    print(f"\n🔍 Analyzing: '{input_text}' -> '{target_term}'")
    print(f"📊 Fuzzy threshold: {phonetic_normalizer.fuzzy_threshold}")
    print(f"📊 Phonetic boost floor: {getattr(phonetic_normalizer, 'phonetic_boost_floor', 'Not found')}")
    
    # Calculate base fuzzy score
    base_score = phonetic_normalizer._fuzzy_match_raw(input_text, target_term)
    print(f"📊 Base fuzzy score: {base_score:.4f}")
    
    # Calculate SequenceMatcher ratio manually to verify
    manual_ratio = calculate_sequence_ratio(input_text.lower(), target_term.lower())
    print(f"📊 Manual SequenceMatcher ratio: {manual_ratio:.4f}")
    
    # Check phonetic representations
    input_phonetics = phonetic_normalizer.to_phonetic(input_text)
    target_phonetics = phonetic_normalizer.to_phonetic(target_term)
    
    print(f"📊 Input phonetics: {input_phonetics}")
    print(f"📊 Target phonetics: {target_phonetics}")
    
    # Check if they're phonetically equal
    phonetic_match = False
    for inp_phon in input_phonetics:
        for targ_phon in target_phonetics:
            if inp_phon == targ_phon:
                phonetic_match = True
                print(f"📊 Phonetic match found: {inp_phon} == {targ_phon}")
                break
        if phonetic_match:
            break
    
    if not phonetic_match:
        print("📊 No phonetic match found")
    
    # Calculate Dutch Soundex score if phonetic match
    soundex_score = 0.0
    if phonetic_match:
        soundex_score = phonetic_normalizer.fuzzy_match(
            phonetic_normalizer._dutch_soundex(input_text),
            phonetic_normalizer._dutch_soundex(target_term)
        )
        print(f"📊 Soundex score: {soundex_score:.4f}")
    
    # Calculate final score with boost (if applicable)
    final_score = min(base_score, 1.0)
    
    # Check boost conditions from the phonetic matcher code
    phonetic_boost_floor = 0.70  # We set this
    min_len_for_boost = 5
    
    boost_conditions = [
        f"base_score >= floor: {base_score:.4f} >= {phonetic_boost_floor} = {base_score >= phonetic_boost_floor}",
        f"phonetic_match: {phonetic_match}",
        f"min_length: len('{input_text}') >= {min_len_for_boost} = {len(input_text) >= min_len_for_boost}",
        f"target length: len('{target_term}') >= {min_len_for_boost} = {len(target_term) >= min_len_for_boost}"
    ]
    
    print("\n📊 Boost conditions:")
    for condition in boost_conditions:
        print(f"   {condition}")
    
    should_boost = (base_score >= phonetic_boost_floor and 
                   phonetic_match and 
                   len(input_text) >= min_len_for_boost and 
                   len(target_term) >= min_len_for_boost)
    
    if should_boost:
        # Apply boost logic from the matcher
        final_score = max(final_score, 0.95)
        # Blend with Soundex
        final_score = (final_score + soundex_score * 0.3) / 1.3
        print(f"📊 Boost applied - final score: {final_score:.4f}")
    else:
        print(f"📊 No boost applied - final score: {final_score:.4f}")
    
    # Check if it passes the threshold
    passes_threshold = final_score >= phonetic_normalizer.fuzzy_threshold
    print(f"📊 Passes threshold ({phonetic_normalizer.fuzzy_threshold}): {passes_threshold}")
    
    # Test the actual match method
    print("\n🧪 Testing actual match method:")
    candidates = ["radiopaak", "radiaal", "lateraal", "apicaal"]  # Include some alternatives
    match_result = phonetic_normalizer.match(input_text, candidates)
    
    if match_result:
        matched_term, score = match_result
        print(f"✅ Match found: '{matched_term}' with score {score:.4f}")
    else:
        print("❌ No match found")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_phonetic_scores())