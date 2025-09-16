#!/usr/bin/env python3
"""
Test script for configurable punctuation removal in postprocessing
"""

import sys
sys.path.append('/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace/pairing_server')

from app.ai.normalization.pipeline import DefaultPostProcessor

def test_punctuation_removal():
    """Test various punctuation removal configurations"""
    
    test_text = "Element 14! Dit is een test; met veel punctuatie? En ook komma's, natuurlijk."
    
    print("Original text:")
    print(f"  '{test_text}'")
    print()
    
    # Test 1: No punctuation removal (default)
    print("Test 1: No punctuation removal (default config)")
    processor = DefaultPostProcessor({})
    result = processor.apply(test_text)
    print(f"  Result: '{result}'")
    print()
    
    # Test 2: Remove exclamations only
    print("Test 2: Remove exclamations only")
    processor = DefaultPostProcessor({
        'remove_exclamations': True
    })
    result = processor.apply(test_text)
    print(f"  Result: '{result}'")
    print()
    
    # Test 3: Remove question marks only
    print("Test 3: Remove question marks only")
    processor = DefaultPostProcessor({
        'remove_question_marks': True
    })
    result = processor.apply(test_text)
    print(f"  Result: '{result}'")
    print()
    
    # Test 4: Remove semicolons only
    print("Test 4: Remove semicolons only")
    processor = DefaultPostProcessor({
        'remove_semicolons': True
    })
    result = processor.apply(test_text)
    print(f"  Result: '{result}'")
    print()
    
    # Test 5: Remove all configured punctuation
    print("Test 5: Remove all configured punctuation")
    processor = DefaultPostProcessor({
        'remove_exclamations': True,
        'remove_question_marks': True,
        'remove_semicolons': True
    })
    result = processor.apply(test_text)
    print(f"  Result: '{result}'")
    print()
    
    # Test 6: Test trailing dots removal (should not affect decimal numbers)
    print("Test 6: Test trailing dots removal")
    test_text_dots = "Dit is 3.5 mm groot. En nog een zin."
    processor = DefaultPostProcessor({
        'remove_trailing_dots': True
    })
    result = processor.apply(test_text_dots)
    print(f"  Input:  '{test_text_dots}'")
    print(f"  Result: '{result}'")
    print()
    
    # Test 7: Test trailing word commas removal (should not affect numbers)
    print("Test 7: Test trailing word commas removal")
    test_text_commas = "Eerst, dan 1,5 mm, en tot slot, klaar."
    processor = DefaultPostProcessor({
        'remove_trailing_word_commas': True
    })
    result = processor.apply(test_text_commas)
    print(f"  Input:  '{test_text_commas}'")
    print(f"  Result: '{result}'")
    print()

if __name__ == "__main__":
    test_punctuation_removal()