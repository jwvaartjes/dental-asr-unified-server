#!/usr/bin/env python3
"""
Detailed search for 'caries' in the lexicon
"""

import asyncio
import sys
import os
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader

async def detailed_lexicon_search():
    print("🔍 Detailed search for 'caries' in lexicon...")
    print("=" * 70)
    
    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    lexicon_data = await data_registry.get_lexicon(admin_id)
    
    if not lexicon_data:
        print("❌ No lexicon data found")
        return
    
    def search_deeply(data, path="", search_term="caries"):
        """Search for term in any nested structure"""
        results = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if key contains search term
                if search_term.lower() in key.lower():
                    results.append(f"KEY: {current_path} = {json.dumps(value, ensure_ascii=False)[:100]}")
                
                # Check if value is string and contains search term
                if isinstance(value, str) and search_term.lower() in value.lower():
                    results.append(f"VALUE: {current_path} = '{value}'")
                
                # Recurse into nested structures
                results.extend(search_deeply(value, current_path, search_term))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                
                if isinstance(item, str) and search_term.lower() in item.lower():
                    results.append(f"LIST_ITEM: {current_path} = '{item}'")
                
                results.extend(search_deeply(item, current_path, search_term))
        
        return results
    
    # Search for 'caries'
    caries_results = search_deeply(lexicon_data, "", "caries")
    
    print(f"🔍 Found {len(caries_results)} matches for 'caries':")
    for result in caries_results:
        print(f"  📍 {result}")
    
    # Also search for potential variations
    variations = ["karies", "cariës", "cavity", "caviteit"]
    for variation in variations:
        var_results = search_deeply(lexicon_data, "", variation)
        if var_results:
            print(f"\n🔍 Found {len(var_results)} matches for '{variation}':")
            for result in var_results:
                print(f"  📍 {result}")
    
    # Check specific categories that might contain pathology terms
    pathology_categories = ["pathologie", "general_dental_terms"]
    
    for category in pathology_categories:
        if category in lexicon_data:
            print(f"\n📂 Checking {category} category:")
            category_data = lexicon_data[category]
            
            if isinstance(category_data, dict):
                print(f"   📊 Contains {len(category_data)} entries")
                # Show some sample entries
                sample_keys = list(category_data.keys())[:10]
                print(f"   📝 Sample entries: {sample_keys}")
                
                # Check if any of these contain caries-related terms
                caries_in_category = search_deeply(category_data, f"{category}", "cari")
                if caries_in_category:
                    print(f"   🎯 Found caries-related terms:")
                    for result in caries_in_category:
                        print(f"     {result}")
            
            elif isinstance(category_data, list):
                print(f"   📊 Contains {len(category_data)} list items")
                sample_items = category_data[:10]
                print(f"   📝 Sample items: {sample_items}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(detailed_lexicon_search())