#!/usr/bin/env python3
"""
Test if element parsing still works with _space_separators_between_digits disabled
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.ai.normalization.pipeline import NormalizationPipeline

async def test():
    pipeline = await NormalizationPipeline.create_for_admin()
    
    tests = [
        # Element parsing should still work
        ('1,4', 'element 14'),
        ('element 1,4', 'element 14'),
        ('tand 1,4', 'tand 14'),
        ('kies 2,3', 'kies 23'),
        
        # Decimal numbers with units should be preserved
        ('1,5 jaar', '1,5 jaar'),
        ('2,5 mm', '2,5 mm'),
        ('3 weken', '3 weken'),
        ('10 dagen', '10 dagen'),
        
        # Mixed cases
        ('element 1,4 en 1,5 jaar', 'element 14 en 1,5 jaar'),
    ]
    
    print("Testing with _space_separators_between_digits DISABLED")
    print("=" * 70)
    
    all_pass = True
    for input_text, expected in tests:
        result = pipeline.normalize(input_text)
        status = '✅' if result.normalized_text == expected else '❌'
        if status == '❌':
            all_pass = False
        print(f'{status} "{input_text}" → "{result.normalized_text}" (expected: "{expected}")')
    
    print("=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASS - Element parsing works, decimals preserved!")
    else:
        print("❌ SOME TESTS FAILED")
    
asyncio.run(test())