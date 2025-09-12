#!/usr/bin/env python3
"""
Add 'element' to the general_dental_terms category in Supabase lexicon.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader

async def main():
    # Setup data access
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Get current lexicon data
    lexicon_data = await registry.get_lexicon("76c7198e-710f-41dc-b26d-ce728571a546")
    
    print("Current general_dental_terms:", lexicon_data.get("general_dental_terms", []))
    
    # Add 'element' if not already present
    general_terms = lexicon_data.get("general_dental_terms", [])
    if "element" not in general_terms:
        general_terms.append("element")
        lexicon_data["general_dental_terms"] = general_terms
        
        # Save back to Supabase
        await registry.save_lexicon("76c7198e-710f-41dc-b26d-ce728571a546", lexicon_data)
        print("✅ Added 'element' to general_dental_terms")
    else:
        print("✅ 'element' already in general_dental_terms")
    
    print("Updated general_dental_terms:", lexicon_data.get("general_dental_terms", []))

if __name__ == "__main__":
    asyncio.run(main())