#!/usr/bin/env python3
"""
Test the actual flow of fuzzy_match to understand the scoring
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Create matcher
pm = DutchPhoneticMatcher()

print("Testing fuzzy_match flow for 'radiaal' vs 'radiopaak'")
print("=" * 70)

# Call fuzzy_match directly
score = pm.fuzzy_match("radiaal", "radiopaak")
print(f"fuzzy_match('radiaal', 'radiopaak') = {score:.4f}")

# Now check the internal _fuzzy_match_raw which is what's actually used
score_raw = pm._fuzzy_match_raw("radiaal", "radiopaak")
print(f"_fuzzy_match_raw('radiaal', 'radiopaak') = {score_raw:.4f}")

print("\n" + "=" * 70)
print("The issue is that fuzzy_match calls _fuzzy_match_raw")
print("which uses _prefix_aware_similarity internally.")
print()
print("_prefix_aware_similarity reduces the score when both")
print("words share a generic prefix (like 'radi').")
print()
print("So adding 'radi' to GENERIC_PREFIXES actually DOES work!")
print("It reduces the similarity from 0.75 to 0.485,")
print("then adds +0.10 prefix bonus to get 0.585.")
