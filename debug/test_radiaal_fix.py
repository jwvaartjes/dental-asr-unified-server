#!/usr/bin/env python3
"""
Quick test to verify radiaal doesn't match to radiopaak anymore
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Create matcher
pm = DutchPhoneticMatcher()

# Test word
test_word = "radiaal"

# Check the fuzzy match score with radiopaak
score = pm.fuzzy_match(test_word, "radiopaak")

print(f"Testing with threshold {pm.fuzzy_threshold}")
print(f"Score for 'radiaal' vs 'radiopaak': {score:.4f}")

if score < pm.fuzzy_threshold:
    print(f"✅ PASS: Score {score:.4f} is below threshold {pm.fuzzy_threshold}")
    print("'radiaal' will NOT match to 'radiopaak'")
else:
    print(f"❌ FAIL: Score {score:.4f} is above threshold {pm.fuzzy_threshold}")
    print("'radiaal' would still match to 'radiopaak'")
