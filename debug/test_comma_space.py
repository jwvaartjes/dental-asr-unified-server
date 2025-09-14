#!/usr/bin/env python3
"""
Debug why '1,5 jaar' becomes '1, 5 jaar'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Create matcher
pm = DutchPhoneticMatcher()

test_text = "1,5 jaar"
print(f"Testing: '{test_text}'")
print("=" * 70)

# Test normalize_text which handles preprocessing
normalized = pm.normalize_text(test_text)
print(f"After normalize_text: '{normalized}'")

# Let's check what happens in tokenization
tokens = test_text.split()
print(f"\nTokens: {tokens}")

# Check if preprocessing adds spaces
import re

# This is likely the culprit - preprocessing might add spaces around commas
test_patterns = [
    (r'(\d),(\d)', r'\1, \2'),  # Adds space after comma between digits
    (r'(\d+),(\d+)', r'\1, \2'),  # Same but for multi-digit
]

for pattern, replacement in test_patterns:
    result = re.sub(pattern, replacement, test_text)
    if result != test_text:
        print(f"\nPattern '{pattern}' changes:")
        print(f"  '{test_text}' -> '{result}'")
