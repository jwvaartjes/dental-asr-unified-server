#!/usr/bin/env python3
"""
Check current lexicon and update 'caries' to 'cariës'
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader

async def check_and_update_lexicon():
    print("🔍 Checking current lexicon data...")
    print("=" * 70)
    
    # Initialize data registry with proper Supabase connection
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    # Load admin components
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    lexicon_data = await data_registry.get_lexicon(admin_id)
    print(f"📚 Current lexicon structure: {type(lexicon_data)}")
    
    if lexicon_data:
        print(f"📚 Lexicon keys: {list(lexicon_data.keys())}")
        
        # Look for 'caries' in different possible locations
        caries_found = False
        
        # Check if there's a 'lexicon' key with canonical terms
        if 'lexicon' in lexicon_data:
            lexicon_dict = lexicon_data['lexicon']
            print(f"📖 Lexicon dict has {len(lexicon_dict)} entries")
            
            if 'caries' in lexicon_dict:
                print(f"❗ Found 'caries' in lexicon: {lexicon_dict['caries']}")
                caries_found = True
        
        # Check if there's a 'canonicals' list
        if 'canonicals' in lexicon_data:
            canonicals = lexicon_data['canonicals']
            print(f"📝 Canonicals list has {len(canonicals)} entries")
            
            if 'caries' in canonicals:
                print(f"❗ Found 'caries' in canonicals list")
                caries_found = True
        
        # Search through all data for 'caries'
        def find_caries_recursive(data, path=""):
            found_locations = []
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if key == 'caries' or (isinstance(value, str) and value == 'caries'):
                        found_locations.append((current_path, value))
                    found_locations.extend(find_caries_recursive(value, current_path))
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, str) and item == 'caries':
                        found_locations.append((current_path, item))
                    found_locations.extend(find_caries_recursive(item, current_path))
            return found_locations
        
        caries_locations = find_caries_recursive(lexicon_data)
        if caries_locations:
            print(f"🔍 Found 'caries' in {len(caries_locations)} locations:")
            for location, value in caries_locations:
                print(f"  📍 {location}: {value}")
            caries_found = True
        
        if not caries_found:
            print("❌ 'caries' not found in lexicon data")
            print("💡 We need to add 'cariës' to the lexicon")
            
            # Show a sample of what's in the lexicon
            if 'lexicon' in lexicon_data and isinstance(lexicon_data['lexicon'], dict):
                sample_keys = list(lexicon_data['lexicon'].keys())[:10]
                print(f"📝 Sample lexicon entries: {sample_keys}")
        
        # Check what the accent preservation system would see
        print("\n🔧 Checking for diacritical words that could build restoration map...")
        
        canonicals = []
        if isinstance(lexicon_data.get("canonicals"), list):
            canonicals = lexicon_data["canonicals"]
        elif isinstance(lexicon_data.get("lexicon"), dict):
            canonicals = list(lexicon_data["lexicon"].keys())
        
        diacritical_words = []
        for canonical in canonicals:
            if isinstance(canonical, str):
                # Check if word contains diacritics using Unicode normalization
                import unicodedata
                if any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", canonical)):
                    diacritical_words.append(canonical)
        
        print(f"✨ Found {len(diacritical_words)} words with diacritics: {diacritical_words}")
        
    else:
        print("❌ No lexicon data found")
    
    print("\n" + "=" * 70)
    print("🎯 Next steps:")
    if not caries_found:
        print("1. Add 'cariës' to the lexicon")
    else:
        print("1. Replace 'caries' with 'cariës' in the lexicon")
    print("2. Test the accent preservation again")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(check_and_update_lexicon())