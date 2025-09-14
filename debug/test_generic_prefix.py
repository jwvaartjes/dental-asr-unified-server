#!/usr/bin/env python3
"""
Test if generic prefix detection is working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

# Create matcher
pm = DutchPhoneticMatcher()

print("Testing Generic Prefix Detection")
print("=" * 70)
print(f"Generic prefixes list: {pm.GENERIC_PREFIXES}")
print("=" * 70)

# Test words
test_words = [
    "radiaal",
    "radiopaak", 
    "radix",
    "interproximaal",
    "interdentaal",
    "mesio-occlusaal",
    "distaal"
]

print("\nTesting _detect_generic_prefix method:")
print("-" * 50)
for word in test_words:
    prefix, core = pm._detect_generic_prefix(word)
    if prefix:
        print(f"'{word}' -> prefix: '{prefix}', core: '{core}'")
    else:
        print(f"'{word}' -> NO GENERIC PREFIX DETECTED")

print("\n" + "=" * 70)
print("Testing _prefix_aware_similarity for 'radiaal' vs 'radiopaak':")
print("-" * 50)

# Test the _prefix_aware_similarity method directly
similarity = pm._prefix_aware_similarity("radiaal", "radiopaak")
print(f"_prefix_aware_similarity('radiaal', 'radiopaak') = {similarity:.4f}")

# Also test with known generic prefix words
print("\nTesting with 'interproximaal' vs 'interdentaal':")
similarity = pm._prefix_aware_similarity("interproximaal", "interdentaal")
print(f"_prefix_aware_similarity('interproximaal', 'interdentaal') = {similarity:.4f}")

# Now let's check what happens in _fuzzy_match_raw
print("\n" + "=" * 70)
print("Testing _fuzzy_match_raw (which adds the prefix bonus):")
print("-" * 50)

# We need to check the actual code flow
import inspect
source = inspect.getsource(pm._fuzzy_match_raw)
# Find the line with prefix bonus
for i, line in enumerate(source.split('\n')):
    if 'startswith' in line and '0.1' in line:
        print(f"Line {i}: {line.strip()}")
        print("This is where the +0.10 prefix bonus is added!")
        break

print("\nThe problem: The prefix bonus at lines 280-281 doesn't check")
print("if the prefix is generic. It just adds +0.10 for ANY 3-char match!")