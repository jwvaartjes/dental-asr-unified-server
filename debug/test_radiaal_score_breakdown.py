#!/usr/bin/env python3
"""
Detailed breakdown of why 'radiaal' gets a score of 0.85 with 'radiopaak'
"""

import sys
import os
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

def analyze_score(word1, word2):
    """Analyze score calculation in detail"""
    print(f"\n{'='*70}")
    print(f"Analyzing: '{word1}' vs '{word2}'")
    print('='*70)
    
    # Create matcher
    pm = DutchPhoneticMatcher()
    
    # Normalize text
    word1_norm = pm.normalize_text(word1)
    word2_norm = pm.normalize_text(word2)
    print(f"\nNormalized:")
    print(f"  '{word1}' -> '{word1_norm}'")
    print(f"  '{word2}' -> '{word2_norm}'")
    
    # Calculate raw SequenceMatcher ratio
    raw_ratio = SequenceMatcher(None, word1_norm, word2_norm).ratio()
    print(f"\n1. Base SequenceMatcher ratio: {raw_ratio:.4f}")
    
    # Check prefix match
    prefix_bonus = 0.0
    if word1_norm.startswith(word2_norm[:3]) or word2_norm.startswith(word1_norm[:3]):
        prefix_bonus = 0.1
        print(f"\n2. Prefix bonus (both start with '{word1_norm[:3]}'): +{prefix_bonus:.2f}")
    else:
        print(f"\n2. No prefix bonus ('{word1_norm[:3]}' vs '{word2_norm[:3]}')")
    
    # Check suffix match
    suffix_bonus = 0.0
    if word1_norm.endswith(word2_norm[-3:]) or word2_norm.endswith(word1_norm[-3:]):
        suffix_bonus = 0.05
        print(f"\n3. Suffix bonus (both end with same 3 chars): +{suffix_bonus:.2f}")
    else:
        print(f"\n3. No suffix bonus ('{word1_norm[-3:]}' vs '{word2_norm[-3:]}')")
    
    # Check vowel reduction
    vowel_bonus = 0.0
    if len(word1_norm) > len(word2_norm):
        for double, single in [('aa', 'a'), ('ee', 'e'), ('oo', 'o'), ('uu', 'u')]:
            if double in word1_norm:
                word1_reduced = word1_norm.replace(double, single, 1)
                if word1_reduced == word2_norm:
                    vowel_bonus = 0.15
                    print(f"\n4. Vowel reduction bonus (perfect match after reduction): +{vowel_bonus:.2f}")
                    break
                elif abs(len(word1_reduced) - len(word2_norm)) <= 1:
                    reduction_sim = SequenceMatcher(None, word1_reduced, word2_norm).ratio()
                    if reduction_sim > 0.9:
                        vowel_bonus = 0.08
                        print(f"\n4. Vowel reduction bonus (high similarity after reduction): +{vowel_bonus:.2f}")
                        break
    
    if vowel_bonus == 0:
        print(f"\n4. No vowel reduction bonus")
    
    # Calculate total
    total_raw = raw_ratio + prefix_bonus + suffix_bonus + vowel_bonus
    print(f"\n{'='*50}")
    print(f"TOTAL (before capping):")
    print(f"  Base ratio:      {raw_ratio:.4f}")
    print(f"  Prefix bonus:    +{prefix_bonus:.2f}")
    print(f"  Suffix bonus:    +{suffix_bonus:.2f}")
    print(f"  Vowel bonus:     +{vowel_bonus:.2f}")
    print(f"  {'='*30}")
    print(f"  Raw total:       {total_raw:.4f}")
    
    # Now get the actual fuzzy_match score
    actual_score = pm.fuzzy_match(word1, word2)
    print(f"\n  Actual fuzzy_match: {actual_score:.4f}")
    print(f"  Capped at 1.0:      {min(total_raw, 1.0):.4f}")
    
    # Verify our calculation matches
    if abs(actual_score - min(total_raw, 1.0)) < 0.0001:
        print(f"\n✅ Our calculation matches the actual implementation!")
    else:
        print(f"\n❌ Discrepancy: calculated {min(total_raw, 1.0):.4f} but got {actual_score:.4f}")
    
    return actual_score

# Test cases
test_pairs = [
    ("radiaal", "radiopaak"),
    ("radiaal", "radiaal"),
    ("radiaal", "radix"),
    ("lich", "laesie"),
]

print("DETAILED SCORE BREAKDOWN")
print("========================")

for word1, word2 in test_pairs:
    score = analyze_score(word1, word2)
    
    # Check against threshold
    threshold = 0.86  # Current threshold
    if score >= threshold:
        print(f"\n⚠️  Would match (score {score:.4f} >= threshold {threshold})")
    else:
        print(f"\n✓  Would NOT match (score {score:.4f} < threshold {threshold})")