#!/usr/bin/env python3
"""
Simple debug of specific failing test cases using the same method as the test script
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory

async def debug_specific_cases():
    print("🔍 Debugging specific failing test cases...")
    print("=" * 70)
    
    # Initialize DataRegistry exactly like the test script
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Create pipeline for admin user - SAME method as test script
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("✅ Pipeline created successfully using NormalizationFactory")
    
    # Comprehensive test cases - all important scenarios
    failing_cases = [
        # Phonetic matching issues (should NOT match)
        ("lich-mucosaal", "lich-mucosaal"),
        ("lich mucosaal", "lich mucosaal"),
        ("licht-mucosaal", "licht-mucosaal"),
        ("licht mucosaal", "licht mucosaal"),
        ("mesio-occlusaal", "mesio-occlusaal"),
        ("mesio-buccaal", "mesio-buccaal"),
        
        # Element parsing tests
        ("1, 2, 3", "1, 2, 3"),              # Should not become "element 12, 3"
        ("14;15;16", "element 14; element 15; element 16"),  # Should parse elements
        ("element 1, 2", "element 12"),       # Should combine in context
        ("de 11", "element 11"),              # Lidwoord cleanup
        ("tand een vier", "tand 14"),         # Context-aware number parsing
        ("kies twee drie", "kies 23"),        # Context-aware number parsing
        
        # Abbreviation tests  
        ("circa", "ca."),                     # Should abbreviate
        ("ongeveer", "ca."),                  # Should abbreviate
        
        # Fuzzy matching tests
        ("interproximaal", "interproximaal"), # Should stay as is (not become intermaxillair)
        ("botverlies", "botverlies"),         # Should stay as compound
        ("bot verlies", "botverlies"),        # Should compound
        
        # Protected word tests (these should remain unchanged)
        ("Paro", "Paro"),                     # Should be protected
        ("30% botverlies", "30% botverlies"), # Percentage should not be fuzzy matched
        
        # Additional element tests
        ("1-4 en 2-3", "element 14 en element 23"),    # Multiple elements
        ("element 14 element 14", "element 14"),        # Deduplication
        
        # Dental context tests
        ("molaar 6 7", "molaar 67"),         # Context combination
        ("premolaar 4 5", "premolaar 45"),   # Context combination
        
        # Edge cases
        ("element een vier", "element 14"),   # Should not become "element element 14"
        ("de element 11", "element 11"),      # Lidwoord cleanup with existing element
        ("parod", "parodontitis"),            # Variant expansion
    ]
    
    print("\n🧪 Testing specific failing cases:")
    print("-" * 70)
    
    for test_input, expected in failing_cases:
        print(f"\n🔍 Input: '{test_input}'")
        print(f"   Expected: '{expected}'")
        
        # Run normalization
        result = pipeline.normalize(test_input)
        actual = result.normalized_text
        
        # Check result
        success = actual == expected
        status = "✅ PASS" if success else "❌ FAIL"
        
        print(f"   Actual:   '{actual}'")
        print(f"   Status:   {status}")
        
        if not success:
            print(f"   💥 ERROR: Expected '{expected}' but got '{actual}'")

if __name__ == "__main__":
    asyncio.run(debug_specific_cases())