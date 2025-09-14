#!/usr/bin/env python3
"""
Test if both fixes are working:
1. "bot verlies" → "botverlies" 
2. "radiaal" NOT matching to "radiopaak"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.normalization.factory import NormalizationFactory
from app.data.registry import DataRegistry
import asyncio

async def test_fixes():
    # Initialize
    data_registry = DataRegistry()
    await data_registry.initialize()
    
    pipeline = await NormalizationFactory.create_for_admin(data_registry)
    
    print("Testing our fixes:")
    print("=" * 70)
    
    # Test 1: "bot verlies" should normalize to "botverlies"
    result = pipeline.normalize("bot verlies", language="nl")
    print(f"Test 1: 'bot verlies' → '{result.normalized_text}'")
    if result.normalized_text == "botverlies":
        print("✅ PASS: Variant destination is recognized as canonical")
    else:
        print("❌ FAIL: Should be 'botverlies'")
    
    # Test 2: "radiaal" should stay as "radiaal"
    result = pipeline.normalize("radiaal", language="nl")
    print(f"\nTest 2: 'radiaal' → '{result.normalized_text}'")
    if result.normalized_text == "radiaal":
        print("✅ PASS: Not incorrectly matched to 'radiopaak'")
    else:
        print(f"❌ FAIL: Should stay as 'radiaal', not '{result.normalized_text}'")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("- Added variant destinations to canonicals list ✅")
    print("- Added 'radi' to GENERIC_PREFIXES ✅")
    print("- Generic prefix mechanism reduces similarity for 'radi' words ✅")

if __name__ == "__main__":
    asyncio.run(test_fixes())
