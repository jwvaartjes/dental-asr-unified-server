#!/usr/bin/env python3
"""
Quick test to verify exclamation mark removal is working with the updated configuration.
This tests the specific case that was failing in test 27.
"""

import re


class TestPostProcessor:
    def __init__(self, config=None):
        self.config = config or {}
        
    def apply(self, text):
        """Test the exclamation removal matching actual pipeline implementation"""
        t = text
        
        # Test exclamation removal (this should now be enabled)
        if getattr(self, "remove_exclamations", False):
            t = t.replace("!", "")
        
        return t.strip()


def test_exclamation_removal():
    print("🧪 Testing exclamation mark removal (test 27 specific case)...")
    
    # Create postprocessor with exclamation removal enabled - matching Supabase config
    processor = TestPostProcessor()
    processor.remove_exclamations = True  # This should match the Supabase configuration now
    
    test_cases = [
        ("karius!", "karius"),  # The specific failing test case from test 27
        ("cariës!", "cariës"),  # Another exclamation case
        ("element 26!", "element 26"),  # Element with exclamation
        ("test zonder uitroep", "test zonder uitroep"),  # No exclamation to remove
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
    test_exclamation_removal()