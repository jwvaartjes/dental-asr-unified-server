#!/usr/bin/env python3
"""
Test script to diagnose why 'radiaal' is being matched to 'radiopaak'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher
from rapidfuzz import fuzz
import json

def test_radiaal_matching():
    """Test why 'radiaal' matches to 'radiopaak'"""
    
    print("🔍 Investigating 'radiaal' → 'radiopaak' matching issue\n")
    
    # Initialize matcher with empty lexicon for testing
    matcher = DutchPhoneticMatcher(lexicon={})
    
    # Test words
    input_word = "radiaal"
    problem_match = "radiopaak"
    
    # Also test some other potential matches to compare
    test_candidates = [
        "radiopaak",
        "radiaal",  # exact match if it exists
        "radiopaque",
        "radio",
        "radiale",
        "radiograaf"
    ]
    
    print(f"Input word: '{input_word}'")
    print(f"Problem match: '{problem_match}'")
    print("-" * 60)
    
    # Calculate fuzzy scores for each candidate
    print("\n📊 Fuzzy matching scores:")
    for candidate in test_candidates:
        # Basic fuzzy score
        basic_score = fuzz.ratio(input_word, candidate) / 100.0
        
        # Partial ratio (substring matching)
        partial_score = fuzz.partial_ratio(input_word, candidate) / 100.0
        
        # Token sort ratio (order-independent)
        token_sort_score = fuzz.token_sort_ratio(input_word, candidate) / 100.0
        
        # Weighted score (similar to what matcher uses)
        weighted_score = (basic_score * 0.5 + partial_score * 0.3 + token_sort_score * 0.2)
        
        print(f"\n  '{candidate}':")
        print(f"    Basic ratio:      {basic_score:.3f}")
        print(f"    Partial ratio:    {partial_score:.3f}")
        print(f"    Token sort ratio: {token_sort_score:.3f}")
        print(f"    Weighted score:   {weighted_score:.3f}")
        
        # Check phonetic boost eligibility
        if weighted_score >= 0.60 and len(candidate) >= 5:
            print(f"    ✅ Eligible for phonetic boost (score >= 0.60, length >= 5)")
            
            # Check morphological families
            input_family = matcher.get_morphological_family(input_word)
            candidate_family = matcher.get_morphological_family(candidate)
            
            print(f"    Input family: {input_family}")
            print(f"    Candidate family: {candidate_family}")
            
            if input_family and candidate_family and input_family != candidate_family:
                print(f"    ❌ Different families - boost blocked")
            elif not input_family or not candidate_family:
                print(f"    ⚠️ No family restriction - boost allowed")
            else:
                print(f"    ✅ Same family - boost allowed")
        else:
            print(f"    ❌ Not eligible for phonetic boost")
    
    print("\n" + "=" * 60)
    print("\n💡 Analysis:")
    print(f"The word 'radiaal' (adjective ending in -aal) is likely being matched")
    print(f"to 'radiopaak' due to:")
    print(f"1. High fuzzy match score (both start with 'radi')")
    print(f"2. Phonetic boost being applied despite different word types")
    print(f"3. Possible issue with morphological family detection")
    
    # Test the actual find_best_match method
    print("\n" + "=" * 60)
    print("\n🔬 Testing actual matcher.find_best_match():")
    
    # Create a small test lexicon
    test_lexicon = {
        "radiopaak": ["radiopaak", "radiopaque"],
        "radiaal": ["radiaal", "radiale"],
        "radio": ["radio"]
    }
    
    # Create matcher with test lexicon
    test_matcher = DutchPhoneticMatcher(lexicon=test_lexicon)
    
    # Test the matching
    result = test_matcher.find_best_match(input_word, threshold=0.5)
    
    if result:
        print(f"\nBest match found: '{result[0]}' with score {result[1]:.3f}")
    else:
        print("\nNo match found above threshold")
    
    return result

if __name__ == "__main__":
    test_radiaal_matching()