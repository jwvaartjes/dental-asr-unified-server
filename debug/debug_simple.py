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
    
    # Comprehensive test cases from stable_baseline_workspace (ALL TESTS)
    failing_cases = [
        # Basic element parsing tests - from test_baseline.py
        ('element een vier', 'element 14'),
        ('karius', 'cariës'),
        ('1-4', 'element 14'),
        ('messial', 'mesiaal'),
        ('30 procent', '30%'),
        
        # Hyphen normalization - from test_hyphen_normalization.py
        ('veriapicaal', 'peri-apicaal'),
        ('periapicaal', 'peri-apicaal'),
        ('peri-apicaal', 'peri-apicaal'),
        ('verticaal', 'verticaal'),
        ('apicaal', 'apicaal'),
        ('radiaal', 'radiaal'),
        ('occlusaal', 'occlusaal'),
        
        # Key hyphen removal tests from stable normalization
        ('licht-mucosale', 'licht mucosale'),        # Remove hyphen
        ('licht-mucosaal', 'licht mucosaal'),        # Remove hyphen
        ('mesio-occlusaal', 'mesio occlusaal'),      # Remove hyphen
        ('mesio-buccaal', 'mesio buccaal'),          # Remove hyphen
        ('disto-occlusaal', 'disto occlusaal'),      # Remove hyphen
        ('disto-buccaal', 'disto buccaal'),          # Remove hyphen
        
        # Important phonetic fixes - should NOT create false matches
        ('interproximaal', 'interproximaal'),        # NOT intermaxillair
        ('lich', 'lich'),                           # NOT laesie
        ('lich mucosaal', 'lich mucosaal'),         # Keep as-is
        
        # Element parsing from stable tests
        ('14;15;16', 'element 14; element 15; element 16'),
        ('1, 2, 3', '1, 2, 3'),                     # Should NOT become "element 12, 3"
        ('element 1, 2', 'element 12'),             
        ('de 11', 'element 11'),                    
        ('tand een vier', 'tand 14'),               
        ('kies twee drie', 'kies 23'),              
        ('1-4 en 2-3', 'element 14 en element 23'),
        ('element 14 element 14', 'element 14'),     # Deduplication
        
        # Number words and context
        ('element een vier', 'element 14'),         # NOT "element element 14"
        ('de element 11', 'element 11'),            # Lidwoord cleanup
        ('molaar 6 7', 'molaar 67'),                # Context combination
        ('premolaar 4 5', 'premolaar 45'),          # Context combination
        
        # Abbreviations and variants
        ('circa', 'ca.'),
        ('ongeveer', 'ca.'),
        ('parod', 'parodontitis'),
        ('botverlies', 'botverlies'),
        ('bot verlies', 'botverlies'),               # Compound
        
        # Protected words should remain unchanged
        ('Paro', 'Paro'),
        ('30% botverlies', '30% botverlies'),        # No fuzzy on percentages
        
        # Additional stable baseline tests
        ('linguaal', 'linguaal'),
        ('palatinaal', 'palatinaal'),
        ('bucaal', 'buccaal'),                      # Variant correction
        ('vestibuleer', 'vestibulaar'),             # Variant correction
        ('gingivaal', 'gingivaal'),
        ('subgingivaal', 'subgingivaal'),
        ('supragingival', 'supragingivaal'),         # Variant correction
        
        # Composite and restoration terms
        ('composiet', 'composiet'),
        ('amalgaam', 'amalgaam'),
        ('kroon', 'kroon'),
        ('wortelkanaal', 'wortelkanaalbehandeling'), # Expansion
        ('endodontie', 'endodontische behandeling'), # Expansion
        
        # Periodontal terms
        ('parodontitis', 'parodontitis'),
        ('gingivitis', 'gingivitis'),
        ('tandvlees', 'tandvlees'),
        ('pockets', 'parodontale pockets'),          # Expansion
        
        # Anatomical terms
        ('maxilla', 'maxilla'),
        ('mandibula', 'mandibula'),
        ('processus', 'processus'),
        ('alveolaire', 'alveolaire'),
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