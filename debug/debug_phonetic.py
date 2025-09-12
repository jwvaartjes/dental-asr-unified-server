#!/usr/bin/env python3
"""
Debug phonetic matcher independently
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher

async def main():
    # Setup data access
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Get lexicon data
    lexicon_data = await registry.get_lexicon("76c7198e-710f-41dc-b26d-ce728571a546")
    
    # Create phonetic matcher with similar config as pipeline
    config = {
        'lexicon': lexicon_data,
        'threshold': 0.8
    }
    
    # Create simple tokenizer for testing
    class SimpleTokenizer:
        def tokenize(self, text):
            import re
            return re.findall(r'\S+|\s+', text)
        def detokenize(self, tokens):
            return ''.join(tokens)
    
    matcher = DutchPhoneticMatcher(config_data=config, tokenizer=SimpleTokenizer())
    
    # Debug info
    print(f"Canonicals found: {len(matcher.canonicals)}")
    if matcher.canonicals:
        print(f"First few canonicals: {matcher.canonicals[:10]}")
        # Check if 'element' is in canonicals
        element_variants = [c for c in matcher.canonicals if 'element' in c.lower()]
        print(f"Element variants in canonicals: {element_variants[:10]}")
    
    # Test cases
    test_cases = [
        "elemet",
        "elemetn", 
        "element",
        "licht-mucosale",
        "voor-operatief"
    ]
    
    print("\n" + "="*50)
    print("Testing individual word matching:")
    for test_word in test_cases:
        match_result = matcher.match(test_word, matcher.canonicals) if matcher.canonicals else None
        print(f"'{test_word}' -> {match_result}")
    
    print("\n" + "="*50)
    print("Testing normalize method:")
    for test_word in test_cases:
        normalized = matcher.normalize(test_word)
        print(f"'{test_word}' -> '{normalized}'")
    
    # Test full phrase
    print("\n" + "="*50)
    print("Testing full phrases:")
    test_phrases = [
        "elemet 14",
        "elemetn 16",
        "licht-mucosale beschadiging"
    ]
    
    for phrase in test_phrases:
        normalized = matcher.normalize(phrase)
        print(f"'{phrase}' -> '{normalized}'")

if __name__ == "__main__":
    asyncio.run(main())