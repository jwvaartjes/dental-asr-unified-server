#!/usr/bin/env python3
"""
Simple test to investigate why 'radiaal' is matching to 'radiopaak'
This test uses only the actual codebase without external dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now let's trace through what happens with 'radiaal' in the actual normalization pipeline
def test_radiaal():
    print("🔍 Investigating why 'radiaal' → 'radiopaak'\n")
    print("=" * 60)
    
    # Test the actual normalization through the learnable normalizer
    try:
        # Import the actual learnable normalizer
        sys.path.insert(0, '/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace')
        from learnable_normalizer import DentalNormalizer
        
        # Initialize normalizer (loads from Supabase)
        normalizer = DentalNormalizer()
        
        # Test the problematic word
        test_word = "radiaal"
        
        print(f"Testing word: '{test_word}'")
        print("-" * 40)
        
        # Run the normalization
        result = normalizer.normalize(test_word)
        
        print(f"\nNormalization result:")
        print(f"  Input:      '{test_word}'")
        print(f"  Normalized: '{result.normalized_text}'")
        
        if hasattr(result, 'debug') and result.debug:
            print(f"\nDebug information:")
            for step, value in result.debug.items():
                if value != test_word and value != result.normalized_text:
                    print(f"  {step}: '{value}'")
        
        # Also test the phonetic matching directly if we can
        print("\n" + "=" * 60)
        print("Testing phonetic matching mechanism:")
        
        # Check what's in the lexicon for radio-related terms
        if hasattr(normalizer, 'lexicon') and normalizer.lexicon:
            print("\nRadio-related terms in lexicon:")
            for key in sorted(normalizer.lexicon.keys()):
                if 'radi' in key.lower():
                    values = normalizer.lexicon[key]
                    if isinstance(values, list):
                        print(f"  {key}: {', '.join(values)}")
                    else:
                        print(f"  {key}: {values}")
        
        # Try to understand the matching score
        print("\n" + "=" * 60)
        print("Analysis of the matching issue:\n")
        
        print("1. Character overlap analysis:")
        print(f"   'radiaal' vs 'radiopaak'")
        print(f"   Common prefix: 'radi' (4 chars)")
        print(f"   Lengths: radiaal=7, radiopaak=9")
        print(f"   Basic similarity: ~4/8 = 50%")
        
        print("\n2. Phonetic similarity:")
        print(f"   Both start with 'radi' sound")
        print(f"   'aal' ending (adjective) vs 'aak' ending")
        print(f"   Phonetically similar but different word types")
        
        print("\n3. Morphological analysis:")
        print(f"   'radiaal' ends with '-aal' (typical adjective ending)")
        print(f"   'radiopaak' has no clear morphological family")
        print(f"   These should NOT be matched together!")
        
        print("\n4. Expected behavior:")
        print(f"   'radiaal' should remain 'radiaal' (or map to a dental term)")
        print(f"   NOT be changed to 'radiopaak' (radiopaque)")
        
        return result
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_radiaal()