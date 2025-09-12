#!/usr/bin/env python3
"""
Test script to verify the prefix-aware similarity fix for interproximaal issue.
Tests that "interproximaal" → "intermaxillair" is prevented by prefix-aware scoring.
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
        'max_edit_distance': 2,
        'boost_top_epsilon': 0.0  # Strict top-1 only boost
    }
}

matcher = DutchPhoneticMatcher(config_data=config)

print("=" * 80)
print("TESTING PREFIX-AWARE SIMILARITY FIX")
print("=" * 80)

# Test case 1: interproximaal should NOT match intermaxillair
input_word1 = "interproximaal"
candidates1 = ["interproximaal", "intermaxillair", "approximaal", "proximaal"]

print(f"\nTest 1: '{input_word1}' should stay as 'interproximaal'")
print("-" * 60)

results1 = []
for candidate in candidates1:
    # Get base similarity (without phonetic boost)
    base_score = matcher._fuzzy_match_raw(input_word1, candidate)
    
    # Check prefix detection
    prefix_input, core_input = matcher._detect_generic_prefix(input_word1)
    prefix_candidate, core_candidate = matcher._detect_generic_prefix(candidate)
    
    # Get prefix-aware similarity
    prefix_aware_score = matcher._prefix_aware_similarity(input_word1, candidate)
    
    results1.append({
        'candidate': candidate,
        'base_score': base_score,
        'prefix_input': f"'{prefix_input}' + '{core_input}'",
        'prefix_candidate': f"'{prefix_candidate}' + '{core_candidate}'",
        'prefix_aware_score': prefix_aware_score,
        'exact_match': candidate == input_word1
    })

# Sort by base score
results1.sort(key=lambda x: x['base_score'], reverse=True)

print("Base similarity scores (with prefix-aware logic):")
for r in results1:
    exact_indicator = " ✅ EXACT" if r['exact_match'] else ""
    print(f"{r['candidate']:15} | Base: {r['base_score']:.3f} | "
          f"Prefix-aware: {r['prefix_aware_score']:.3f} | "
          f"Input: {r['prefix_input']:20} | Candidate: {r['prefix_candidate']:20}{exact_indicator}")

print(f"\nWinner: {results1[0]['candidate']} (score: {results1[0]['base_score']:.3f})")
print(f"Expected: interproximaal should win with perfect 1.000 score")

# Test case 2: Verify other prefix combinations
print("\n" + "=" * 80)
print("Test 2: Other prefix combinations")
print("-" * 60)

test_pairs = [
    ("intrabuccaal", "intraoraal"),      # Same prefix, different cores
    ("periapicaal", "periodonticaal"),   # Same prefix, different cores  
    ("subgingivaal", "subgingival"),     # Same prefix, similar cores
    ("hyperkeratose", "hypermobiliteit"), # Same prefix, different cores
    ("mesioocclusaal", "distocclusaal"),  # Different prefixes
]

for word1, word2 in test_pairs:
    # Standard similarity
    standard_sim = matcher._fuzzy_match_raw(word1, word2)
    
    # Prefix analysis
    prefix1, core1 = matcher._detect_generic_prefix(word1)
    prefix2, core2 = matcher._detect_generic_prefix(word2)
    
    # Prefix-aware similarity 
    prefix_aware_sim = matcher._prefix_aware_similarity(word1, word2)
    
    same_prefix = prefix1 and prefix1 == prefix2
    
    print(f"{word1:15} ↔ {word2:15} | "
          f"Standard: {standard_sim:.3f} | Prefix-aware: {prefix_aware_sim:.3f} | "
          f"Same prefix: {same_prefix} ({prefix1} vs {prefix2})")

# Test case 3: Verify non-prefix words are unaffected
print("\n" + "=" * 80)
print("Test 3: Non-prefix words should be unaffected")
print("-" * 60)

non_prefix_pairs = [
    ("proximaal", "maxillair"),     # No prefixes
    ("buccaal", "linguaal"),        # No prefixes
    ("occlusaal", "gingivaal"),     # No prefixes  
]

for word1, word2 in non_prefix_pairs:
    # Standard similarity
    standard_sim = matcher._fuzzy_match_raw(word1, word2)
    
    # Prefix-aware similarity (should be same as standard)
    prefix_aware_sim = matcher._prefix_aware_similarity(word1, word2)
    
    difference = abs(standard_sim - prefix_aware_sim)
    
    print(f"{word1:15} ↔ {word2:15} | "
          f"Standard: {standard_sim:.3f} | Prefix-aware: {prefix_aware_sim:.3f} | "
          f"Difference: {difference:.6f}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

success_criteria = [
    ("interproximaal wins over intermaxillair", results1[0]['candidate'] == 'interproximaal'),
    ("interproximaal has perfect score", abs(results1[0]['base_score'] - 1.0) < 0.001),
    ("intermaxillair gets lower score due to prefix-aware logic", 
     next(r for r in results1 if r['candidate'] == 'intermaxillair')['base_score'] < 0.7)
]

print("\nTest Results:")
for criterion, passed in success_criteria:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} {criterion}")

all_passed = all(passed for _, passed in success_criteria)
final_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
print(f"\n{final_status}")

if all_passed:
    print("\n🎉 The prefix-aware similarity fix is working correctly!")
    print("   - 'interproximaal' correctly stays as 'interproximaal'")
    print("   - Generic prefix 'inter' no longer dominates similarity scoring")
    print("   - Core word differences ('proximaal' vs 'maxillair') are properly weighted")
else:
    print("\n⚠️  The fix needs adjustment. Check the scoring logic.")