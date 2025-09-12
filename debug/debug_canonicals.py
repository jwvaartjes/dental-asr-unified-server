#!/usr/bin/env python3
"""
Debug script to compare canonicals between direct test and pipeline
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
from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

async def debug_canonicals():
    print("🔍 Debugging canonicals count and content...")
    print("=" * 70)
    
    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    # Get data
    lexicon_data = await data_registry.get_lexicon(admin_id)
    config_data = await data_registry.get_config(admin_id)
    
    print("🧪 DIRECT TEST METHOD:")
    print("-" * 30)
    
    # Create phonetic matcher DIRECTLY like the test script
    matcher = DutchPhoneticMatcher(config_data=config_data)
    
    # Extract canonicals DIRECTLY like the test script
    canonicals = []
    for category, items in lexicon_data.items():
        if isinstance(items, list):
            canonicals.extend(items)
        elif isinstance(items, dict):
            canonicals.extend(items.keys())
    
    # Filter to valid strings only
    canonicals = [c for c in canonicals if isinstance(c, str) and c.strip()]
    print(f"📝 Direct method canonical count: {len(canonicals)}")
    
    # Check if problematic terms are in canonicals
    problematic = ["laesie", "mucosa", "intermaxillair"]
    found = [term for term in problematic if term in canonicals]
    print(f"🚨 Problematic terms found in DIRECT canonicals: {found}")
    
    print(f"\n🏭 PIPELINE METHOD:")
    print("-" * 30)
    
    # Create pipeline for admin user - SAME method as test script
    pipeline = await NormalizationFactory.create_for_admin(data_registry)
    
    # Get the canonicals that the pipeline creates
    pipeline_canonicals = pipeline.canonicals if hasattr(pipeline, 'canonicals') else []
    print(f"📝 Pipeline canonical count: {len(pipeline_canonicals)}")
    
    # Check if problematic terms are in pipeline canonicals
    found_pipeline = [term for term in problematic if term in pipeline_canonicals]
    print(f"🚨 Problematic terms found in PIPELINE canonicals: {found_pipeline}")
    
    print(f"\n📊 COMPARISON:")
    print("-" * 30)
    print(f"Direct canonicals:   {len(canonicals)}")
    print(f"Pipeline canonicals: {len(pipeline_canonicals)}")
    print(f"Difference:          {len(pipeline_canonicals) - len(canonicals)}")
    
    if len(pipeline_canonicals) != len(canonicals):
        # Find the differences
        direct_set = set(canonicals)
        pipeline_set = set(pipeline_canonicals)
        
        extra_in_pipeline = pipeline_set - direct_set
        missing_in_pipeline = direct_set - pipeline_set
        
        if extra_in_pipeline:
            print(f"\n⚠️  EXTRA in pipeline ({len(extra_in_pipeline)}): {list(extra_in_pipeline)[:10]}...")
        if missing_in_pipeline:
            print(f"⚠️  MISSING in pipeline ({len(missing_in_pipeline)}): {list(missing_in_pipeline)[:10]}...")
    
    print(f"\n🧪 Test with 'lich':")
    print("-" * 30)
    
    # Test direct method
    direct_result = matcher.normalize("lich", canonicals)
    print(f"Direct result: '{direct_result}'")
    
    # Test pipeline method
    pipeline_result = pipeline.normalize("lich")
    print(f"Pipeline result: '{pipeline_result.normalized_text}'")

if __name__ == "__main__":
    asyncio.run(debug_canonicals())