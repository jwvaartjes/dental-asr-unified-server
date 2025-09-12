#!/usr/bin/env python3
"""
learnable_normalizer.py - Normalizer with learning capabilities
Config-based versie met phonetic matching
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
from functools import lru_cache
from difflib import SequenceMatcher
from .core.variant_generator import VariantGenerator, SmartMatcher, _normalize_text
from .utils import NormalizationUtils
# json_handler removed - using Supabase data

# Import phonetic matcher if available
try:
    from phonetic_matcher import DutchPhoneticMatcher
except ImportError:
    DutchPhoneticMatcher = None

class LearnableVariantGenerator(VariantGenerator):
    """Extended variant generator that can learn from user feedback"""
    
    def __init__(self, custom_patterns_data: Dict[str, Any] = None, config_data: Dict[str, Any] = None, 
                 supabase_mgr = None, user_id: str = None):
        # Initialize with data instead of file paths
        super().__init__(config_data or {})
        self.custom_patterns_data = custom_patterns_data or {}
        self.supabase_mgr = supabase_mgr
        self.user_id = user_id
        self.direct_mappings = {}
        self.multi_word_mappings = {}
        self.failed_matches = []
        self.load_custom_patterns()
        
        # Add phonetic matcher if available AND enabled in config
        # Don't initialize here - let DentalNormalizerLearnable handle it centrally
        self.phonetic_matcher = None  # Will be set by parent class if needed
    
    def load_custom_patterns(self):
        """Load user-defined patterns from Supabase data"""
        try:
            # Use provided Supabase data instead of file
            custom = self.custom_patterns_data
            self.direct_mappings = custom.get('direct_mappings', {})
            self.multi_word_mappings = custom.get('multi_word_mappings', {})
            
            print(f"Loaded {len(self.direct_mappings)} single mappings")
            print(f"Loaded {len(self.multi_word_mappings)} multi-word mappings")
        except Exception as e:
            print(f"Error loading custom patterns: {e}")
            self.direct_mappings = {}
            self.multi_word_mappings = {}
    
    def save_custom_patterns(self):
        """Save custom patterns to Supabase"""
        custom = {
            'direct_mappings': self.direct_mappings,
            'multi_word_mappings': self.multi_word_mappings,
            'last_updated': datetime.now().isoformat()
        }
        
        # Save to Supabase if manager available
        if self.supabase_mgr and self.user_id:
            self.supabase_mgr.save_custom_patterns(self.user_id, custom)
        else:
            print("⚠️ No Supabase manager - patterns not saved to cloud")
    
    def add_mapping(self, variant: str, canonical: str) -> bool:
        """Add a direct mapping from variant to canonical form"""
        variant_norm = _normalize_text(variant)
        
        if variant_norm and canonical:
            self.direct_mappings[variant_norm] = canonical
            self.save_custom_patterns()
            return True
        return False
    
    def add_multi_word_mapping(self, phrase: str, canonical: str) -> bool:
        """Add a multi-word mapping"""
        phrase_norm = _normalize_text(phrase)
        
        if phrase_norm and canonical:
            self.multi_word_mappings[phrase_norm] = canonical
            self.save_custom_patterns()
            return True
        return False
    
    def generate(self, term: str, max_variants: int = 50) -> List[str]:
        """Generate variants, checking custom mappings first"""
        term_norm = _normalize_text(term)
        
        # Check direct mappings
        if term_norm in self.direct_mappings:
            return [self.direct_mappings[term_norm]]
        
        # Normal generation
        return super().generate(term, max_variants)
    
    def track_failed_match(self, input_text: str, context: str = ""):
        """Track when a match fails"""
        self.failed_matches.append({
            'input': input_text,
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        # Keep only last 100 failed matches
        if len(self.failed_matches) > 100:
            self.failed_matches = self.failed_matches[-100:]
    


class DentalNormalizerLearnable:
    """Dental normalizer with learning capabilities - SUPABASE CLOUD VERSION"""
    
    def __init__(self, lexicon_data: Dict[str, Any], config_data: Dict[str, Any] = None, 
                 custom_patterns_data: Dict[str, Any] = None, protect_words_data: Dict[str, Any] = None,
                 supabase_mgr = None, user_id: str = None):
        """Initialize with Supabase data instead of file paths"""
        # Use provided data instead of loading from files
        self.lex = lexicon_data
        self.config = config_data or {}
        self.supabase_mgr = supabase_mgr
        self.user_id = user_id
        
        # Use learnable variant generator with Supabase data
        self.generator = LearnableVariantGenerator(
            custom_patterns_data=custom_patterns_data or {},
            config_data=config_data or {},
            supabase_mgr=supabase_mgr,
            user_id=user_id
        )
        
        # Add phonetic matcher if available AND enabled in config
        phonetic_enabled = config_data.get('matching', {}).get('phonetic_enabled', True) if config_data else True
        
        if DutchPhoneticMatcher and phonetic_enabled:
            try:
                # Try to import global caches from server
                try:
                    from server_windows_spsc import (GLOBAL_PHONETIC_CACHE, GLOBAL_SOUNDEX_CACHE, 
                                                   GLOBAL_PHONETIC_INDEX)
                    self.phonetic_matcher = DutchPhoneticMatcher(
                        config_data=config_data, 
                        phonetic_cache=GLOBAL_PHONETIC_CACHE,
                        soundex_cache=GLOBAL_SOUNDEX_CACHE,
                        phonetic_index=GLOBAL_PHONETIC_INDEX
                    )
                    print(f"Phonetic matching enabled with global cache (config: phonetic_enabled = {phonetic_enabled})")
                except ImportError:
                    # Fallback to creating new matcher without cache (for standalone use)
                    self.phonetic_matcher = DutchPhoneticMatcher(config_data=config_data)
                    print(f"Phonetic matching enabled without cache (config: phonetic_enabled = {phonetic_enabled})")
            except Exception as e:
                self.phonetic_matcher = None
                print(f"Phonetic matching not available: {e}")
        else:
            self.phonetic_matcher = None
            if not phonetic_enabled:
                print("Phonetic matching disabled (config: phonetic_enabled = False)")
            else:
                print("Phonetic matching not available (module not found)")
        
        # Share the phonetic matcher with the generator
        if hasattr(self.generator, 'phonetic_matcher'):
            self.generator.phonetic_matcher = self.phonetic_matcher
        
        # Element sets (deze blijven speciaal)
        self.elements = set(self.lex.get("elements_permanent", [])) | set(self.lex.get("elements_primary", []))
        
        # Load protected words from Supabase data
        self.protected_words = self._load_protected_words(protect_words_data)
        
        # Build element variant map
        self.element_variant_map = {}
        if "element_variants" in self.lex:
            for elem, variants in self.lex["element_variants"].items():
                for variant in variants:
                    self.element_variant_map[_normalize_text(variant)] = elem
        
        # Initialize dynamic matchers
        self.matchers = {}
        self._init_dynamic_matchers()
        
        # Word-level cache for ultra-fast lookups
        self._word_cache = {}
        self._build_word_cache()
        
        # Cache voor performance
        self._multi_word_cache = {}
        self._all_canonical_terms = None
        
        print(f"Initialized with {len(self.matchers)} dynamic matchers")
        print(f"Config loaded from Supabase cloud")
    
    
    def _load_protected_words(self, protect_words_data: Dict[str, Any] = None) -> list:
        """Load protected words from Supabase data with fallback to config"""
        try:
            # Use provided Supabase data
            protect_data = protect_words_data or {}
            
            # Handle new Supabase format with "protected_words" array
            if protect_data and "protected_words" in protect_data:
                protected_words = protect_data["protected_words"]
                if protected_words:
                    print(f"✅ Loaded {len(protected_words)} protected words from Supabase")
                    return protected_words
                else:
                    print("ℹ️  Empty protected_words array in Supabase")
                    return []
            
            # Handle legacy format with "categories"
            elif protect_data and "categories" in protect_data:
                # Flatten all words from all categories
                protected_words = []
                for category_name, category_data in protect_data.get("categories", {}).items():
                    words = category_data.get("words", [])
                    protected_words.extend(words)
                
                if protected_words:
                    print(f"✅ Loaded {len(protected_words)} protected words from Supabase categories")
                    return protected_words
                else:
                    print("ℹ️  Empty categories in protected words data")
                    return []
            
            else:
                # Fallback to config if no protected words data
                fallback_words = self.config.get('protect_words', [])
                if fallback_words:
                    print(f"⚠️  Using fallback protect_words from config ({len(fallback_words)} words)")
                    return fallback_words
                else:
                    print("ℹ️  No protected words found in Supabase or config")
                    return []
            
        except (FileNotFoundError, KeyError, AttributeError) as e:
            # Fallback to config for backwards compatibility
            fallback_words = self.config.get('protect_words', [])
            if fallback_words:
                print(f"⚠️  Error loading protected words from Supabase: {e}")
                print(f"⚠️  Using fallback protect_words from config ({len(fallback_words)} words)")
            else:
                print(f"❌ Error loading protected words: {e}")
                print("ℹ️  No protected words found in config fallback")
            return fallback_words
    
    def _init_dynamic_matchers(self):
        """Dynamically initialize matchers voor ALLE categorieën in lexicon"""
        
        # Skip deze keys - ze zijn geen categorieën voor normalisatie
        skip_keys = {'elements_permanent', 'elements_primary', 'element_variants'}
        
        # Voor elke key in de lexicon
        for category_key in self.lex.keys():
            if category_key in skip_keys:
                continue
                
            # Check of het een lijst is (canonical terms)
            if isinstance(self.lex[category_key], list):
                # Maak een matcher voor deze categorie
                self.matchers[category_key] = SmartMatcher(
                    self.lex[category_key], 
                    self.generator
                )
                print(f"Created matcher for '{category_key}' with {len(self.lex[category_key])} terms")
        
        print(f"Initialized with {len(self.matchers)} dynamic matchers")
    
    def _build_word_cache(self):
        """Build word-level cache for instant lookups"""
        print("🔄 Building word-level cache...")
        
        # Cache all canonical terms by first word
        for category, terms in self.lex.items():
            if isinstance(terms, list):
                for term in terms:
                    words = term.lower().split()
                    if words:
                        first_word = words[0]
                        if first_word not in self._word_cache:
                            self._word_cache[first_word] = []
                        self._word_cache[first_word].append({
                            'term': term,
                            'category': category,
                            'words': words
                        })
        
        print(f"✅ Word cache built with {len(self._word_cache)} entries")
    
    def get_config(self) -> dict:
        """Get current configuration"""
        return self.config
    
    def update_config(self, updates: dict) -> bool:
        """Update configuration values"""
        try:
            # Deep merge updates into config
            import copy
            new_config = copy.deepcopy(self.config)
            
            def deep_merge(base, update):
                for key, value in update.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
            
            deep_merge(new_config, updates)
            
            # Save to Supabase
            if self.supabase_mgr and self.user_id:
                success = self.supabase_mgr.save_config(self.user_id, new_config)
                if not success:
                    return False
            else:
                print("⚠️ No Supabase manager - config not saved to cloud")
            
            # Reload config
            self.config = new_config
            
            # Reinitialize phonetic matcher if needed
            if self.phonetic_matcher and DutchPhoneticMatcher:
                self.phonetic_matcher = DutchPhoneticMatcher(self.config_path)
            
            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def get_all_canonical_terms(self) -> Set[str]:
        """Get ALL canonical terms from all categories - cached"""
        if self._all_canonical_terms is None:
            self._all_canonical_terms = set()
            
            for key, value in self.lex.items():
                if isinstance(value, list):
                    self._all_canonical_terms.update(value)
                    
        return self._all_canonical_terms
    
    def normalize_dynamic(self, text: str) -> Optional[Tuple[str, str, str]]:
        """Try to normalize text using any dynamic matcher
        Returns: (normalized_text, category, match_type) or None
        
        IMPROVED: Now selects the BEST match across all categories, not just the first match
        """
        # First check if text is EXACTLY a canonical term (case-sensitive)
        for category, terms in self.lex.items():
            if isinstance(terms, list):
                for term in terms:
                    if text == term:  # EXACT match, case-sensitive
                        # It's already canonical - exact match
                        return text, category, 'library'
        
        # Then check case-insensitive but still exact spelling
        text_lower = text.lower()
        for category, terms in self.lex.items():
            if isinstance(terms, list):
                for term in terms:
                    if text_lower == term.lower():  # Case-insensitive but exact spelling
                        # It's canonical with different case
                        return term, category, 'library'
        
        # Try hyphen removal for canonical matching (before fuzzy/phonetic)
        if '-' in text:
            text_no_hyphen = text.replace('-', '')
            
            # Check exact match without hyphens
            for category, terms in self.lex.items():
                if isinstance(terms, list):
                    for term in terms:
                        if text_no_hyphen == term:
                            return term, category, 'library'
            
            # Check case-insensitive match without hyphens
            text_no_hyphen_lower = text_no_hyphen.lower()
            for category, terms in self.lex.items():
                if isinstance(terms, list):
                    for term in terms:
                        if text_no_hyphen_lower == term.lower():
                            return term, category, 'library'
        
        # Collect ALL possible matches from all matchers
        all_matches = []
        
        for category, matcher in self.matchers.items():
            # Use match_with_info to get match type
            if hasattr(matcher, 'match_with_info'):
                result = matcher.match_with_info(text)
                if result:
                    matched_term, info = result
                    match_type = info.get('match_type', 'fuzzy')
                    score = info.get('confidence', info.get('score', 0.8))  # Check confidence first, then score
                    
                    # Convert match_type to our standard types
                    if match_type == 'direct':
                        # Only treat as library if it's truly a direct match (no transformation)
                        if text.lower() == matched_term.lower():
                            match_type = 'library'
                        else:
                            # It's a fuzzy match that was labeled as direct by the matcher
                            match_type = 'fuzzy'
                    elif match_type == 'phonetic':
                        match_type = 'phonetic'
                    else:
                        match_type = 'fuzzy'
                    
                    all_matches.append((matched_term, category, match_type, score))
            else:
                # Fallback to basic match
                result = matcher.match(text)
                if result:
                    # Calculate fuzzy score for comparison
                    from difflib import SequenceMatcher
                    score = SequenceMatcher(None, text.lower(), result.lower()).ratio()
                    all_matches.append((result, category, 'fuzzy', score))
        
        # If no matches found, return None
        if not all_matches:
            return None
        
        # Select the BEST match based on score
        # Sort by score (descending), then by match_type priority (library > fuzzy > phonetic)
        type_priority = {'library': 0, 'fuzzy': 1, 'phonetic': 2}
        all_matches.sort(key=lambda x: (-x[3], type_priority.get(x[2], 3)))
        
        # Return the best match (without the score)
        best_match = all_matches[0]
        return best_match[0], best_match[1], best_match[2]
    
    def check_multi_word_mapping(self, text: str) -> Optional[str]:
        """Check if text matches any multi-word mapping"""
        text_norm = _normalize_text(text)
        
        # Check cache first
        if text_norm in self._multi_word_cache:
            return self._multi_word_cache[text_norm]
        
        # Check multi-word mappings
        if text_norm in self.generator.multi_word_mappings:
            result = self.generator.multi_word_mappings[text_norm]
            self._multi_word_cache[text_norm] = result
            return result
        
        # Cache negative result
        self._multi_word_cache[text_norm] = None
        return None

    def parse_element(self, text: str) -> Optional[str]:
        """Parse element number from text - smart matching with element_variants"""
        # Clean the text: lowercase, remove punctuation, normalize spaces
        text_clean = text.lower()
        # Remove punctuation but KEEP commas, periods, hyphens, and colons (needed for parsing)
        # Remove only sentence-ending punctuation and semicolons
        # KEEP colons for element formatting (e.g., "Element 41:")
        text_clean = re.sub(r'[;!?]', '', text_clean)
        # Keep periods - they prevent number combination just like commas
        # Normalize multiple spaces to single space
        text_clean = ' '.join(text_clean.split())
        
        # Normalize for matching (removes remaining special chars)
        text_normalized = _normalize_text(text_clean)

        # First check if entire text is element variant
        if hasattr(self, 'element_variant_map') and text_normalized in self.element_variant_map:
            elem = self.element_variant_map[text_normalized]
            if elem in self.elements:
                return elem

        # Check custom mappings
        if text_normalized in self.generator.direct_mappings:
            mapped = self.generator.direct_mappings[text_normalized]
            if mapped.startswith("element "):
                elem = mapped.replace("element ", "")
                if elem in self.elements:
                    return elem

        # Search for element patterns within the text
        if hasattr(self, 'element_variant_map'):
            # Sort by length (longest first) to match longest patterns first
            for variant in sorted(self.element_variant_map.keys(), key=len, reverse=True):
                if variant in text_normalized:
                    elem = self.element_variant_map[variant]
                    if elem in self.elements:
                        return elem

        # Legacy pattern matching as fallback
        patterns = [
            r'\belement\s+([1-8])([1-8])\b',
            r'\b([1-8])\s*-\s*([1-8])\b',  # Hyphen (range notation)
            r'\b([1-8]),([1-8])\b',  # Dental notation with comma (no space): "1,6" -> "16"
            r'\b([1-8])\.([1-8])\b',  # Dental notation with period: "1.6" -> "16"
            r'\b([1-8])/([1-8])\b',  # Dental notation with forward slash: "1/6" -> "16"
            # Only match consecutive digits WITHOUT comma, period, slash, or space between them
            r'(?<!\been\s)(?<!\been)([1-8])(?![\s,\./])([1-8])\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_clean)
            if match:
                elem = match.group(1) + match.group(2)
                if elem in self.elements:
                    return elem

        return None
    
    # Backwards compatibility functies
    def parse_surface(self, text: str) -> Optional[Tuple[str, bool]]:
        """Parse surface from text - gebruik dynamic matchers"""
        # Try combo surfaces first
        if 'combo_surfaces' in self.matchers:
            combo = self.matchers['combo_surfaces'].match(text)
            if combo:
                return combo, True
        
        # Try regular surfaces
        if 'surfaces' in self.matchers:
            surface = self.matchers['surfaces'].match(text)
            if surface:
                return surface, False
        
        return None
    
    def parse_rx_finding(self, text: str) -> Optional[str]:
        """Parse RX finding - gebruik dynamic matcher"""
        if 'rx_findings' in self.matchers:
            return self.matchers['rx_findings'].match(text)
        return None
    
    def parse_rx_anatomy(self, text: str) -> Optional[str]:
        """Parse RX anatomy - gebruik dynamic matcher"""
        if 'rx_anatomy' in self.matchers:
            return self.matchers['rx_anatomy'].match(text)
        return None
    
    def parse_rx_descriptor(self, text: str) -> Optional[str]:
        """Parse RX descriptor - gebruik dynamic matcher"""
        if 'rx_descriptors' in self.matchers:
            return self.matchers['rx_descriptors'].match(text)
        return None
    
    def parse_rx(self, text: str) -> Optional[Dict[str, str]]:
        """Parse RX terms - gebruik dynamic matchers"""
        out = {}
        
        if 'rx_types' in self.matchers:
            rx_type = self.matchers['rx_types'].match(text)
            if rx_type:
                out['type'] = rx_type
        
        if 'rx_quality' in self.matchers:
            quality = self.matchers['rx_quality'].match(text)
            if quality:
                out['quality'] = quality
        
        if 'rx_density' in self.matchers:
            density = self.matchers['rx_density'].match(text)
            if density:
                out['density'] = density
        
        return out if out else None
    
    def parse_ceph(self, text: str) -> Optional[str]:
        """Parse cephalometric landmark - gebruik dynamic matcher"""
        if 'ceph_landmarks' in self.matchers:
            return self.matchers['ceph_landmarks'].match(text)
        return None

    def find_multi_word_matches(self, words: List[str], start_index: int) -> Optional[Tuple[str, int, str, str]]:
        """
        Look ahead to find the longest multi-word match starting from start_index
        Returns: (matched_term, words_consumed, match_type, category) or None
        """
        # Check progressively longer sequences (multi-word only, minimum 2 words)
        max_words = self.config.get('multi_word_matching', {}).get('max_word_count', 5)
        for length in range(min(max_words, len(words) - start_index), 1, -1):
            # Build the phrase
            phrase_parts = []
            for i in range(length):
                word = words[start_index + i]
                # Clean punctuation from edges but keep internal punctuation
                if i == length - 1:  # Last word
                    # Use tokenization to separate punctuation
                    pre, core, post = NormalizationUtils.split_token(word)
                    word_clean = core
                else:
                    word_clean = word
                phrase_parts.append(word_clean)
            
            phrase = ' '.join(phrase_parts)
            phrase_normalized = _normalize_text(phrase)
            
            # First check custom multi-word mappings
            if phrase_normalized in self.generator.multi_word_mappings:
                return self.generator.multi_word_mappings[phrase_normalized], length, 'custom', 'multi_word_mapping'
            
            # FIRST: Check for exact matches in all canonical terms (library)
            for category, terms in self.lex.items():
                if isinstance(terms, list):
                    for term in terms:
                        # Only match if same word count (don't match 2-word phrase to 1-word term)
                        if len(term.split()) == length:
                            if _normalize_text(term) == phrase_normalized:
                                return term, length, 'library', category
            
            # SECOND: Only if no exact match found, try fuzzy matching
            # BUT: Only if individual words in phrase are NOT already canonical
            
            # Check if all individual words are already canonical (for multi-word phrases)
            all_words_canonical = False
            if length >= 2:  # Only for multi-word phrases
                all_words_canonical = True
                for word in phrase_parts:
                    word_normalized = _normalize_text(word)
                    is_canonical = False
                    
                    # Check if this word exists as a canonical term
                    for category, terms in self.lex.items():
                        if isinstance(terms, list):
                            for term in terms:
                                if _normalize_text(term) == word_normalized:
                                    is_canonical = True
                                    break
                    
                    if not is_canonical:
                        all_words_canonical = False
                        break
            
            # If all individual words are canonical, skip fuzzy matching
            # This prevents "distopalatinale radix" -> "palatinale radix"
            if length >= 2 and all_words_canonical:
                pass  # Skip fuzzy matching - let individual words be processed
            else:
                # NEW: Try fuzzy matching on the complete phrase first
                if length >= 2:
                    # CRITICAL: Don't fuzzy match phrases containing element patterns
                    # This prevents "2-3" from matching ">1/3 - <2/3"
                    contains_element_pattern = False
                    for part in phrase_parts:
                        # Use tokenization for part processing
                        _, part_core, _ = NormalizationUtils.split_token(part)
                        if re.match(r'^\d+[-]?\d*$', part_core):
                            contains_element_pattern = True
                            break
                    
                    if not contains_element_pattern:
                        # Try fuzzy match on entire phrase
                        for category, terms in self.lex.items():
                            if isinstance(terms, list):
                                for term in terms:
                                    if len(term.split()) == length:
                                        # Use fuzzy matching on complete phrase
                                        similarity = SequenceMatcher(None, phrase_normalized, _normalize_text(term)).ratio()
                                        if similarity >= 0.85:  # High threshold for multi-word
                                            return term, length, 'fuzzy', category
                
                # FALLBACK: Use existing matcher-based fuzzy matching
                # But still check for element patterns to prevent "2-3" matching fractions
                contains_element_pattern = False
                for part in phrase_parts:
                    # Use tokenization for part processing
                    _, part_core, _ = NormalizationUtils.split_token(part)
                    if re.match(r'^\d+[-]?\d*$', part_core):
                        contains_element_pattern = True
                        break
                
                if not contains_element_pattern:
                    for category, terms in self.lex.items():
                        if isinstance(terms, list) and self.matchers.get(category):
                            result = self.matchers[category].match(phrase)
                            # CRITICAL: Only accept result if it has same word count as input
                            if result and len(result.split()) == length:
                                return result, length, 'fuzzy', category
        
        return None

    def normalize(self, text: str, return_mappings: bool = False) -> Optional[Any]:
        """Main normalization function - uses smart element_variants matching
        
        Args:
            text: Text to normalize
            return_mappings: If True, returns (normalized_text, mappings) tuple
                           mappings is a list of dicts with:
                           - original: original word
                           - normalized: normalized word  
                           - type: 'custom', 'fuzzy', 'phonetic', 'element', 'library', or None
                           - category: category that matched (if applicable)
        """
        # Track word mappings if requested
        word_mappings = [] if return_mappings else None
        
        # Check if entire text is a known mapping
        if _normalize_text(text) in self.generator.direct_mappings:
            result = self.generator.direct_mappings[_normalize_text(text)]
            if return_mappings:
                word_mappings.append({
                    'original': text,
                    'normalized': result,
                    'type': 'custom',
                    'category': 'direct_mapping'
                })
                return result, word_mappings
            return result
        
        # Preprocess: remove spaces in patterns like "1 -5" -> "1-5"
        text = re.sub(r'(\d)\s+(-\d)', r'\1\2', text)
        
        # NEW PREPROCESSING: Split hyphenated words that contain descriptive terms
        # This ensures "licht-mucosale" becomes "licht mucosale" for proper processing
        descriptive_terms = ['licht', 'matig', 'ernstig', 'mild', 'fors', 'gering', 'sterk', 'zwak']
        words_to_process = text.split()
        preprocessed_words = []
        
        for word in words_to_process:
            if '-' in word:
                parts = word.split('-')
                # Check if first part is a descriptive term
                if len(parts) >= 2 and parts[0].lower() in descriptive_terms:
                    # Split into separate words
                    preprocessed_words.extend(parts)
                else:
                    # Keep as-is
                    preprocessed_words.append(word)
            else:
                preprocessed_words.append(word)
        
        text = ' '.join(preprocessed_words)
        
        # Special preprocessing for "een een" duplicates
        # Only parse as "11" if preceded by dental context words
        dental_context_words = ['element', 'tand', 'kies', 'molaar', 'premolaar']
        words_lower = text.lower().split()
        
        # Check for "een een" pattern
        if 'een' in words_lower:
            new_words = []
            skip_next = False
            
            for idx, word in enumerate(text.split()):
                if skip_next:
                    skip_next = False
                    continue
                    
                # Check if this is "een een" pattern
                if (word.lower() == 'een' and 
                    idx + 1 < len(text.split()) and 
                    text.split()[idx + 1].lower() == 'een'):
                    
                    # Check if preceded by dental context
                    has_dental_context = (idx > 0 and 
                                         NormalizationUtils.split_token(text.split()[idx - 1])[1].lower() in dental_context_words)
                    
                    if has_dental_context:
                        # Keep both "een een" for element parsing as "11"
                        new_words.append(word)
                    else:
                        # Remove duplicate - just keep single "een"
                        new_words.append(word)
                        skip_next = True  # Skip the duplicate
                else:
                    new_words.append(word)
            
            text = ' '.join(new_words)
        
        words = text.split()
        result = []
        i = 0
        
        # DEBUG: Uncomment to trace processing
        debug = text == "1-4 mesiopalatinaal"  # Enable debug for specific input
        if debug:
            print(f"DEBUG: Processing text: {text}")
            print(f"DEBUG: Words: {words}")
        
        while i < len(words):
            handled = False
            
            word = words[i]
            # Use tokenization to separate punctuation from core text
            pre, word_clean, post = NormalizationUtils.split_token(word)
            
            if debug:
                print(f"DEBUG: --- Iteration {i}, word: '{word}', word_clean: '{word_clean}' ---")
            
            
            # CASE NORMALIZATION: Handle sentence-initial capitalization
            # Convert sentence-initial articles and common words to lowercase
            normalized_case_word = word_clean
            if i == 0 or (i > 0 and NormalizationUtils.split_token(words[i-1])[1].lower() in ['.', '!', '?']):
                # This is likely sentence-initial, normalize common articles to lowercase
                if word_clean in ['De', 'Het', 'Een']:
                    normalized_case_word = word_clean.lower()
            
            # HIGHEST PRIORITY: Check for element patterns BEFORE fuzzy matching
            # This ensures "2-3" gets parsed as element numbers, not matched to ">1/3 - <2/3"
            # BUT only if it's actually a valid element number AND not followed by a unit
            if not handled and re.match(r'^\d+[-]?\d*$', word_clean):
                # Check if this word looks like an element pattern (e.g., "14", "2-3", "26")
                # But NOT if it's already preceded by "element" word
                if i == 0 or words[i-1].lower() != 'element':
                    # Check if followed by a unit (like "procent", "millimeter")
                    is_followed_by_unit = NormalizationUtils.is_followed_by_unit(
                        words, i, self.generator.direct_mappings
                    )
                    # IMPORTANT: Actually validate it's a real element before treating it as one
                    # AND skip if followed by unit (e.g., "25 procent" should not be "element 25 %")
                    elem = self.parse_element(word_clean) if not is_followed_by_unit else None
                    if elem and elem in self.elements:  # Must be a valid element number
                        # Use tokenization to preserve punctuation
                        element_text = NormalizationUtils.join_token(pre, f"element {elem}", post)
                        result.append(element_text)
                        
                        if word_mappings is not None:
                            word_mappings.append({
                                'original': word,
                                'normalized': element_text,
                                'type': 'element',
                                'category': 'element_parsing'
                            })
                        
                        i += 1
                        handled = True
                        if debug:
                            print(f"DEBUG: Early element detection handled '{word_clean}' -> element {elem}, i now = {i}")
            
            # Also check for two-word element patterns early (e.g., "een vier" → "14", "element 14")
            if not handled and i + 1 < len(words):
                # Check for Dutch number combinations that form elements
                word1_clean = word_clean.lower()
                # Use tokenization for second word
                _, word2_clean, _ = NormalizationUtils.split_token(words[i+1]) if i+1 < len(words) else ("", "", "")
                word2_clean = word2_clean.lower()
                
                # Special check for dental context + element
                dental_context = ['element', 'tand', 'kies', 'molaar', 'premolaar']
                if word1_clean in dental_context:
                    # Try parsing the second word as element
                    word2_with_punct = words[i+1]
                    pre2, word2_core, post2 = NormalizationUtils.split_token(word2_with_punct)
                    elem = self.parse_element(word2_core)
                    if elem:
                        # Handle based on context word, preserving punctuation
                        if word1_clean == 'element':
                            # For "element X", output "element X" with preserved punctuation
                            elem_text = NormalizationUtils.join_token(pre2, f"element {elem}", post2)
                            result.append(elem_text)
                        else:
                            # For other dental words (tand, kies), keep both words
                            result.append(word1_clean)
                            # Just the element number with preserved punctuation
                            elem_text = NormalizationUtils.join_token(pre2, elem, post2)
                            result.append(elem_text)
                        
                        if word_mappings is not None:
                            normalized_full = f"{word1_clean} {elem_text}"
                            word_mappings.append({
                                'original': f"{words[i]} {words[i+1]}",
                                'normalized': normalized_full,
                                'type': 'element',
                                'category': 'element_parsing'
                            })
                        
                        i += 2
                        handled = True
            
            # SECOND PRIORITY: Check for multi-word patterns (fuzzy matching happens here)
            if not handled:
                multi_result = self.find_multi_word_matches(words, i)
                if multi_result:
                    matched_term, words_consumed, match_type, match_category = multi_result
                    result.append(matched_term)
                    
                    if word_mappings is not None:
                        original_phrase = ' '.join(words[i:i+words_consumed])
                        word_mappings.append({
                            'original': original_phrase,
                            'normalized': matched_term,
                            'type': match_type,  # Use actual type from find_multi_word_matches
                            'category': match_category  # Use actual category
                        })
                    
                    i += words_consumed
                    handled = True
                    continue
            
            # SECOND PRIORITY: Check for direct custom mappings (for individual words)
            if not handled:
                word_normalized = _normalize_text(word_clean)
                if word_normalized in self.generator.direct_mappings:
                    mapped = self.generator.direct_mappings[word_normalized]
                    result.append(mapped)
                    
                    if word_mappings is not None:
                        word_mappings.append({
                            'original': word,
                            'normalized': mapped,
                            'type': 'custom',
                            'category': 'direct_mapping'
                        })
                    
                    i += 1
                    handled = True
                    continue
            
            # THIRD PRIORITY: Protected words that should not be normalized
            if not handled:
                # Check if this is a protected word - if so, preserve it unchanged
                if word_clean.lower() in [pw.lower() for pw in self.protected_words]:
                    # Use case-normalized word if different from original
                    final_word = normalized_case_word if normalized_case_word != word_clean else word
                    result.append(final_word)
                    
                    if word_mappings is not None:
                        word_mappings.append({
                            'original': word,
                            'normalized': final_word,  # May have case normalization
                            'type': 'case_norm' if final_word != word else None,
                            'category': None
                        })
                    
                    i += 1
                    handled = True
                    continue
            
            # FOURTH PRIORITY: FALLBACK element parsing (with unit awareness from proven baseline)
            # Most element patterns should be caught by HIGHEST PRIORITY check above,
            # but this handles edge cases and ensures we don't miss any element patterns
            # that slipped through the early detection (e.g., complex unit-aware cases)
            
            if not handled:
                # Use centralized unit checking to avoid treating "30 procent" as element 30
                is_followed_by_unit = NormalizationUtils.is_followed_by_unit(
                    words, i, self.generator.direct_mappings
                )
                
                # Only try element parsing if NOT followed by unit (proven logic from baseline)
                elem = self.parse_element(word_clean) if not is_followed_by_unit else None
                
                if elem:
                    # Use tokenization to preserve punctuation
                    element_text = NormalizationUtils.join_token(pre, f"element {elem}", post)
                    result.append(element_text)
                    
                    if word_mappings is not None:
                        word_mappings.append({
                            'original': word,
                            'normalized': element_text,
                            'type': 'element',
                            'category': 'element_parsing'
                        })
                    
                    i += 1
                    handled = True
                    continue
            
            # SECOND PRIORITY: Check for unit attachment (number + unit combinations)
            if i + 1 < len(words):
                current_word = word_clean
                _, next_word, _ = NormalizationUtils.split_token(words[i + 1])
                
                # Check if current word is number and next is unit
                if NormalizationUtils.should_attach_unit(current_word, next_word):
                    # Convert unit to abbreviation and attach
                    unit_abbrev = NormalizationUtils.normalize_units(next_word)
                    combined_result = NormalizationUtils.attach_unit_to_number(current_word, unit_abbrev)
                    
                    result.append(combined_result)
                    
                    if word_mappings is not None:
                        original_phrase = f"{words[i]} {words[i + 1]}"
                        word_mappings.append({
                            'original': original_phrase,
                            'normalized': combined_result,
                            'type': 'unit',
                            'category': 'unit_attachment'
                        })
                    
                    i += 2  # Skip both words (number + unit)
                    handled = True
                    continue
            
            # THIRD PRIORITY: Check for multi-word patterns 
            # But first check if current word has a good single-word match
            # Safety check: ensure we haven't gone past the end of words array
            if i >= len(words):
                continue
            _, current_word, _ = NormalizationUtils.split_token(words[i])
            has_single_match = False
            
            # Check if current word has direct mapping or dynamic match
            if _normalize_text(current_word) in self.generator.direct_mappings:
                has_single_match = True
            elif self.normalize_dynamic(current_word):
                has_single_match = True
            
            
            # Check if it's already a unit abbreviation that should be attached
            if NormalizationUtils.is_unit(word_clean) and result and NormalizationUtils.should_attach_unit(result[-1], word_clean):
                # Convert unit word to abbreviation before attachment (procent→%, millimeter→mm)
                unit_abbrev = NormalizationUtils.normalize_units(word_clean)
                result[-1] = NormalizationUtils.attach_unit_to_number(result[-1], unit_abbrev)
                if word_mappings is not None:
                    word_mappings.append({
                        'original': word,
                        'normalized': word_clean,
                        'type': 'library',
                        'category': 'units'
                    })
                i += 1
                handled = True
            
            # FALLBACK: Try 2-word element patterns
            # This is additional element parsing for complex cases not caught by the
            # HIGHEST PRIORITY element check at the beginning of the loop.
            # Most simple patterns like "2-3" or "een vier" should already be handled,
            # but this catches more complex patterns like "element 2, 6" or special contexts
            if not handled and i + 1 < len(words):
                
                # Special handling for "element X, Y" pattern
                if not handled and words[i].lower() == "element" and NormalizationUtils.split_token(words[i+1])[1].isdigit():
                    # Check if it's "element 1, 2" pattern
                    if words[i+1].endswith(',') and i + 2 < len(words):
                        three_word = f"{words[i+1]} {words[i+2]}"
                        elem = self.parse_element(three_word)
                        if elem:
                            result.append("element")
                            result.append(elem)
                            i += 3
                            handled = True
                
                # NEW: Check for 3-word patterns: context word + Dutch number combination
                # Example: "tand een vier" -> "tand 14"
                if not handled and i + 2 < len(words):
                    _, word1_clean, _ = NormalizationUtils.split_token(words[i])
                    _, word2_clean, _ = NormalizationUtils.split_token(words[i+1])
                    word1_clean = word1_clean.lower()
                    word2_clean = word2_clean.lower()
                    
                    # Check if it's a context word followed by a Dutch number combination
                    context_words = ['tand', 'kies', 'molaar', 'premolaar', 'element']
                    dutch_numbers = ['een', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht', 'negen']
                    
                    if word1_clean in context_words and word2_clean in dutch_numbers:
                        # Try to parse the number combination
                        two_word_number = f"{words[i+1]} {words[i+2]}"
                        elem = self.parse_element(two_word_number)
                        if elem:
                            # Output: context word + parsed element number
                            result.append(word1_clean)
                            result.append(elem)
                            # Track the normalization
                            if word_mappings is not None:
                                word_mappings.append({
                                    'original': f"{words[i]} {two_word_number}",
                                    'normalized': f"{word1_clean} {elem}",
                                    'type': 'custom',
                                    'category': 'element'
                                })
                            i += 3
                            handled = True
                
                if not handled:
                    # Use centralized unit checking
                    is_second_word_unit = NormalizationUtils.is_followed_by_unit(
                        words, i, self.generator.direct_mappings
                    )
                    
                    # First check if first word alone is an element (but skip if second word is a unit)
                    _, word_core, _ = NormalizationUtils.split_token(words[i])
                    elem1 = self.parse_element(word_core) if not is_second_word_unit else None
                    
                    if elem1:
                        # First word is already an element, don't consume second word
                        if any(c.isdigit() or c == '-' for c in words[i]):
                            result.append(f"element {elem1}")
                        else:
                            result.append(elem1)
                        i += 1
                        handled = True
                    else:
                        # Check if first word should be normalized separately
                        # If first word doesn't contain digits/hyphens and isn't a dental context word,
                        # it should be normalized independently
                        _, word1_clean, _ = NormalizationUtils.split_token(words[i])
                        word1_clean = word1_clean.lower()
                        dental_context = ['element', 'tand', 'kies', 'molaar', 'premolaar']
                        
                        # Check if first word contains digits or is dental context
                        if not any(c.isdigit() or c == '-' for c in words[i]) and word1_clean not in dental_context:
                            # First word should be processed separately if it has a mapping
                            norm = self.normalize_dynamic(word1_clean)
                            if norm:
                                # First word has its own normalization, don't treat as 2-word element
                                normalized_text, category, match_type = norm
                                result.append(normalized_text)
                                i += 1
                                handled = True
                        
                        if not handled:
                            # Use centralized unit checking (don't parse "3,5 millimeter" as element)
                            is_unit_pattern = NormalizationUtils.is_followed_by_unit(
                                words, i, self.generator.direct_mappings
                            )
                            
                            # Try parsing as 2-word element (skip if second word is a unit)
                            two_word = f"{words[i]} {words[i+1]}"
                            elem = self.parse_element(two_word) if not is_unit_pattern else None
                            
                            if elem:
                                # Determine how to output based on context
                                
                                # Don't consume protected words as part of element patterns
                                if word1_clean in [pw.lower() for pw in self.protected_words]:
                                    # This is a protected word, don't treat as 2-word pattern
                                    handled = False
                                elif word1_clean == "element":
                                    # "element XX" -> keep as is
                                    result.append("element")
                                    result.append(elem)
                                    # Track if element number was parsed/normalized
                                    if word_mappings is not None and two_word != f"element {elem}":
                                        word_mappings.append({
                                            'original': two_word,
                                            'normalized': f"element {elem}",
                                            'type': 'element',  # Special type for element parsing
                                            'category': 'element'
                                        })
                                    i += 2
                                    handled = True
                                elif word1_clean in ['tand', 'kies', 'molaar', 'premolaar']:
                                    # "tand XX" -> keep context word
                                    result.append(word1_clean)
                                    result.append(elem)
                                    # Track if element number was parsed/normalized
                                    if word_mappings is not None and two_word != f"{word1_clean} {elem}":
                                        word_mappings.append({
                                            'original': two_word,
                                            'normalized': f"{word1_clean} {elem}",
                                            'type': 'custom',
                                            'category': 'element'
                                        })
                                    i += 2
                                    handled = True
                                else:
                                    # IMPORTANT: Keep the first word UNLESS it's a droppable word like "een", "twee", etc.
                                    # Example: "Mesiale radix X1-6" should become "Mesiale radix element 16"
                                    # But: "een vier" should become just "14" (drop "een")
                                    
                                    # Words that should be dropped when parsing elements
                                    droppable_words = ['een', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht', 'negen']
                                    
                                    # Check if first word should be dropped
                                    if word1_clean in droppable_words:
                                        # Drop the first word (e.g., "een vier" -> "14")
                                        # Use tokenization to preserve punctuation from second word
                                        pre2, _, post2 = NormalizationUtils.split_token(words[i+1])
                                        element_text = NormalizationUtils.join_token(pre2, f"element {elem}", post2)
                                        result.append(element_text)
                                    # Check if the second word looks like an element pattern with special chars (X, R)
                                    elif any(c in 'XxR' for c in words[i+1]):
                                        # Keep first word (e.g., "Mesialeradi X1-6") and add parsed element
                                        result.append(words[i])
                                        # Use tokenization to preserve punctuation from second word
                                        pre2, _, post2 = NormalizationUtils.split_token(words[i+1])
                                        element_text = NormalizationUtils.join_token(pre2, f"element {elem}", post2)
                                        result.append(element_text)
                                        # Track only the element parsing
                                        if word_mappings is not None:
                                            word_mappings.append({
                                                'original': words[i+1],
                                                'normalized': element_text,
                                                'type': 'custom',
                                                'category': 'element'
                                            })
                                    # Check if it looks like a numeric pattern
                                    elif any(c.isdigit() or c == '-' for c in two_word):
                                        # Keep the first word for patterns like "distaal 16"
                                        result.append(words[i])
                                        # Use tokenization to preserve punctuation from second word
                                        pre2, _, post2 = NormalizationUtils.split_token(words[i+1])
                                        element_text = NormalizationUtils.join_token(pre2, f"element {elem}", post2)
                                        result.append(element_text)
                                        # Track that we parsed and normalized this
                                        if word_mappings is not None:
                                            word_mappings.append({
                                                'original': two_word,
                                                'normalized': element_text,
                                                'type': 'custom',
                                                'category': 'element'
                                            })
                                    else:
                                        # Dutch words like "een vier" -> just the number
                                        result.append(elem)
                                        # Track that we parsed and normalized this
                                        if word_mappings is not None:
                                            word_mappings.append({
                                                'original': two_word,
                                                'normalized': elem,
                                                'type': 'custom',
                                                'category': 'element'
                                            })
                                    i += 2
                                    handled = True
            
            # Single word processing
            if not handled:
                word = words[i]
                # Strip ALL punctuation and hyphens (both leading and trailing) for matching
                word_clean = word.strip('.,;!?-')
                
                # Use centralized unit checking (to avoid treating "25" in "25 procent" as element 25)
                # This handles all cases including "3,5 millimeter", "3.5 millimeter", "25 procent" etc.
                is_followed_by_unit = NormalizationUtils.is_followed_by_unit(
                    words, i, self.generator.direct_mappings
                )
                
                # Try element parsing (skip if followed by unit - handles any number format)
                elem = self.parse_element(word_clean) if not is_followed_by_unit else None
                
                if elem:
                    # Single word element - check if it needs "element" prefix
                    if any(c.isdigit() or c == '-' for c in word_clean):
                        normalized = f"element {elem}"
                        result.append(normalized)
                        # Track if this was a conversion
                        if word_mappings is not None and word_clean != normalized:
                            word_mappings.append({
                                'original': word,
                                'normalized': normalized,
                                'type': 'element',  # Special type for element parsing
                                'category': 'element'
                            })
                    else:
                        result.append(elem)
                        # Track if this was a conversion
                        if word_mappings is not None and word_clean != elem:
                            word_mappings.append({
                                'original': word,
                                'normalized': elem,
                                'type': 'element',  # Special type for element parsing
                                'category': 'element'
                            })
                else:
                    # Try normal word normalization (direct mappings already checked at top of loop)
                    norm = self.normalize_dynamic(word_clean)
                    if norm:
                        normalized_text, category, match_type = norm
                        result.append(normalized_text)
                        if word_mappings is not None:
                            word_mappings.append({
                                'original': word,
                                'normalized': normalized_text,
                                'type': match_type,  # Use the actual match type
                                'category': category
                            })
                    else:
                        # HYPHEN HANDLING: Last resort - try splitting hyphenated words
                        # Only if ALL other matching (direct, library, fuzzy, phonetic) failed
                        if '-' in word_clean:
                            hyphen_parts = word_clean.split('-')
                            if len(hyphen_parts) == 2 and all(part.strip() for part in hyphen_parts):
                                # Process both parts and add them separately  
                                for part_idx, part in enumerate(hyphen_parts):
                                    # Use tokenization for part
                                    _, part_clean, _ = NormalizationUtils.split_token(part)
                                    
                                    # Try to normalize the part
                                    part_norm = self.normalize_dynamic(part_clean)
                                    if part_norm:
                                        result.append(part_norm[0])  # Use normalized form
                                    else:
                                        result.append(part_clean)  # Use original form
                            else:
                                result.append(word_clean)  # Fallback for complex hyphens
                        else:
                            result.append(word_clean)  # No hyphen, keep as-is
                        if word_mappings is not None:
                            word_mappings.append({
                                'original': word,
                                'normalized': word_clean,
                                'type': None,  # Word not found in any lexicon
                                'category': None
                            })
                i += 1
                if debug:
                    print(f"DEBUG: End of loop iteration, i now = {i}, len(words) = {len(words)}")
        
        if debug:
            print(f"DEBUG: Loop ended, result = {result}")
        
        # Join result first
        text_result = " ".join(result)
        
        # Post-processing: remove consecutive duplicate canonical terms
        # This fixes cases like "verdikt. verdekking" → "verdikking verdikking" → "verdikking"
        text_result = self._remove_consecutive_duplicates(text_result)
        
        # Post-processing: remove "de" directly before "element"
        # Replace " de element " with " element "
        text_result = text_result.replace(" de element ", " element ")
        # Also handle start of string
        if text_result.startswith("de element "):
            text_result = text_result[3:]  # Remove "de "
        
        # Don't apply sentence breaks here anymore - we use segment boundaries instead
        # text_result = self.apply_sentence_breaks(text_result)
        
        if return_mappings:
            return text_result, word_mappings
        return text_result
    
    def _remove_consecutive_duplicates(self, text: str) -> str:
        """Remove consecutive duplicate words and phrases from normalized text.
        
        This fixes cases where different variants normalize to the same canonical term,
        creating duplicates like "verdikking verdikking" → "verdikking".
        
        Also handles multi-word duplicates like "element 14 element 14" → "element 14".
        
        Args:
            text: The normalized text that may contain consecutive duplicates
            
        Returns:
            Text with consecutive duplicates removed
        """
        if not text:
            return text
            
        words = text.split()
        if len(words) <= 1:
            return text
            
        result = []
        i = 0
        
        while i < len(words):
            current_word = words[i]
            result.append(current_word)
            
            # Check for consecutive single-word duplicates
            j = i + 1
            while j < len(words) and words[j].lower() == current_word.lower():
                j += 1  # Skip duplicate words
            
            # Check for multi-word phrase duplicates (like "element 14")
            if current_word.lower() == "element" and j < len(words) and words[j].isdigit():
                # We have "element [number]", check if the next phrase is "element [same_number]"
                element_number = words[j]
                result.append(element_number)
                k = j + 1
                
                # Look for consecutive "element [number]" patterns
                while k + 1 < len(words) and words[k].lower() == "element" and words[k + 1] == element_number:
                    k += 2  # Skip the duplicate "element number" phrase
                
                i = k
            else:
                i = j
        
        return " ".join(result)
    
    def apply_sentence_breaks(self, text: str) -> str:
        """Apply intelligent sentence breaks based on dental context
        
        Rules:
        1. New sentence after rx_anatomy or element number
        2. EXCEPT when followed by connection words: en, ook, samen met, net als, plus, met
        3. New sentence before rx_findings
        """
        if not text:
            return text
        
        # Connection words that prevent sentence breaks
        connection_words = [
            ' en ', ' ook ', ' samen met ', ' net als ', ' plus ', ' met ',
            ' en element ', ' ook element ', ' samen met element ',
            ' net als element ', ' plus element ', ' met element '
        ]
        
        # Get rx_anatomy terms for detection
        rx_anatomy_terms = [term.lower() for term in self.lex.get('rx_anatomy', [])]
        
        # Get rx_findings terms for detection
        rx_findings_terms = [term.lower() for term in self.lex.get('rx_findings', [])]
        
        # Split into words but keep track of positions
        words = text.split()
        result_parts = []
        current_sentence = []
        
        i = 0
        while i < len(words):
            word = words[i]
            current_sentence.append(word)
            
            # Check if current word is rx_anatomy or element number
            should_break = False
            
            # Check for rx_anatomy term
            if word.lower() in rx_anatomy_terms:
                should_break = True
            
            # Check for element number pattern
            elif word == 'element' and i + 1 < len(words):
                # Element followed by number
                should_break = True
            elif re.match(r'^\d{2}$', word):  # Two digit element number
                should_break = True
            
            # Check if next part starts with rx_findings
            if i + 1 < len(words) and words[i + 1].lower() in rx_findings_terms:
                should_break = True
            
            # Check for connection words that prevent break
            if should_break and i + 1 < len(words):
                # Look ahead for connection words
                next_part = ' '.join(words[i+1:min(i+4, len(words))])
                for conn in connection_words:
                    if next_part.lower().startswith(conn.strip()):
                        should_break = False
                        break
            
            # Apply break if needed
            if should_break and i < len(words) - 1:
                result_parts.append(' '.join(current_sentence))
                current_sentence = []
            
            i += 1
        
        # Add remaining sentence
        if current_sentence:
            result_parts.append(' '.join(current_sentence))
        
        # Join with line breaks, but clean up empty parts
        result = '<br>'.join(part for part in result_parts if part.strip())
        
        # Clean up any double breaks
        result = re.sub(r'(<br>\s*)+', '<br>', result)
        
        return result
    
    def teach(self, variant: str, canonical: str, category: str) -> bool:
        """Teach the system a new variant - werkt met alle categorieën"""
        # Check of het een multi-word variant is
        if len(variant.split()) > 1:
            # Multi-word mapping
            success = self.generator.add_multi_word_mapping(variant, canonical)
        else:
            # Single word mapping
            success = self.generator.add_mapping(variant, canonical)
        
        if success:
            # Clear cache when learning
            self._multi_word_cache.clear()
            
            # Update de matcher voor deze categorie als die bestaat
            if category in self.matchers:
                # Clear cache since lexicon was updated
                self.matchers[category]._match_cached.cache_clear()
                # Regenerate variants for the new canonical term
                self.matchers[category]._generate_variants_for_term(canonical)
            
        return success
    
    def get_failed_matches(self) -> List[Dict]:
        """Get recent failed matches"""
        return self.generator.failed_matches
    
    def get_canonical_terms(self, category: str) -> List[str]:
        """Get canonical terms for a category - DYNAMISCH"""
        # Direct uit lexicon
        return self.lex.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories"""
        categories = []
        skip_keys = {'elements_permanent', 'elements_primary', 'element_variants'}
        
        for key in self.lex.keys():
            if key in skip_keys or key.endswith('_abbr'):
                continue
            if isinstance(self.lex[key], list):
                categories.append(key)
                
        return sorted(categories)
    
    def analyze(self, text: str) -> Dict:
        """Analyze text and return all found components"""
        out = {
            "input": text,
            "normalized": self.normalize(text)
        }
        
        # Check if it's a learned phrase
        if _normalize_text(text) in self.generator.direct_mappings:
            out["learned"] = True
            out["learned_type"] = "single_word"
        elif self.check_multi_word_mapping(text):
            out["learned"] = True
            out["learned_type"] = "multi_word"
        
        # Element parsing
        elem = self.parse_element(text)
        if elem:
            out["element"] = elem
        
        # Try all dynamic matchers en track welke matchen
        matches = []
        for category, matcher in self.matchers.items():
            result = matcher.match(text)
            if result:
                matches.append({
                    "category": category,
                    "match": result
                })
        
        if matches:
            out["matches"] = matches
        
        return out
    
    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        return {
            "single_word_mappings": len(self.generator.direct_mappings),
            "multi_word_mappings": len(self.generator.multi_word_mappings),
            "failed_matches": len(self.generator.failed_matches),
            "dynamic_categories": len(self.matchers),
            "total_canonical_terms": len(self.get_all_canonical_terms()),
            "config": {
                "fuzzy_threshold": self.config.get('matching', {}).get('fuzzy_threshold', 0.8),
                "phonetic_enabled": self.config.get('matching', {}).get('phonetic_enabled', True),
                "protect_words_count": len(self.protected_words),
                "dental_context_count": len(self.config.get('dental_context_words', []))
            },
            "last_updated": self.generator.custom_patterns_file
        }


# Make it backwards compatible
DentalNormalizer = DentalNormalizerLearnable


# Test function
if __name__ == "__main__":
    print("Testing Config-Based Learnable Dental Normalizer")
    print("=" * 60)
    
    # Initialize
    dn = DentalNormalizerLearnable("compact_lexicon.json", "config.json")
    
    # Show config
    print(f"\nCurrent config:")
    config = dn.get_config()
    print(f"  Fuzzy threshold: {config['matching']['fuzzy_threshold']}")
    print(f"  Phonetic enabled: {config['matching']['phonetic_enabled']}")
    print(f"  Skip words: {len(config.get('skip_words', []))}")
    
    # Show loaded categories
    print(f"\nLoaded categories: {dn.get_all_categories()}")
    
    # Test cases
    test_cases = [
        ("radiolicentie", "radiolucentie", "rx_findings"),
        ("radio licentie", "radiolucentie", "rx_findings"),
        ("dus stout", "distaal", "surfaces"),
        ("dusstout", "distaal", "surfaces"),
    ]
    
    print("\nTeaching new mappings...")
    for variant, canonical, category in test_cases:
        success = dn.teach(variant, canonical, category)
        print(f"  {variant} -> {canonical}: {'✓' if success else '✗'}")
    
    # Show statistics
    stats = dn.get_statistics()
    print(f"\nStatistics:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
