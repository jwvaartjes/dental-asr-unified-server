#!/usr/bin/env python3
"""
Check lexicon for radiaal and radiopaak
"""

import sys
sys.path.insert(0, '/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace')

from supabase_manager import SupabaseManager

sm = SupabaseManager()
lex = sm.get_all_lexicons()

print(f"Total lexicon entries: {len(lex)}")

# Search for radio-related words
radi_words = [k for k in lex.keys() if 'radi' in k.lower()]
print(f"\nFound {len(radi_words)} radio-related words:")
for word in sorted(radi_words)[:20]:
    print(f"  {word}")

print(f"\n'radiaal' in lexicon: {'radiaal' in lex}")
print(f"'radiopaak' in lexicon: {'radiopaak' in lex}")

# If radiopaak exists, show its variants
if 'radiopaak' in lex:
    print(f"\nradiopaak variants: {lex['radiopaak']}")
    
# If radiaal exists, show its variants  
if 'radiaal' in lex:
    print(f"\nradiaal variants: {lex['radiaal']}")