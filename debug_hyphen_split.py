#!/usr/bin/env python3
"""
Debug script to test the hyphen splitting method directly.
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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_hyphen_split():
    """Debug the hyphen splitting functionality."""
    
    print("🐛 Debug: Hyphen Splitting Method")
    print("="*50)
    
    try:
        # Create data registry and normalization pipeline
        cache = InMemoryCache()
        loader = SupabaseLoader()
        data_registry = DataRegistry(cache=cache, loader=loader)
        
        # Get admin user ID
        admin_id = loader.get_admin_id()
        print(f"Using admin ID: {admin_id}")
        
        # Create normalization pipeline
        pipeline = await NormalizationFactory.create_for_admin(data_registry)
        print("✅ Pipeline created successfully")
        
        # Test the hyphen splitting method directly
        test_cases = [
            "licht-mucosaal",
            "peri-apicaal",
            "vestibulo-linguaal",
            "inter-occlusaal",
            "simple-test"
        ]
        
        print("\n🔍 Testing hyphen split method directly:")
        print("-" * 40)
        
        for test in test_cases:
            result = pipeline._split_noncanonical_hyphens(test)
            print(f"Input:  '{test}'")
            print(f"Output: '{result}'")
            print()
        
        # Test the full pipeline step by step
        print("\n🔍 Testing full pipeline with debug:")
        print("-" * 40)
        
        test_input = "licht-mucosaal"
        print(f"Original input: '{test_input}'")
        
        # Step 1: Protected wrap
        wrapped = pipeline.guard.wrap(test_input)
        print(f"After protect wrap: '{wrapped}'")
        
        # Step 2: NBSP replacement
        nbsp_fixed = wrapped.replace("\u00A0", " ")
        print(f"After NBSP fix: '{nbsp_fixed}'")
        
        # Step 3: Apply hyphen splitting on unprotected
        hyphen_result = pipeline._apply_on_unprotected(nbsp_fixed, pipeline._split_noncanonical_hyphens)
        print(f"After hyphen split: '{hyphen_result}'")
        
        print("\n✅ Debug complete")
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the debug
    asyncio.run(debug_hyphen_split())