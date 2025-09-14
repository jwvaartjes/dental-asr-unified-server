#!/usr/bin/env python3
"""
Simple debug to see why radiaal matches to radiopaak
"""

import sys
import os
# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Create matcher
pm = DutchPhoneticMatcher()

# Test direct fuzzy scores
test_word = "radiaal"
candidates = ["radiaal", "radiopaak", "radiale", "radiopaque", "radioactief"]

print(f"Testing '{test_word}' against candidates:")
print("-" * 60)

for candidate in candidates:
    # Get base fuzzy score using phonetic matcher's fuzzy_match method
    base_score = pm.fuzzy_match(test_word, candidate)
    
    # Check if phonetic match
    input_phonetics = set(pm.to_phonetic(test_word))
    candidate_phonetics = set(pm.to_phonetic(candidate))
    phonetic_match = bool(input_phonetics & candidate_phonetics)
    
    # Check morphological compatibility
    families_compatible = pm._families_compatible(test_word, candidate)
    
    print(f"\n'{test_word}' vs '{candidate}':")
    print(f"  Base fuzzy score: {base_score:.4f}")
    print(f"  Phonetic match: {phonetic_match}")
    print(f"  Phonetics: {input_phonetics} vs {candidate_phonetics}")
    print(f"  Families compatible: {families_compatible}")
    
    # Would it get boosted?
    if base_score >= 0.70 and len(test_word) >= 5 and len(candidate) >= 5:
        if phonetic_match and families_compatible:
            print(f"  -> Would get phonetic boost from {base_score:.4f} to 0.95")
        elif phonetic_match and not families_compatible:
            print(f"  -> Phonetic boost blocked by family incompatibility")
    
    # Soundex
    soundex_input = pm._dutch_soundex(test_word)
    soundex_cand = pm._dutch_soundex(candidate)
    soundex_score = pm.fuzzy_match(soundex_input, soundex_cand)
    print(f"  Soundex: '{soundex_input}' vs '{soundex_cand}' = {soundex_score:.4f}")
    
    # Final score after boost
    if base_score >= 0.70 and phonetic_match and families_compatible and len(test_word) >= 5:
        final = max(base_score, 0.95)
        final = (final + soundex_score * 0.3) / 1.3
        print(f"  Final score after boost: {final:.4f}")
