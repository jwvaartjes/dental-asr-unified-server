#!/usr/bin/env python3
"""
variant_generator.py - Core variant generation system
Config-based versie zonder hardcoded patterns
"""

import re
import unicodedata
from typing import List, Set, Dict, Tuple, Optional, Any
from functools import lru_cache

def _normalize_text(text: str) -> str:
    """Normalize text for matching"""
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return text.strip().lower()

class VariantGenerator:
    """Generates all possible variants of a term using linguistic patterns from config"""
    
    def __init__(self, config_data: Dict[str, Any] = None):
        """Initialize with config data instead of file path"""
        self.config = config_data or {}
        self._load_patterns()
        
        # Load digit words from Supabase config - REQUIRED
        variant_config = self.config.get('variant_generation')
        if not variant_config:
            raise ValueError("❌ CRITICAL: variant_generation config not found in Supabase!")
            
        self.digit_words = variant_config.get('digit_words')
        if not self.digit_words:
            raise ValueError("❌ CRITICAL: digit_words not found in variant_generation config! Please update Supabase configuration.")
    
    def _load_patterns(self):
        """Load all patterns from configuration"""
        print("🔄 Loading variant patterns from config...")
        
        # Get patterns from config
        # FAIL FAST: All patterns must come from Supabase config
        self.patterns = {
            'splittable_prefixes': self.config.get('prefixes'),
            'suffix_groups': self.config.get('suffix_groups'),
            'char_substitutions': [],
            'phonetic_patterns': [],
            'separators': self.config.get('variant_generation', {}).get('separators'),
            'element_separators': self.config.get('element_separators'),
        }
        
        # Validate critical patterns exist
        if self.patterns['separators'] is None:
            raise ValueError("❌ CRITICAL: separators not found in variant_generation config!")
        if self.patterns['element_separators'] is None:
            raise ValueError("❌ CRITICAL: element_separators not found in Supabase config!")
        
        # Convert phonetic patterns from config
        if 'phonetic_patterns' in self.config:
            # Dutch sounds
            if 'dutch_sounds' in self.config['phonetic_patterns']:
                for pattern, replacements in self.config['phonetic_patterns']['dutch_sounds'].items():
                    for replacement in replacements:
                        self.patterns['char_substitutions'].append((pattern, replacement))
            
            # Common errors
            if 'common_errors' in self.config['phonetic_patterns']:
                for pattern, replacements in self.config['phonetic_patterns']['common_errors'].items():
                    for replacement in replacements:
                        self.patterns['phonetic_patterns'].append((pattern, replacement))
        
        # Load suffix categories - FAIL FAST
        self.suffix_categories = self.config.get('suffix_patterns')
        if self.suffix_categories is None:
            raise ValueError("❌ CRITICAL: suffix_patterns not found in Supabase config!")
        
        self.common_suffixes = []
        for category, suffixes in self.suffix_categories.items():
            self.common_suffixes.extend(suffixes)
        
        # FAIL FAST: No fallbacks - configuration MUST come from Supabase
        if not self.patterns['splittable_prefixes']:
            raise ValueError("❌ CRITICAL: splittable_prefixes not found in Supabase config!")
        if not self.patterns['suffix_groups']:
            raise ValueError("❌ CRITICAL: suffix_groups not found in Supabase config!")
        if not self.suffix_categories:
            raise ValueError("❌ CRITICAL: suffix_patterns not found in Supabase config!")
        
        # Log what was loaded from variant_generation config
        variant_config = self.config.get('variant_generation')
        if variant_config:
            print(f"  ✅ Variant Generation Config Found:")
            print(f"     - high_value_combos: {len(variant_config.get('high_value_combos', []))} patterns")
            print(f"     - digit_words: {len(variant_config.get('digit_words', {}))} digits")
            print(f"     - number_patterns: {len(variant_config.get('number_patterns', []))} patterns")
            print(f"     - element_patterns: {len(variant_config.get('element_patterns', []))} patterns")
            print(f"     - separators: {variant_config.get('separators', [])}")
        else:
            raise ValueError("❌ CRITICAL: variant_generation config not found in Supabase!")
            
        print(f"  ✅ Prefixes: {len(self.patterns['splittable_prefixes'])} loaded")
        print(f"  ✅ Suffix Groups: {len(self.patterns['suffix_groups'])} loaded")
        print(f"  ✅ Separators: {self.patterns['separators']}")
    
    def split_suffix(self, word: str) -> List[Tuple[str, str, str]]:
        """
        Try to split word into base + suffix combinations
        Returns: List of (base, suffix, suffix_type) tuples
        """
        splits = []
        word_lower = word.lower()
        
        # Sort suffixes by length (longest first)
        sorted_suffixes = sorted(self.common_suffixes, key=len, reverse=True)
        
        for suffix in sorted_suffixes:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
                base = word[:-(len(suffix))]
                
                # Determine suffix type
                suffix_type = 'other'
                for cat, suffixes in self.suffix_categories.items():
                    if suffix in suffixes:
                        suffix_type = cat
                        break
                
                # Special check for ordinal numbers
                if suffix_type == 'ordinal' and self._could_be_number(base):
                    splits.insert(0, (base, suffix, suffix_type))  # Priority
                else:
                    splits.append((base, suffix, suffix_type))
        
        return splits
    
    def _could_be_number(self, text: str) -> bool:
        """Check if text could be a number word"""
        text_lower = text.lower()
        
        # Check direct number words
        for digit, words in self.digit_words.items():
            if text_lower in words:
                return True
        
        # Load number patterns from Supabase config - REQUIRED
        variant_config = self.config.get('variant_generation', {})
        number_patterns = variant_config.get('number_patterns')
        if not number_patterns:
            raise ValueError("❌ CRITICAL: number_patterns not found in variant_generation config! Please update Supabase configuration.")
        
        for pattern in number_patterns:
            if re.match(pattern, text_lower):
                return True
        
        return False
    
    def generate(self, term: str, max_variants: int = 50) -> List[str]:
        """Generate all variants of a term"""
        term = term.strip()
        if not term:
            return []
        
        variants = set([term, term.lower()])
        
        # Apply all generation strategies
        self._add_case_variants(term, variants)
        self._add_split_variants(term, variants)
        self._add_suffix_variants(term, variants)
        self._add_substitution_variants(term, variants)
        self._add_element_variants(term, variants)
        self._add_suffix_stripped_variants(term, variants)
        self._add_phonetic_variants(term, variants)
        
        # Sort and limit results
        result = list(variants)[:max_variants]
        if term in result:
            result.remove(term)
        return [term] + sorted(result, key=len)
    
    def _add_phonetic_variants(self, term: str, variants: Set[str]):
        """Add variants based on phonetic patterns from config"""
        term_lower = term.lower()
        
        # Apply all substitution patterns
        all_patterns = self.patterns['char_substitutions'] + self.patterns['phonetic_patterns']
        
        for old, new in all_patterns:
            if old in term_lower:
                variant = term_lower.replace(old, new)
                variants.add(variant)
                
                # For compound words with spaces or hyphens
                if ' ' in term_lower or '-' in term_lower:
                    parts = re.split(r'[\s\-]+', term_lower)
                    for i, part in enumerate(parts):
                        if old in part:
                            new_parts = parts.copy()
                            new_parts[i] = part.replace(old, new)
                            variants.add(' '.join(new_parts))
                            variants.add('-'.join(new_parts))
    
    def _add_case_variants(self, term: str, variants: Set[str]):
        """Add case variations"""
        variants.add(term.lower())
        variants.add(term.upper())
        variants.add(term.capitalize())
        
        # Title case for multi-word terms
        if ' ' in term:
            variants.add(term.title())
    
    def _add_split_variants(self, term: str, variants: Set[str]):
        """Add variants by splitting at prefix boundaries"""
        term_lower = term.lower()
        
        for prefix in self.patterns['splittable_prefixes']:
            if term_lower.startswith(prefix) and len(term) > len(prefix) + 2:
                rest = term[len(prefix):]
                rest_lower = rest.lower()
                
                for sep in self.patterns['separators']:
                    # Original case
                    variants.add(f"{prefix}{sep}{rest}")
                    # Lower case
                    variants.add(f"{prefix}{sep}{rest_lower}")
                    
                    # Apply phonetic variants to the second part
                    for old, new in self.patterns['phonetic_patterns']:
                        if old in rest_lower:
                            variant_rest = rest_lower.replace(old, new)
                            variants.add(f"{prefix}{sep}{variant_rest}")
    
    def _add_suffix_variants(self, term: str, variants: Set[str]):
        """Add variants by changing suffixes"""
        term_lower = term.lower()
        
        for suffix_group in self.patterns['suffix_groups']:
            for suffix in suffix_group:
                if term_lower.endswith(suffix):
                    base = term[:-len(suffix)]
                    # Try all other suffixes in the group
                    for alt_suffix in suffix_group:
                        if alt_suffix != suffix:
                            variants.add(base + alt_suffix)
                            variants.add((base + alt_suffix).lower())
                    break  # Only match one suffix per group
    
    def _add_substitution_variants(self, term: str, variants: Set[str]):
        """Add variants by character substitution - optimized for Dutch dental terms"""
        term_lower = term.lower()
        
        # Single substitutions - always apply these common Dutch patterns
        for old, new in self.patterns['char_substitutions'] + self.patterns['phonetic_patterns']:
            if old in term_lower:
                variant = term_lower.replace(old, new)
                variants.add(variant)
                # Also try reverse substitution
                if new in term_lower:
                    variants.add(term_lower.replace(new, old))
        
        # Smart double substitutions for longer terms (no cartesian product!)
        if len(term) > 8:  # Only for longer words that benefit from double substitutions
            # Get high-value combinations from Supabase config
            variant_config = self.config.get('variant_generation', {})
            
            # Check if smart doubling is enabled
            if not variant_config.get('enable_smart_doubling', True):
                return variants  # Skip if disabled
            
            high_value_combos_raw = variant_config.get('high_value_combos')
            if not high_value_combos_raw:
                # No high-value combos configured - skip double substitutions
                return variants
            
            # Convert from JSON format to tuple format
            high_value_combos = []
            for combo in high_value_combos_raw:
                if len(combo) == 2:
                    pattern1, pattern2 = combo
                    high_value_combos.append((tuple(pattern1), tuple(pattern2)))
            
            # Apply only specific high-value combinations
            for (old1, new1), (old2, new2) in high_value_combos:
                if old1 in term_lower and old2 in term_lower and old1 != old2:
                    # Apply both substitutions
                    variant = term_lower.replace(old1, new1).replace(old2, new2)
                    if variant != term_lower:
                        variants.add(variant)
                    
                    # Try reverse order too
                    variant_reverse = term_lower.replace(old2, new2).replace(old1, new1)
                    if variant_reverse != term_lower and variant_reverse != variant:
                        variants.add(variant_reverse)
    
    def _add_element_variants(self, term: str, variants: Set[str]):
        """Add variants for element numbers"""
        if not re.search(r'[1-8]', term):
            return
        
        # Load element patterns from Supabase config - REQUIRED
        variant_config = self.config.get('variant_generation', {})
        element_patterns = variant_config.get('element_patterns')
        if not element_patterns:
            raise ValueError("❌ CRITICAL: element_patterns not found in variant_generation config! Please update Supabase configuration.")
        
        for pattern in element_patterns:
            matches = re.findall(pattern, term)
            for d1, d2 in matches:
                # Generate variants with different separators
                for sep in self.patterns['element_separators']:
                    variants.add(f"{d1}{sep}{d2}")
                
                # Dutch number words
                if d1 in self.digit_words and d2 in self.digit_words:
                    for w1 in self.digit_words[d1]:
                        for w2 in self.digit_words[d2]:
                            variants.add(f"{w1} {w2}")
                            variants.add(f"{w1}-{w2}")
                            variants.add(f"{w1}{w2}")
    
    def _add_suffix_stripped_variants(self, term: str, variants: Set[str]):
        """Add variants with suffixes stripped"""
        splits = self.split_suffix(term)
        
        for base, suffix, suffix_type in splits:
            # Add the base alone
            variants.add(base)
            variants.add(base.lower())
            
            # Generate variants of the base
            base_variants = set()
            self._add_case_variants(base, base_variants)
            self._add_substitution_variants(base, base_variants)
            
            # Add base variants
            variants.update(base_variants)
            
            # For ordinal suffixes, try without connecting letters
            if suffix_type == 'ordinal':
                if base.endswith('d'):
                    variants.add(base[:-1])
                elif base.endswith('t'):
                    variants.add(base[:-1])


# Most frequent Dutch dental terms for pre-computation
COMMON_DENTAL_TERMS = [
    # Surfaces
    'distaal', 'mesiaal', 'buccaal', 'linguaal', 'occlusaal', 
    'approximaal', 'cervicaal', 'incisaal', 'palatinaal',
    
    # Pathology
    'cariës', 'abces', 'fistel', 'parodontitis', 'gingivitis',
    'pulpitis', 'periapicaal', 'radiculair',
    
    # Elements
    'element', 'tand', 'kies', 'molaar', 'premolaar',
    'incisief', 'canine', 'hoektand',
    
    # Radiology
    'radiolucentie', 'radioopaciteit', 'bitewing', 'okw',
    'panoramisch', 'cbct', 'periapicale',
    
    # Common procedures
    'vulling', 'extractie', 'wortelkanaal', 'kroon',
    'brug', 'implantaat', 'prothese'
]


class SmartMatcher:
    """Matches input against canonical terms using variant generation with caching and lazy loading"""
    
    def __init__(self, canonical_terms: List[str], generator: Optional[VariantGenerator] = None, config_data: Dict[str, Any] = None):
        self.canonical_terms = canonical_terms
        self.generator = generator or VariantGenerator(config_data=config_data)
        self.variant_map = {}
        self.variants_generated = set()  # Track which terms have variants generated
        self._all_variants_generated = False
        
        # Get variant settings from generator's config (already loaded from Supabase)
        if hasattr(self.generator, 'config') and self.generator.config:
            self.variant_config = self.generator.config.get('variant_generation')
            if not self.variant_config:
                raise ValueError("❌ CRITICAL: variant_generation config not found in generator config!")
        else:
            # Fallback to config_data parameter if provided
            self.variant_config = (config_data or {}).get('variant_generation')
            if not self.variant_config:
                raise ValueError("❌ CRITICAL: variant_generation config not found - generator has no config!")
        
        self.use_lazy_loading = self.variant_config.get('use_lazy_loading')
        if self.use_lazy_loading is None:
            raise ValueError("❌ CRITICAL: use_lazy_loading not found in variant_generation config!")
            
        self.lru_cache_size = self.variant_config.get('lru_cache_size')
        if self.lru_cache_size is None:
            raise ValueError("❌ CRITICAL: lru_cache_size not found in variant_generation config!")
            
        self.precompute_count = self.variant_config.get('precompute_common')
        if self.precompute_count is None:
            raise ValueError("❌ CRITICAL: precompute_common not found in variant_generation config!")
        
        # Initialize with lazy loading if enabled (from Supabase)
        if self.use_lazy_loading:
            self._precompute_common_terms()
        else:
            # Generate all variants upfront if lazy loading is disabled
            self._build_variant_map()
        
        # Try to load phonetic matcher if available
        self.phonetic_matcher = None
        self._init_phonetic_matcher()
        
        # Create cached version of match method with configurable cache size
        self._match_cached = lru_cache(maxsize=self.lru_cache_size)(self._match_internal)
    
    def _init_phonetic_matcher(self):
        """Initialize phonetic matcher if available and enabled"""
        # Check multiple sources for phonetic_enabled setting
        import os
        
        # 1. Check environment variable first
        env_phonetic_enabled = os.getenv('PHONETIC_ENABLED', '').lower() in ('true', '1', 'yes')
        
        # 2. Check config data if generator has config
        config_phonetic_enabled = False
        if hasattr(self.generator, 'config_data') and self.generator.config_data:
            config_phonetic_enabled = self.generator.config_data.get('matching', {}).get('phonetic_enabled', False)
        
        # 3. Check the generator's internal config as fallback
        fallback_phonetic_enabled = False
        if hasattr(self.generator, 'config'):
            fallback_phonetic_enabled = self.generator.config.get('matching', {}).get('phonetic_enabled', False)
        
        # Enable if any source indicates it should be enabled
        phonetic_enabled = env_phonetic_enabled or config_phonetic_enabled or fallback_phonetic_enabled
        
        if not phonetic_enabled:
            return
            
        try:
            from phonetic_matcher import DutchPhoneticMatcher
            # Try to use global cache from server - DELAYED IMPORT to avoid circular dependency
            try:
                import sys
                if 'server_windows_spsc' in sys.modules:
                    # Server is already loaded, safe to import
                    server_module = sys.modules['server_windows_spsc']
                    if hasattr(server_module, 'GLOBAL_PHONETIC_CACHE'):
                        self.phonetic_matcher = DutchPhoneticMatcher(
                            self.generator.config, 
                            phonetic_cache=server_module.GLOBAL_PHONETIC_CACHE,
                            soundex_cache=server_module.GLOBAL_SOUNDEX_CACHE,
                            phonetic_index=server_module.GLOBAL_PHONETIC_INDEX
                        )
                    else:
                        # Cache not yet built, create without cache
                        self.phonetic_matcher = DutchPhoneticMatcher(self.generator.config)
                else:
                    # Server not loaded yet, create without cache
                    self.phonetic_matcher = DutchPhoneticMatcher(self.generator.config)
            except (ImportError, AttributeError):
                # Fallback to creating new matcher without cache
                self.phonetic_matcher = DutchPhoneticMatcher(self.generator.config)
        except ImportError:
            pass
    
    def _precompute_common_terms(self):
        """Pre-generate variants only for the most common dental terms"""
        # Determine which common terms are in our canonical list
        common_to_generate = []
        # Use precompute_count from Supabase config
        limit = self.precompute_count if hasattr(self, 'precompute_count') else 50
        for term in COMMON_DENTAL_TERMS[:limit]:
            if term in self.canonical_terms:
                common_to_generate.append(term)
        
        # If we have fewer than 50 common terms, add some from canonical list
        if len(common_to_generate) < 50:
            for term in self.canonical_terms[:50 - len(common_to_generate)]:
                if term not in common_to_generate:
                    common_to_generate.append(term)
        
        # Generate variants for common terms
        for term in common_to_generate:
            self._generate_variants_for_term(term)
    
    def _generate_variants_for_term(self, term: str):
        """Generate variants for a single term (lazy loading support)"""
        if term not in self.variants_generated:
            variants = self.generator.generate(term)
            for variant in variants:
                normalized = _normalize_text(variant)
                if normalized not in self.variant_map:
                    self.variant_map[normalized] = term
            
            # HYPHEN NORMALIZATION: Also add dehyphenated version of canonical term
            # This ensures "peri-apicaal" also creates variant "periapicaal"
            if '-' in term:
                dehyphenated = _normalize_text(term.replace('-', ''))
                if dehyphenated not in self.variant_map:
                    self.variant_map[dehyphenated] = term
            
            self.variants_generated.add(term)
    
    def _generate_remaining_variants(self):
        """Generate variants for all remaining terms (called on-demand)"""
        if not self._all_variants_generated:
            for term in self.canonical_terms:
                if term not in self.variants_generated:
                    self._generate_variants_for_term(term)
            self._all_variants_generated = True
    
    def match(self, text: str) -> Optional[str]:
        """Find canonical form of input text with caching"""
        return self._match_cached(text)
    
    def _match_internal(self, text: str) -> Optional[str]:
        """Internal match logic (cached by LRU)"""
        normalized = _normalize_text(text)
        
        # Direct lookup in current variant map
        if normalized in self.variant_map:
            return self.variant_map[normalized]
        
        # If not all variants generated yet, generate remaining (lazy loading)
        if not self._all_variants_generated:
            self._generate_remaining_variants()
            # Try lookup again after generation
            if normalized in self.variant_map:
                return self.variant_map[normalized]
        
        # Try phonetic matching if available
        if self.phonetic_matcher:
            matching_config = self.generator.config.get('matching')
            if not matching_config:
                raise ValueError("❌ CRITICAL: matching config not found in Supabase!")
            threshold = matching_config.get('fuzzy_threshold')
            if threshold is None:
                raise ValueError("❌ CRITICAL: fuzzy_threshold not found in matching config!")
            
            result = self.phonetic_matcher.match(text, self.canonical_terms)
            if result and result[1] >= threshold:
                return result[0]
        
        # Try splitting off suffixes
        splits = self.generator.split_suffix(text)
        for base, suffix, suffix_type in splits:
            base_normalized = _normalize_text(base)
            
            # Direct match on base
            if base_normalized in self.variant_map:
                return self.variant_map[base_normalized]
            
            # Try generating variants of the base
            max_base_variants = self.generator.config.get('max_base_variants', 10)
            base_variants = self.generator.generate(base, max_variants=max_base_variants)
            
            for variant in base_variants:
                norm_variant = _normalize_text(variant)
                if norm_variant in self.variant_map:
                    return self.variant_map[norm_variant]
        
        # Try generating variants of full input
        max_input_variants = self.generator.config.get('max_input_variants', 20)
        input_variants = self.generator.generate(text, max_variants=max_input_variants)
        
        for variant in input_variants:
            norm_variant = _normalize_text(variant)
            if norm_variant in self.variant_map:
                return self.variant_map[norm_variant]
        
        return None
    
    def match_with_info(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Match and return additional info about how the match was made
        Returns: (canonical_form, info_dict) or None
        """
        normalized = _normalize_text(text)
        
        # Direct lookup
        if normalized in self.variant_map:
            return self.variant_map[normalized], {'match_type': 'direct'}
        
        # Phonetic match
        if self.phonetic_matcher:
            matching_config = self.generator.config.get('matching')
            if not matching_config:
                raise ValueError("❌ CRITICAL: matching config not found in Supabase!")
            threshold = matching_config.get('fuzzy_threshold')
            if threshold is None:
                raise ValueError("❌ CRITICAL: fuzzy_threshold not found in matching config!")
            
            result = self.phonetic_matcher.match(text, self.canonical_terms)
            if result and result[1] >= threshold:
                return result[0], {
                    'match_type': 'phonetic',
                    'confidence': result[1]
                }
        
        # Try splitting off suffixes
        splits = self.generator.split_suffix(text)
        for base, suffix, suffix_type in splits:
            base_normalized = _normalize_text(base)
            
            if base_normalized in self.variant_map:
                return self.variant_map[base_normalized], {
                    'match_type': 'suffix_split',
                    'base': base,
                    'suffix': suffix,
                    'suffix_type': suffix_type
                }
        
        # Try variants
        max_input_variants = self.generator.config.get('max_input_variants', 20)
        input_variants = self.generator.generate(text, max_variants=max_input_variants)
        
        for variant in input_variants:
            norm_variant = _normalize_text(variant)
            if norm_variant in self.variant_map:
                return self.variant_map[norm_variant], {
                    'match_type': 'variant',
                    'variant_used': variant
                }
        
        return None
    
    def add_term(self, term: str):
        """Add a new canonical term and generate its variants"""
        if term not in self.canonical_terms:
            self.canonical_terms.append(term)
            # Generate variants for the new term
            self._generate_variants_for_term(term)
            # Clear the cache since we have a new term
            self._match_cached.cache_clear()


# DIGIT_WORDS are loaded from Supabase config (variant_generation.digit_words) - see line 28


# Test function
if __name__ == "__main__":
    print("Testing Config-Based Variant Generator")
    print("=" * 60)
    
    try:
        # Test generator
        generator = VariantGenerator()
        print("✓ Config loaded successfully")
        
        # Show loaded patterns
        print(f"\nLoaded patterns:")
        print(f"  - Prefixes: {len(generator.patterns['splittable_prefixes'])}")
        print(f"  - Suffix groups: {len(generator.patterns['suffix_groups'])}")
        print(f"  - Phonetic patterns: {len(generator.patterns['char_substitutions'] + generator.patterns['phonetic_patterns'])}")
        
        test_words = [
            "radiolucentie",
            "vierde",
            "element 14",
            "distaal"
        ]
        
        print("\nVariant generation tests:")
        for word in test_words:
            variants = generator.generate(word, max_variants=10)
            print(f"\n'{word}' generates {len(variants)} variants:")
            for i, variant in enumerate(variants[:5]):
                print(f"  {i+1}. {variant}")
            if len(variants) > 5:
                print(f"  ... and {len(variants)-5} more")
        
        # Test matching
        print("\n" + "=" * 60)
        print("Testing SmartMatcher:")
        
        canonical_terms = ["radiolucentie", "element 14", "distaal", "mesiaal"]
        matcher = SmartMatcher(canonical_terms)
        
        test_inputs = [
            "radio lucentie",
            "radiolicentie", 
            "distal",
            "een vier",
            "mesial"
        ]
        
        print("\nMatching tests:")
        for text in test_inputs:
            result = matcher.match_with_info(text)
            if result:
                canonical, info = result
                print(f"'{text}' → '{canonical}' ({info['match_type']})")
            else:
                print(f"'{text}' → No match found")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure default_config.json exists with all required patterns!")
