#!/usr/bin/env python3
"""
Quick test script to verify hyphen splitting fix for normalization issues.

Tests the specific cases that were problematic:
- "vestibuleer" should become "vestibulair" (not "vestibulum")  
- "interproximaal" should stay "interproximaal" (not become "intermaxillair")
"""

import asyncio
import sys
import os
import logging

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.ai.normalization.factory import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.loader_supabase import SupabaseLoader
from app.data.cache.cache_memory import InMemoryCache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_hyphen_fix():
    """Test the hyphen splitting fix for normalization."""
    
    print("🧪 Testing Hyphen Splitting Fix")
    print("="*50)
    
    try:
        # Create data registry and normalization pipeline (like in main.py)
        cache = InMemoryCache()
        loader = SupabaseLoader()
        data_registry = DataRegistry(cache=cache, loader=loader)
        
        # Get admin user ID
        admin_id = loader.get_admin_id()
        print(f"Using admin ID: {admin_id}")
        
        # Create normalization pipeline
        pipeline = await NormalizationFactory.create_for_admin(data_registry)
        print("✅ Pipeline created successfully")
        
        # Test cases that were previously problematic
        test_cases = [
            # The main problematic cases from user's report
            ("vestibuleer", "vestibulair"),  # Should NOT become "vestibulum"
            ("interproximaal", "interproximaal"),  # Should NOT become "intermaxillair"
            
            # Additional hyphen-related test cases
            ("licht-mucosaal", "licht mucosaal"),  # Should split non-canonical hyphen
            ("peri-apicaal", "peri-apicaal"),      # Should keep canonical hyphen
            ("inter-occlusaal", "inter-occlusaal"),  # Should keep canonical hyphen
            ("vestibulo-linguaal", "vestibulo linguaal"),  # Should split non-canonical
        ]
        
        print("\n🔍 Running Test Cases:")
        print("-" * 30)
        
        all_passed = True
        
        for i, (input_text, expected) in enumerate(test_cases, 1):
            try:
                result = pipeline.normalize(input_text, language="nl")
                actual = result.normalized_text
                
                # Check if test passed
                passed = actual == expected
                status = "✅ PASS" if passed else "❌ FAIL"
                
                print(f"{i}. {status}")
                print(f"   Input:    '{input_text}'")
                print(f"   Expected: '{expected}'")
                print(f"   Actual:   '{actual}'")
                
                if not passed:
                    all_passed = False
                    print(f"   🔍 Debug info:")
                    if hasattr(result, 'debug'):
                        debug = result.debug
                        if 'hyphen_split' in debug:
                            print(f"      After hyphen split: '{debug['hyphen_split']}'")
                        if 'phonetic' in debug:
                            print(f"      After phonetic:     '{debug['phonetic']}'")
                
                print()
                
            except Exception as e:
                print(f"{i}. ❌ ERROR: {str(e)}")
                all_passed = False
                print()
        
        # Final result
        print("="*50)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Hyphen fix is working correctly.")
        else:
            print("⚠️  SOME TESTS FAILED. Please review the results above.")
        print("="*50)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_hyphen_fix())
    exit_code = 0 if result else 1
    sys.exit(exit_code)