#!/usr/bin/env python3
"""
Search for specific problematic mappings in Supabase data
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

async def search_mappings():
    print("🔍 Searching for problematic mappings...")
    print("=" * 70)
    
    # Initialize data registry
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(loader=loader, cache=cache)
    
    admin_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    # Get all data
    lexicon_data = await data_registry.get_lexicon(admin_id)
    config_data = await data_registry.get_config(admin_id)
    
    print(f"📚 Loaded {len(lexicon_data)} lexicon categories")
    print(f"⚙️  Config keys: {list(config_data.keys())}")
    
    # Search for problematic mappings
    problematic_words = [
        ("lich", "laesie"),
        ("mesio", "mucosa"),
        ("interproximaal", "intermaxillair"),
        ("circa", "ca"),
        ("frameprothese", "Foramen Apicale"),
        ("tandsteen", "tandbeen"),
        ("fractuur", "furcatie")
    ]
    
    def search_in_data(data, path="", target_mappings=None):
        """Recursively search for mappings"""
        found_mappings = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check for direct key-value mappings
                for source, expected_target in target_mappings:
                    if key.lower() == source.lower() and isinstance(value, str):
                        if expected_target.lower() in value.lower():
                            found_mappings.append(f"FOUND: {current_path} = '{value}' (maps '{source}' -> '{expected_target}')")
                        else:
                            # Check if value contains the problematic mapping
                            if any(expected_target.lower() in str(v).lower() for v in [value] if isinstance(v, str)):
                                found_mappings.append(f"POTENTIAL: {current_path} = '{value}'")
                
                # Recurse
                found_mappings.extend(search_in_data(value, current_path, target_mappings))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                found_mappings.extend(search_in_data(item, current_path, target_mappings))
        
        return found_mappings
    
    print("\n🔍 Searching in lexicon data...")
    lexicon_results = search_in_data(lexicon_data, "lexicon", problematic_words)
    
    print("\n🔍 Searching in config data...")
    config_results = search_in_data(config_data, "config", problematic_words)
    
    # Print results
    print(f"\n📊 Found {len(lexicon_results)} potential mappings in lexicon:")
    for result in lexicon_results:
        print(f"   {result}")
    
    print(f"\n📊 Found {len(config_results)} potential mappings in config:")
    for result in config_results:
        print(f"   {result}")
    
    # Also look for variant_generation specifically
    print("\n🔍 Checking variant_generation section:")
    variant_gen = config_data.get("variant_generation", {})
    if variant_gen:
        print("   variant_generation found:")
        for key, value in variant_gen.items():
            if isinstance(value, dict):
                print(f"      {key}: {len(value)} entries")
                # Check for our problematic mappings
                for source, target in problematic_words:
                    if source in value:
                        print(f"         🎯 FOUND MAPPING: '{source}' -> '{value[source]}'")
            else:
                print(f"      {key}: {value}")
    
    # Check learnable normalization
    print("\n🔍 Checking learnable normalization rules:")
    learnable_rules = config_data.get("learnable_rules", {})
    if learnable_rules:
        print(f"   learnable_rules: {len(learnable_rules)} entries")
        for source, target in problematic_words:
            if source in learnable_rules:
                print(f"      🎯 FOUND LEARNABLE: '{source}' -> '{learnable_rules[source]}'")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(search_mappings())