#!/usr/bin/env python3
"""
Test script to verify unit guard and unit compaction fixes
Tests the two reported issues:
1. "15 mm" should stay "15mm" (not become "element 15 mm")
2. "30 %" should compact to "30%"
"""

import sys
import os

# Add the parent directory to the path so we can import app module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ai.normalization.pipeline import NormalizationPipeline

def test_unit_guard_and_compaction():
    """Test both the unit guard and unit compaction functionality"""
    
    # Create a simple pipeline
    config = {
        "variant_generation": {
            "separators": ["-", " ", ",", ";", "/"],
            "element_separators": ["-", " ", ",", ";", "/"],
            "digit_words": {
                "één": "1", "twee": "2", "drie": "3", "vier": "4",
                "vijf": "5", "zes": "6", "zeven": "7", "acht": "8"
            }
        },
        "phonetic": {"threshold": 0.84},
        "normalization": {
            "enable_element_parsing": True,
            "enable_learnable": False,
            "enable_variant_generation": False,
            "enable_phonetic_matching": False,
            "enable_post_processing": True
        }
    }
    
    pipeline = NormalizationPipeline(lexicon_data={}, config=config)
    
    print("🧪 Testing Unit Guard and Compaction Fixes\n")
    print("=" * 50)
    
    # Test cases for both issues
    test_cases = [
        # Issue 1: Unit guard should prevent element conversion
        ("15 mm", "15mm", "Unit guard: prevent '15 mm' → 'element 15 mm'"),
        ("3 cm", "3cm", "Unit guard: prevent '3 cm' → 'element 3 cm'"), 
        ("25 mg", "25mg", "Unit guard: prevent '25 mg' → 'element 25 mg'"),
        ("12 %", "12%", "Unit guard: prevent '12 %' → 'element 12 %'"),
        
        # Issue 2: Unit compaction should work
        ("30 %", "30%", "Unit compaction: '30 %' → '30%'"),
        ("5 mm", "5mm", "Unit compaction: '5 mm' → '5mm'"),
        ("100 ml", "100ml", "Unit compaction: '100 ml' → '100ml'"),
        ("37 °C", "37°C", "Unit compaction: '37 °C' → '37°C'"),
        
        # Valid element conversion should still work
        ("1 4", "element 14", "Valid elements: '1 4' → 'element 14'"),
        ("element 2 3", "element 23", "Element context: 'element 2 3' → 'element 23'"),
        ("tand 3 1", "tand 31", "Dental context: 'tand 3 1' → 'tand 31'"),
        
        # Edge cases
        ("element 15 mm", "element 15mm", "Mixed: element with unit should compact"),
        ("tand 2 5 mm", "tand 25mm", "Mixed: dental element with unit"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_text, expected, description) in enumerate(test_cases, 1):
        result = pipeline.normalize(input_text, language="nl")
        actual = result.normalized_text
        
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        if actual == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"Test {i:2d}: {status}")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Actual:   '{actual}'")
        print(f"  Description: {description}")
        
        if actual != expected:
            print(f"  🚨 MISMATCH: Expected '{expected}' but got '{actual}'")
        
        print()
    
    print("=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Unit guard and compaction fixes are working correctly.")
        return True
    else:
        print(f"⚠️  {failed} test(s) failed. The fixes may need adjustment.")
        return False

if __name__ == "__main__":
    success = test_unit_guard_and_compaction()
    sys.exit(0 if success else 1)