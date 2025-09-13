#!/usr/bin/env python3
"""
Test script to verify the comma removal fix works correctly.
"""

import re


class TestPostProcessor:
    def __init__(self, config=None):
        self.config = config or {}
        
    def apply(self, text):
        """Test the safer regex patterns matching actual pipeline implementation"""
        t = text
        
        # -- Test exclamation removal --
        if getattr(self, "remove_exclamations", False):
            t = t.replace("!", "")
        
        # -- Test question mark removal --
        if getattr(self, "remove_question_marks", False):
            t = t.replace("?", "")
        
        # -- Test semicolon removal --
        if getattr(self, "remove_semicolons", False):
            t = t.replace(";", "")
        
        # -- Test trailing word commas (only after letters, before space/EOL) --
        if getattr(self, "remove_trailing_word_commas", False):
            t = re.sub(r'(?<=[A-Za-zÀ-ÿ]),(?=\s|$)', '', t)
        
        # -- Test trailing commas at end of line (safer pattern) --
        if getattr(self, "remove_trailing_commas_eol", False):
            t = re.sub(r',\s*$', '', t)
            
        # -- Test sentence dots (preserve decimals) --
        if getattr(self, "remove_sentence_dots", False):
            t = re.sub(r'(?<!\d)\.(?!\d)', '', t)
            
        return t.strip()


def test_comma_removal():
    print("🧪 Testing comma removal fix...")
    
    # Create postprocessor with enabled flags - matching Supabase config
    processor = TestPostProcessor()
    processor.remove_exclamations = True
    processor.remove_question_marks = True  
    processor.remove_semicolons = True
    processor.remove_trailing_word_commas = True  # This should handle trailing commas after words
    processor.remove_trailing_commas_eol = True  # This handles commas at end of line
    processor.remove_sentence_dots = True
    
    test_cases = [
        ("karius,", "karius"),  # The failing test case
        ("cariës,", "cariës"),
        ("1,5 jaar", "1,5 jaar"),  # Should preserve decimal
        ("1, 2, 3", "1, 2, 3"),  # Should preserve list
        ("test, nog een test", "test, nog een test"),  # Should preserve mid-sentence commas
        ("eindkomma word weg,", "eindkomma word weg"),  # Should remove trailing comma
        ("comma aan einde van regel, \n", "comma aan einde van regel\n"),  # Should remove comma before newline
    ]
    
    print("\nTest results:")
    all_passed = True
    
    for input_text, expected in test_cases:
        result = processor.apply(input_text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
            
        print(f"{status} '{input_text}' → '{result}' (expected: '{expected}')")
    
    print(f"\n{'🎉 All tests PASSED!' if all_passed else '💥 Some tests FAILED!'}")
    return all_passed


if __name__ == "__main__":
    test_comma_removal()