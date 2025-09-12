#!/usr/bin/env python3
"""
Test script to demonstrate the vestibuleer → vestibulum issue
and verify the proposed top-1-only boost solution
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Initialize the matcher with the current configuration
config = {
    'matching': {
        'fuzzy_threshold': 0.84,
        'phonetic_enabled': True,
        'max_edit_distance': 2
    }
}

matcher = DutchPhoneticMatcher(config_data=config)

# Test case: vestibuleer should match vestibulair, not vestibulum
input_word = "vestibuleer"
candidates = ["vestibulair", "vestibulum", "buccaal", "linguaal", "palatinaal"]

print(f"Testing: {input_word}")
print("=" * 60)

# Calculate scores for all candidates
results = []
for candidate in candidates:
    # Get base similarity (without phonetic boost)
    base_score = matcher._fuzzy_match_raw(input_word, candidate)
    
    # Check if phonetically equal
    input_phonetics = matcher.to_phonetic(input_word)
    candidate_phonetics = matcher.to_phonetic(candidate)
    phonetic_match = any(ip in candidate_phonetics for ip in input_phonetics)
    
    # Get Soundex scores
    soundex_input = matcher._dutch_soundex(input_word)
    soundex_candidate = matcher._dutch_soundex(candidate)
    soundex_score = matcher.fuzzy_match(soundex_input, soundex_candidate)
    
    # Calculate final score (as done in match() method)
    final_score = min(base_score, 1.0)
    
    # Apply phonetic boost if conditions are met (current logic)
    boosted_score = final_score
    if phonetic_match:
        phonetic_boost_floor = 0.60
        min_len_for_boost = 5
        
        if final_score >= phonetic_boost_floor and len(input_word) >= min_len_for_boost and len(candidate) >= min_len_for_boost:
            boosted_score = max(final_score, 0.95)
            # Apply Soundex blend
            boosted_score = (boosted_score + soundex_score * 0.3) / 1.3
    
    results.append({
        'candidate': candidate,
        'base_score': base_score,
        'phonetic_match': phonetic_match,
        'soundex_score': soundex_score,
        'final_score': final_score,
        'boosted_score': boosted_score,
        'soundex_input': soundex_input,
        'soundex_candidate': soundex_candidate
    })

# Sort by boosted score
results.sort(key=lambda x: x['boosted_score'], reverse=True)

# Display results
print("Current Scoring (ALL candidates get boost if eligible):")
print("-" * 60)
for r in results:
    boost_indicator = " 🚀 BOOSTED" if r['boosted_score'] > r['final_score'] else ""
    print(f"{r['candidate']:15} | Base: {r['base_score']:.3f} | Phonetic: {r['phonetic_match']} | "
          f"Soundex: {r['soundex_score']:.3f} | Final: {r['boosted_score']:.3f}{boost_indicator}")
    print(f"                | Soundex: {r['soundex_input']} vs {r['soundex_candidate']}")

print("\n" + "=" * 60)

# Find the best base score
best_base = max(r['base_score'] for r in results)
print(f"Best base score: {best_base:.3f}")

# Show which would win with current logic
winner_current = results[0]
print(f"\nCurrent winner: {winner_current['candidate']} (score: {winner_current['boosted_score']:.3f})")

# Show what would happen with top-1-only boost
print("\n" + "=" * 60)
print("Proposed Top-1-Only Boost (only best base score gets boost):")
print("-" * 60)

# Recalculate with top-1-only logic
boost_epsilon = 0.0  # Strict top-1
for r in results:
    is_top = (best_base - r['base_score']) <= boost_epsilon
    
    # Reset to base score
    r['top1_score'] = min(r['base_score'], 1.0)
    
    # Only apply boost if this is the top candidate
    if is_top and r['phonetic_match']:
        phonetic_boost_floor = 0.60
        min_len_for_boost = 5
        
        if r['top1_score'] >= phonetic_boost_floor and len(input_word) >= min_len_for_boost and len(r['candidate']) >= min_len_for_boost:
            r['top1_score'] = max(r['top1_score'], 0.95)
            # Apply Soundex blend
            r['top1_score'] = (r['top1_score'] + r['soundex_score'] * 0.3) / 1.3
    
    boost_indicator = " 🎯 TOP-1 BOOST" if is_top and r['top1_score'] > min(r['base_score'], 1.0) else ""
    print(f"{r['candidate']:15} | Base: {r['base_score']:.3f} | Is Top: {is_top} | "
          f"Final: {r['top1_score']:.3f}{boost_indicator}")

# Sort by top-1 score
results.sort(key=lambda x: x['top1_score'], reverse=True)
winner_top1 = results[0]
print(f"\nTop-1-only winner: {winner_top1['candidate']} (score: {winner_top1['top1_score']:.3f})")

# Test other problematic cases
print("\n" + "=" * 60)
print("Testing other problematic case: interproximaal")
print("=" * 60)

input_word2 = "interproximaal"
candidates2 = ["interproximaal", "intermaxillair", "approximaal", "proximaal"]

results2 = []
for candidate in candidates2:
    base_score = matcher._fuzzy_match_raw(input_word2, candidate)
    results2.append({
        'candidate': candidate,
        'base_score': base_score
    })

results2.sort(key=lambda x: x['base_score'], reverse=True)

print("Base scores for 'interproximaal':")
for r in results2:
    exact_match = "✅ EXACT" if r['candidate'] == input_word2 else ""
    print(f"{r['candidate']:20} | Base: {r['base_score']:.3f} {exact_match}")

best_base2 = max(r['base_score'] for r in results2)
print(f"\nBest base score: {best_base2:.3f}")
print(f"With top-1-only boost, only '{results2[0]['candidate']}' would get phonetic boost")