#!/usr/bin/env python3
"""
Debug full normalization pipeline for specific failing test cases
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization.pipeline import NormalizationPipeline

async def debug_full_pipeline():
    print("🔍 Debugging full normalization pipeline...")
    print("=" * 70)
    
    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    # Create pipeline
    pipeline = NormalizationPipeline(data_registry, admin_id)
    await pipeline.initialize()
    
    print("✅ Pipeline initialized successfully")
    
    # Test problematic cases with detailed debug output
    test_cases = [
        "lich-mucosaal",
        "lich mucosaal", 
        "mesio-occlusaal",
        "mesio-buccaal",
        "circa",
        "1, 2, 3",
        "interproximaal",
        "frameprothese"
    ]
    
    print("\n🧪 Testing problematic cases with full pipeline:")
    print("-" * 70)
    
    for test_input in test_cases:
        print(f"\n🔍 Input: '{test_input}'")
        print("   " + "-" * 50)
        
        # Run normalization with debug
        result = pipeline.normalize(test_input)
        
        print(f"   📤 Output: '{result.normalized_text}'")
        print(f"   ⏱️  Processing time: {result.processing_time_ms:.1f}ms")
        
        # Print debug steps if available
        if hasattr(result, 'debug') and result.debug:
            print("   🔧 Debug steps:")
            for step_name, step_result in result.debug.items():
                if step_result != test_input:  # Only show steps that changed something
                    print(f"      {step_name}: '{step_result}'")
        
        print()
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(debug_full_pipeline())