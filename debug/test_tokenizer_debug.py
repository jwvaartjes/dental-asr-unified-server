#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.ai.normalization.pipeline import DefaultTokenizer

# Test tokenization of hyphenated words
tokenizer = DefaultTokenizer()

test_cases = [
    "licht-mucosaal",
    "peri-apicaal",
    "vestibulo-linguaal"
]

for text in test_cases:
    tokens = tokenizer.tokenize(text)
    print(f"'{text}' → {tokens}")
    
    # Test what happens if we process each token
    print("Processing each token:")
    for i, token in enumerate(tokens):
        print(f"  Token {i}: '{token}' (has hyphen: {'-' in token}, is alpha: {any(c.isalpha() for c in token)})")
    print()