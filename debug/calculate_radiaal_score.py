#!/usr/bin/env python3
"""
Calculate exact fuzzy match scores between 'radiaal' and 'radiopaak'
"""

import sys
sys.path.insert(0, '/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace/pairing_server')

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Initialize matcher
matcher = DutchPhoneticMatcher()

# Test words
word1 = "radiaal"
word2 = "radiopaak"

print(f"Analyzing match between '{word1}' and '{word2}'")
print("=" * 60)

# Calculate base fuzzy score
from difflib import SequenceMatcher
base_score = SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
print(f"\n1. Base fuzzy score (Levenshtein): {base_score:.4f}")

# Calculate phonetic representations
phonetic1 = matcher._dutch_soundex(word1)
phonetic2 = matcher._dutch_soundex(word2)
print(f"\n2. Phonetic representations:")
print(f"   '{word1}' -> '{phonetic1}'")
print(f"   '{word2}' -> '{phonetic2}'")

# Calculate phonetic similarity
phonetic_score = SequenceMatcher(None, phonetic1, phonetic2).ratio()
print(f"   Phonetic similarity: {phonetic_score:.4f}")

# Check morphological families
print(f"\n3. Morphological analysis:")
print(f"   '{word1}' ends with '-aal' (adjective suffix)")
print(f"   '{word2}' ends with '-aak' (no clear morphological pattern)")

# Calculate what the final score would be with different thresholds
print(f"\n4. Score analysis with phonetic boost:")
phonetic_boost_floor = 0.70  # Current threshold
if base_score >= phonetic_boost_floor:
    boosted_score = base_score * 0.85 + phonetic_score * 0.15
    print(f"   With threshold 0.70: base {base_score:.4f} >= 0.70")
    print(f"   Boosted score: {boosted_score:.4f}")
else:
    print(f"   With threshold 0.70: base {base_score:.4f} < 0.70")
    print(f"   No boost applied, final score: {base_score:.4f}")

# Try with higher threshold
phonetic_boost_floor = 0.75
print(f"\n5. With higher threshold (0.75):")
if base_score >= phonetic_boost_floor:
    boosted_score = base_score * 0.85 + phonetic_score * 0.15
    print(f"   Base {base_score:.4f} >= 0.75")
    print(f"   Boosted score: {boosted_score:.4f}")
else:
    print(f"   Base {base_score:.4f} < 0.75")
    print(f"   No boost applied, final score: {base_score:.4f}")

# Check if it would match with current scoring
print(f"\n6. Match decision:")
print(f"   Typical match threshold: 0.84")
print(f"   Base score {base_score:.4f} {'>' if base_score > 0.84 else '<'} 0.84")
if base_score > 0.84:
    print(f"   ✓ Would match even without phonetic boost!")
else:
    print(f"   ✗ Should not match without boost")

# Check actual matching through the matcher
print(f"\n7. Testing through actual matcher:")
result = matcher.find_best_match(word1, [word2, "radiaal", "radiculair"])
print(f"   Best match for '{word1}': '{result[0]}' (score: {result[1]:.4f})")