#!/usr/bin/env python3
"""
Script to check what variants are loaded from Supabase
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def check_variants():
    print("=" * 70)
    print("🔍 Checking what variants are loaded from Supabase...")
    print("=" * 70)
    
    # Import the necessary modules
    from app.data.registry import DataRegistry
    from app.data.cache.cache_memory import InMemoryCache
    from app.data.loaders.loader_supabase import SupabaseLoader
    from app.ai.normalization import NormalizationFactory
    
    # Initialize DataRegistry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Get admin user ID
    admin_user_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    # Load lexicon data
    print(f"\n📚 Loading lexicon for admin user: {admin_user_id}")
    lexicon_data = await registry.get_lexicon(admin_user_id)
    
    if lexicon_data and 'variants' in lexicon_data:
        variants = lexicon_data['variants']
        print(f"\n✅ Found {len(variants)} variants in lexicon")
        
        # Check specifically for "bot verlies"
        if 'bot verlies' in variants:
            print(f"\n🎯 Found 'bot verlies' → '{variants['bot verlies']}'")
        else:
            print(f"\n❌ 'bot verlies' NOT found in variants")
            
        # Show sample of variants
        print(f"\n📋 Sample of loaded variants:")
        for i, (src, dst) in enumerate(list(variants.items())[:10]):
            print(f"  {i+1}. '{src}' → '{dst}'")
            
        # Check for similar compound words
        print(f"\n🔍 Checking for similar compound word variants:")
        compound_checks = ['bot verlies', 'bot-verlies', 'hand verlies', 'been verlies']
        for check in compound_checks:
            if check in variants:
                print(f"  ✅ '{check}' → '{variants[check]}'")
            else:
                print(f"  ❌ '{check}' not found")
    else:
        print("\n❌ No variants found in lexicon_data")
        
    # Now let's check what the pipeline actually gets
    print("\n" + "=" * 70)
    print("🔧 Creating normalization pipeline...")
    
    pipeline = await NormalizationFactory.create_for_admin(registry)
    print("✅ Pipeline created")
    
    # Test normalization directly
    print("\n📝 Testing normalization:")
    test_cases = [
        'bot verlies',
        'bot-verlies',
        'hand verlies',
        'been verlies'
    ]
    
    for test in test_cases:
        result = pipeline.normalize(test)
        print(f"  '{test}' → '{result.normalized_text}'")

if __name__ == "__main__":
    asyncio.run(check_variants())