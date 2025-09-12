#!/usr/bin/env python3
"""
Mock DataRegistry for testing normalization components
Provides the same interface as the real DataRegistry but with test data
"""

import json
from typing import Dict, Any, Optional
from unittest.mock import MagicMock

class MockDataRegistry:
    """Mock DataRegistry that provides test lexicon data for normalization tests"""
    
    def __init__(self):
        """Initialize mock data registry with test data"""
        self._test_lexicon_data = self._create_test_lexicon_data()
        
    def get_lexicon_data(self) -> Dict[str, Any]:
        """Return test lexicon data that matches expected structure"""
        return self._test_lexicon_data
    
    def _create_test_lexicon_data(self) -> Dict[str, Any]:
        """Create comprehensive test lexicon data"""
        return {
            # Canonical terms for exact matching
            'canonical_terms': [
                'element', 'tand', 'kies', 'molaar',
                'distaal', 'mesiaal', 'buccaal', 'palatinaal',
                'vestibulair', 'linguaal', 'cariës', 'composiet',
                'amalgaam', 'kroon', 'brug', 'implantaat',
                'ca.', 'bijv.', 'bv.', 'etc.',
                'mm', 'cm', 'ml', '%'
            ],
            
            # Phonetic cache for fuzzy matching
            'phonetic_cache': {
                'karius': 'cariës',
                'carius': 'cariës', 
                'karies': 'cariës',
                'element': 'element',
                'tand': 'tand',
                'kies': 'kies',
                'molaar': 'molaar',
                'bukkaal': 'buccaal',
                'festubilair': 'vestibulair',
                'distaal': 'distaal',
                'mesiaal': 'mesiaal'
            },
            
            # Soundex cache for phonetic matching
            'soundex_cache': {
                'K620': ['cariës', 'karius', 'caries'],
                'E453': ['element'],
                'T530': ['tand'],
                'K200': ['kies'], 
                'M460': ['molaar'],
                'B240': ['buccaal', 'bukkaal'],
                'V231': ['vestibulair', 'festubilair']
            },
            
            # Phonetic index for reverse lookups
            'phonetic_index': {
                'cariës': ['karius', 'carius', 'karies'],
                'buccaal': ['bukkaal'],
                'vestibulair': ['festubilair']
            },
            
            # Dutch number mappings
            'dutch_numbers': {
                'een': '1', 'twee': '2', 'drie': '3', 'vier': '4', 'vijf': '5',
                'zes': '6', 'zeven': '7', 'acht': '8', 'negen': '9', 'tien': '10',
                'elf': '11', 'twaalf': '12', 'dertien': '13', 'veertien': '14',
                'vijftien': '15', 'zestien': '16', 'zeventien': '17', 'achttien': '18',
                'negentien': '19', 'twintig': '20', 'eenentwintig': '21',
                'tweeëntwintig': '22', 'drieëntwintig': '23', 'vierentwintig': '24',
                'vijfentwintig': '25', 'zesentwintig': '26', 'zevenentwintig': '27',
                'achtentwintig': '28', 'negenentwintig': '29', 'dertig': '30',
                'eenendertig': '31', 'tweeëndertig': '32', 'drieëndertig': '33',
                'vierendertig': '34', 'vijfendertig': '35', 'zesendertig': '36',
                'zevenendertig': '37', 'achtendertig': '38', 'negenendertig': '39',
                'veertig': '40', 'eenenveertig': '41', 'tweeënveertig': '42',
                'drieënveertig': '43', 'vierenveertig': '44', 'vijfenveertig': '45',
                'zesenveertig': '46', 'zevenenveertig': '47', 'achtenveertig': '48'
            },
            
            # Custom pattern mappings
            'custom_patterns': {
                'karius': 'cariës',
                'bukkaal': 'buccaal', 
                'festubilair': 'vestibulair',
                'circa': 'ca.',
                '30 procent': '30%',
                'dertig procent': '30%'
            },
            
            # Variant generation configuration
            'variant_generation': {
                'separators': ['-', ' ', ''],
                'element_separators': ['-', ' '],
                'patterns': [
                    '{prefix}{separator}{suffix}',
                    '{word}_variant'
                ],
                'digit_words': {
                    '1': ['een', 'eerste'],
                    '2': ['twee', 'tweede'], 
                    '3': ['drie', 'derde'],
                    '4': ['vier', 'vierde'],
                    '5': ['vijf', 'vijfde'],
                    '6': ['zes', 'zesde'],
                    '7': ['zeven', 'zevende'],
                    '8': ['acht', 'achtste']
                },
                'number_patterns': [
                    r'\d+',
                    r'[a-z]+(een|twee|drie|vier|vijf|zes|zeven|acht)',
                    r'(een|twee|drie|vier|vijf|zes|zeven|acht)[a-z]*'
                ],
                'element_patterns': [
                    r'(\d)[\s\-](\d)',
                    r'(\d)(\d)'
                ],
                'high_value_combos': [
                    [['ë', 'e'], ['c', 'k']],
                    [['ï', 'i'], ['c', 'k']],
                    [['uu', 'u'], ['cc', 'c']]
                ],
                'use_lazy_loading': True,
                'lru_cache_size': 1000,
                'precompute_common': 50,
                'enable_smart_doubling': True
            },
            
            # Element separators (required at root level by VariantGenerator)
            'element_separators': ['-', ' '],
            
            # Required patterns for VariantGenerator
            'prefixes': ['dis', 'mes', 'buc', 'pal', 'ves', 'ling', 'occ', 'inc', 'cer', 'apr'],
            'suffix_groups': [
                ['aal', 'ale', 'alen'],
                ['isch', 'ische'],  
                ['air', 'aire'],
                ['ief', 'ieve'],
                ['itis', 'itiden']
            ],
            'suffix_patterns': {
                'ordinal': ['de', 'ste', 'e'],
                'plural': ['en', 's'], 
                'adjective': ['aal', 'ale', 'isch', 'ische', 'air', 'aire']
            },
            
            # Protected words that shouldn't be modified
            'protect_words': [
                'element', 'tand', 'kies', 'molaar',
                'ca.', 'bijv.', 'etc.', 'mm', 'cm', 'op'
            ],
            
            # Unit abbreviations
            'units_abbr': {
                'millimeter': 'mm',
                'centimeter': 'cm', 
                'milliliter': 'ml',
                'procent': '%',
                'graden': '°',
                'circa': 'ca.'
            },
            
            # Surface mappings
            'surfaces': {
                'distaal': 'distaal',
                'mesiaal': 'mesiaal', 
                'buccaal': 'buccaal',
                'palatinaal': 'palatinaal',
                'vestibulair': 'vestibulair',
                'linguaal': 'linguaal',
                'occlusaal': 'occlusaal',
                'incisaal': 'incisaal',
                'mesiopalatinaal': 'mesiopalatinaal',
                'distopalatinaal': 'distopalatinaal',
                'mesiovestibulair': 'mesiovestibulair',
                'distovestibulair': 'distovestibulair'
            },
            
            # Dental context triggers
            'dental_contexts': [
                'element', 'tand', 'kies', 'molaar', 'hoektand', 
                'snijtand', 'premolaar', 'wijsheidstand'
            ]
        }

def create_mock_data_registry() -> MockDataRegistry:
    """Factory function to create a mock data registry for tests"""
    return MockDataRegistry()

def get_test_config() -> Dict[str, Any]:
    """Get test configuration for normalization pipeline"""
    return {
        'enable_element_parsing': True,
        'enable_learnable_normalization': True,
        'enable_post_processing': True,
        'phonetic': {
            'min_similarity_threshold': 0.8,
            'use_fuzzy_matching': True
        }
    }