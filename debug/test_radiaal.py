#!/usr/bin/env python3
"""
Test script to diagnose why 'radiaal' is being matched to 'radiopaak'
"""

import sys
import os
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('..'))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher
from difflib import SequenceMatcher

def test_radiaal_matching():
    print("🔍 Testing phonetic matching for 'radiaal' → 'radiopaak'")
    print("="*60)
    
    # Initialize matcher
    matcher = DutchPhoneticMatcher(fuzzy_threshold=0.84)
    
    # Test words
    input_word = "radiaal"
    candidates = ["radiopaak", "radiolucent", "radix", "radiolucentie"]
    
    print(f"\n📝 Input: '{input_word}'")
    print(f"📚 Candidates: {candidates}")
    print("\n" + "="*60)
    
    # Check phonetic representations
    print("\n🔊 Phonetic representations:")
    input_phonetics = matcher.to_phonetic(input_word)
    print(f"  '{input_word}': {input_phonetics}")
    
    for candidate in candidates:
        cand_phonetics = matcher.to_phonetic(candidate)
        print(f"  '{candidate}': {cand_phonetics}")
        
        # Check for phonetic match
        phonetic_match = False
        for inp_phon in input_phonetics:
            for cand_phon in cand_phonetics:
                if inp_phon == cand_phon:
                    phonetic_match = True
                    print(f"    ✅ Phonetic match found: '{inp_phon}'")
                    break
    
    print("\n" + "="*60)
    print("\n📊 Scoring details:")
    
    # Test each candidate
    for candidate in candidates:
        print(f"\n  Testing: '{input_word}' vs '{candidate}'")
        
        # Base fuzzy score
        base_score = SequenceMatcher(None, input_word.lower(), candidate.lower()).ratio()
        print(f"    Base fuzzy score: {base_score:.4f}")
        
        # Check morphological families
        input_family = matcher._suffix_family(input_word)
        cand_family = matcher._suffix_family(candidate)
        families_compatible = matcher._families_compatible(input_word, candidate)
        
        print(f"    Morphological family (input): {input_family}")
        print(f"    Morphological family (candidate): {cand_family}")
        print(f"    Families compatible: {families_compatible}")
        
        # Check if phonetic boost would apply
        phonetic_boost_floor = 0.60
        min_len_for_boost = 5
        
        boost_eligible = (
            base_score >= phonetic_boost_floor and 
            len(input_word) >= min_len_for_boost and 
            len(candidate) >= min_len_for_boost
        )
        
        print(f"    Boost eligible (base >= {phonetic_boost_floor}, len >= {min_len_for_boost}): {boost_eligible}")
        
        # Try actual matching
        result = matcher.match(input_word, [candidate])
        if result:
            matched_word, score = result
            print(f"    ✨ Final match: '{matched_word}' with score {score:.4f}")
        else:
            print(f"    ❌ No match (below threshold)")
    
    print("\n" + "="*60)
    print("\n🎯 Full matching test with all candidates:")
    result = matcher.match(input_word, candidates)
    if result:
        matched_word, score = result
        print(f"  Result: '{input_word}' → '{matched_word}' (score: {score:.4f})")
    else:
        print(f"  No match found")

if __name__ == "__main__":
    test_radiaal_matching()
