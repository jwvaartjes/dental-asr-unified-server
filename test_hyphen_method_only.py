#!/usr/bin/env python3

# Simple test to debug the hyphen splitting method directly

text = "licht-mucosaal"
print(f"Input: '{text}'")
print(f"Has hyphen: {'-' in text}")

# Simulate the canonical check
canonical_hyphenated = {
    'peri-apicaal', 'peri-apicale', 'inter-occlusaal', 'inter-occlusale',
    'supra-gingivaal', 'sub-gingivaal', 'pre-molaar', 'post-operatief',
    'extra-oraal', 'intra-oraal', 'co-morbiditeit', 're-interventie'
}

text_lower = text.lower()
is_canonical = text_lower in canonical_hyphenated

print(f"Text lowercase: '{text_lower}'")
print(f"Is canonical: {is_canonical}")

if not is_canonical and '-' in text:
    split_text = text.replace('-', ' ')
    print(f"Should be split to: '{split_text}'")
else:
    print("Should NOT be split")