#!/usr/bin/env python3
"""
Debug script to understand why "12 %" is still becoming "element 12%"
"""

import re

# Current regex patterns from pipeline.py
_ELEMENT_SIMPLE_RE = re.compile(r'([1-4])\s*[\- ,]?\s*([1-8])')
_UNIT_AFTER_RE = re.compile(r'^\s*(mm|cm|m|ml|mg|g|kg|µm|μm|um|%|‰|°c|°f)\b', re.IGNORECASE)

def debug_12_percent():
    text = "12 %"
    print(f"Original text: '{text}'")
    
    # Show what the element pattern matches
    matches = list(_ELEMENT_SIMPLE_RE.finditer(text))
    print(f"Element pattern matches: {len(matches)}")
    for i, match in enumerate(matches):
        print(f"  Match {i}: '{match.group(0)}' at position {match.start()}-{match.end()}")
        print(f"    Group 1: '{match.group(1)}', Group 2: '{match.group(2)}'")
        
        # Check what follows this match
        suffix = text[match.end():]
        print(f"    Suffix after match: '{suffix}'")
        unit_match = _UNIT_AFTER_RE.match(suffix)
        print(f"    Unit pattern matches suffix: {bool(unit_match)}")
        if unit_match:
            print(f"      Unit found: '{unit_match.group(1)}'")
    
    # Test the protection pattern
    protection_pattern = re.compile(r'(\d+)\s+(mm|cm|m|ml|mg|g|kg|µm|μm|um|%|‰|°c|°f)(?=\s|$)', re.IGNORECASE)
    protection_matches = list(protection_pattern.finditer(text))
    print(f"\nProtection pattern matches: {len(protection_matches)}")
    for i, match in enumerate(protection_matches):
        print(f"  Match {i}: '{match.group(0)}' - number: '{match.group(1)}', unit: '{match.group(2)}'")

if __name__ == "__main__":
    debug_12_percent()