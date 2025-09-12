#!/usr/bin/env python3
"""
Quick test to verify that compound word functionality works correctly
"""

from app.ai.normalization.pipeline import DefaultCustomPatternNormalizer

def test_compound_words():
    """Test the compound word functionality"""
    
    # Test patterns
    patterns = {
        "direct_mappings": {
            "karius": "cariës"
        }
    }
    
    # Create normalizer with punctuation preservation enabled (default)
    normalizer = DefaultCustomPatternNormalizer(patterns, preserve_punctuation=True)
    
    test_cases = [
        # Basic cases (should remove punctuation)
        ("karius", "cariës"),
        ("karius!", "cariës"),
        ("karius,", "cariës"),
        ("karius.", "cariës"),
        
        # Compound words (should preserve hyphens and slashes, and trailing punctuation)
        ("karius-achtige", "cariës-achtige"),
        ("karius/achtige", "cariës/achtige"),
        ("karius-achtige!", "cariës-achtige!"),  # Trailing punctuation is preserved for compound words
        ("karius/lesie,", "cariës/lesie,"),      # Trailing punctuation is preserved for compound words
    ]
    
    print("🧪 Testing compound word functionality:")
    print("=" * 50)
    
    all_passed = True
    for input_text, expected in test_cases:
        result = normalizer.apply(input_text)
        passed = result == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} '{input_text}' → '{result}' {'(expected: ' + expected + ')' if not passed else ''}")
        
        if not passed:
            all_passed = False
    
    print("=" * 50)
    print(f"Overall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    test_compound_words()