#!/usr/bin/env python3
"""
Phonetic matcher for Dutch dental terms using sound-based matching
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any, Iterable
from difflib import SequenceMatcher
import unicodedata


class _SimpleTokenizer:
    """Fallback tokenizer when none provided - matches DefaultTokenizer implementation"""
    _SEP_RE = re.compile(r"(\s+|[.,;:/!?()\[\]{}\-])")
    
    def tokenize(self, text: str) -> List[str]:
        parts: List[str] = []
        idx = 0
        for m in self._SEP_RE.finditer(text):
            if m.start() > idx:
                parts.append(text[idx:m.start()])
            parts.append(m.group(0))
            idx = m.end()
        if idx < len(text):
            parts.append(text[idx:])
        return parts
    
    def detokenize(self, tokens: Iterable[str]) -> str:
        return ''.join(tokens)


class DutchPhoneticMatcher:

    # Morphological suffix families to avoid cross-family boosts (e.g., -um vs -air)
    MORPH_FAMILIES = {
        "latin_noun": ("um", "us", "a"),
        "adjective": ("air", "aal", "eel", "ief", "oor", "air", "air"),  # dutch adj endings (approx)
        "verb_like": ("eer", "eren", "eert", "eerde", "ering"),
    }
    def _suffix_family(self, w: str) -> str:
        wl = w.lower()
        for fam, endings in self.MORPH_FAMILIES.items():
            for suf in endings:
                if wl.endswith(suf) and len(wl) >= len(suf)+3:
                    return fam
        return "other"
    def _families_compatible(self, a: str, b: str) -> bool:
        fa, fb = self._suffix_family(a), self._suffix_family(b)
        # Allow same family or 'other'. Block latin_noun vs adjective/verb_like swaps
        blocked = {("latin_noun","adjective"),("latin_noun","verb_like"),
                   ("adjective","latin_noun"),("verb_like","latin_noun")}
        return (fa, fb) not in blocked
    """Phonetic matching for Dutch language with dental context"""
    
    # Generic dental prefixes that should not dominate similarity scoring
    GENERIC_PREFIXES = (
        "inter", "intra", "infra", "supra", "sub", "peri", "para",
        "hyper", "hypo", "endo", "ecto", "meso", "meta", "ortho",
        "mesio", "disto", "bucco", "linguo", "palato", "labio"
    )
    
    def _detect_generic_prefix(self, word: str) -> tuple[str, str]:
        """
        Detect if word starts with a generic dental prefix.
        Returns (prefix, core_word) or ('', word) if no prefix found.
        """
        word_lower = word.lower()
        for prefix in self.GENERIC_PREFIXES:
            if word_lower.startswith(prefix) and len(word) > len(prefix):
                # Ensure there's a meaningful core word (at least 3 chars)
                core_word = word[len(prefix):]
                if len(core_word) >= 3:
                    return prefix, core_word
        return '', word
    
    def _prefix_aware_similarity(self, word1: str, word2: str) -> float:
        """
        Calculate similarity with prefix awareness.
        If both words share the same generic prefix, focus scoring on core words.
        """
        prefix1, core1 = self._detect_generic_prefix(word1)
        prefix2, core2 = self._detect_generic_prefix(word2)
        
        # If both have the same generic prefix, calculate similarity primarily on core words
        if prefix1 and prefix1 == prefix2:
            # Calculate core similarity
            core_sim = SequenceMatcher(None, core1.lower(), core2.lower()).ratio()
            
            # Give small bonus for shared prefix but don't let it dominate
            prefix_bonus = 0.1
            
            # Weight: 80% core similarity + 10% prefix bonus + 10% full word fallback
            full_sim = SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
            return (core_sim * 0.8) + (prefix_bonus * 0.1) + (full_sim * 0.1)
        
        # No shared generic prefix - use normal similarity
        return SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
    
    def __init__(self, config_data: Dict[str, Any] = None, 
                 phonetic_cache: Dict[str, List[str]] = None,
                 soundex_cache: Dict[str, str] = None,
                 phonetic_index: Dict[str, List[str]] = None,
                 tokenizer=None):
        self.config = config_data or {}
        
        matching_config = self.config.get('matching', {})
        self.fuzzy_threshold = matching_config.get('fuzzy_threshold', 0.84)
        self.phonetic_enabled = matching_config.get('phonetic_enabled', True)
        self.max_edit_distance = matching_config.get('max_edit_distance', 2)
        self.boost_top_epsilon = matching_config.get('boost_top_epsilon', 0.0)
        
        # Use provided cache or create new
        self._phonetic_cache = phonetic_cache or {}
        self._soundex_cache = soundex_cache or {}
        self._phonetic_index = phonetic_index or {}
        
        # Initialize tokenizer (fallback to _SimpleTokenizer if none provided)
        self.tokenizer = tokenizer if tokenizer is not None else _SimpleTokenizer()
        
        # Build phonetic conversion table
        self._build_phonetic_table()
    
    def _build_phonetic_table(self):
        """Build comprehensive phonetic conversion table"""
        self.phonetic_table = {}
        
        # Get phonetic patterns from config (with fallback to defaults)
        phonetic_patterns = self.config.get('phonetic_patterns', {})
        
        if not phonetic_patterns:
            # Use basic Dutch phonetic patterns as fallback
            phonetic_patterns = {
                'dutch_sounds': {
                    'ei': ['ij', 'ai'],
                    'ij': ['ei', 'y'],
                    'ou': ['au'],
                    'au': ['ou'],
                    'c': ['k', 's'],
                    'k': ['c'],
                    'ch': ['g'],
                    'g': ['ch']
                },
                'common_errors': {
                    'element': ['eliment', 'elemnt'],
                    'occlusaal': ['occlusaal', 'okklusaal'],
                    'distaal': ['distal', 'distale']
                }
            }
        
        # Add Dutch sounds
        dutch_sounds = phonetic_patterns.get('dutch_sounds', {})
        for sound, variants in dutch_sounds.items():
            self.phonetic_table[sound] = variants
            # Add reverse mappings
            for variant in variants:
                if variant not in self.phonetic_table:
                    self.phonetic_table[variant] = [sound]
                else:
                    self.phonetic_table[variant].append(sound)
        
        # Add common errors
        common_errors = phonetic_patterns.get('common_errors', {})
        for error, corrections in common_errors.items():
            if error in self.phonetic_table:
                self.phonetic_table[error].extend(corrections)
            else:
                self.phonetic_table[error] = corrections
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        return text.strip().lower()
    
    def to_phonetic(self, word: str) -> List[str]:
        """Convert word to phonetic representations (uses cache if available)"""
        word = self.normalize_text(word)
        
        # Check cache first if available
        if word in self._phonetic_cache:
            return self._phonetic_cache[word]
        
        representations = [word]
        
        if not self.phonetic_enabled:
            return representations
        
        # Apply phonetic conversions
        for i in range(min(3, len(word))):  # Max 3 iterations
            new_reps = []
            for rep in representations:
                # Try each phonetic pattern
                for pattern, replacements in self.phonetic_table.items():
                    if pattern in rep:
                        for replacement in replacements:
                            new_rep = rep.replace(pattern, replacement, 1)
                            if new_rep not in representations and new_rep not in new_reps:
                                new_reps.append(new_rep)
            
            representations.extend(new_reps[:5])  # Limit growth
            if not new_reps:
                break
        
        # Also generate soundex-like representation
        soundex = self._dutch_soundex(word)
        if soundex not in representations:
            representations.append(soundex)
        
        return representations[:10]  # Return max 10 representations
    
    def _dutch_soundex(self, word: str) -> str:
        """Dutch-adapted soundex algorithm (uses cache if available)"""
        if not word:
            return ""
        
        word = self.normalize_text(word)
        
        # Check cache first if available
        if word in self._soundex_cache:
            return self._soundex_cache[word]
        
        # Dutch soundex mappings
        mappings = {
            'b': '1', 'p': '1', 'f': '1', 'v': '1', 'w': '1',
            'c': '2', 'g': '2', 'j': '2', 'k': '2', 'q': '2', 's': '2', 'x': '2', 'z': '2',
            'd': '3', 't': '3',
            'l': '4',
            'm': '5', 'n': '5',
            'r': '6'
        }
        
        # Keep first letter
        soundex = word[0]
        
        # Convert rest
        for char in word[1:]:
            if char in mappings:
                code = mappings[char]
                if not soundex or soundex[-1] != code:
                    soundex += code
        
        # Pad with zeros
        soundex = soundex[:4].ljust(4, '0')
        
        return soundex
    
    def _fuzzy_match_raw(self, word1: str, word2: str) -> float:
        """Calculate fuzzy match score between two words (uncapped for comparison)"""
        word1 = self.normalize_text(word1)
        word2 = self.normalize_text(word2)
        
        # Direct match
        if word1 == word2:
            return 1.0
        
        # HYPHEN NORMALIZATION: Check if removing hyphens creates a match
        # This handles cases like "veriapicaal" matching "peri-apicaal"
        word1_no_hyphen = word1.replace('-', '')
        word2_no_hyphen = word2.replace('-', '')
        
        if word1_no_hyphen == word2_no_hyphen:
            return 1.0  # Perfect match when ignoring hyphens
        
        # Length difference penalty (compare without hyphens for fairer comparison)
        len_diff = abs(len(word1_no_hyphen) - len(word2_no_hyphen))
        if len_diff > self.max_edit_distance:
            return 0.0
        
        # Calculate similarity - use prefix-aware scoring and dehyphenated versions
        # This ensures "peri-apicaal" and "periapicaal" are considered very similar
        # and that generic prefixes don't dominate similarity scoring
        similarity_with_hyphen = self._prefix_aware_similarity(word1, word2)
        similarity_without_hyphen = self._prefix_aware_similarity(word1_no_hyphen, word2_no_hyphen)
        
        # Use the better score - this handles both hyphenated and non-hyphenated comparisons
        similarity = max(similarity_with_hyphen, similarity_without_hyphen)
        
        # Bonus for matching start/end
        if word1.startswith(word2[:3]) or word2.startswith(word1[:3]):
            similarity += 0.1
        if word1.endswith(word2[-3:]) or word2.endswith(word1[-3:]):
            similarity += 0.05
        
        # ENHANCED: Check for high-value phonetic patterns
        # Give bonus for Dutch double-to-single vowel reduction (aa→a, ee→e, oo→o)
        if len(word1) > len(word2):
            # Check if word1 contains double vowels that become single in word2
            for double, single in [('aa', 'a'), ('ee', 'e'), ('oo', 'o'), ('uu', 'u')]:
                if double in word1:
                    # Create a version of word1 with double vowel replaced by single
                    word1_reduced = word1.replace(double, single, 1)
                    if word1_reduced == word2:
                        # Perfect match after vowel reduction - high bonus
                        similarity += 0.15
                        break
                    elif abs(len(word1_reduced) - len(word2)) <= 1:
                        # Close match after vowel reduction
                        reduction_sim = SequenceMatcher(None, word1_reduced, word2).ratio()
                        if reduction_sim > 0.9:
                            similarity += 0.08
                            break
        
        # Return uncapped score for comparison
        return similarity
    
    def fuzzy_match(self, word1: str, word2: str) -> float:
        """Calculate fuzzy match score between two words (capped at 1.0)"""
        return min(self._fuzzy_match_raw(word1, word2), 1.0)
    
    def match(self, input_text: str, candidates: List[str]) -> Optional[Tuple[str, float]]:
        """Find best match from candidates using phonetic and fuzzy matching with top-1-only boost"""
        input_norm = self.normalize_text(input_text)
        
        # Skip phonetic matching for numbers and percentages
        if input_text.isdigit() or input_text.replace('%', '').replace(',', '').replace('.', '').isdigit():
            return None
        
        # IMPORTANT: If input is multi-word, reject it for single-word matching
        # Multi-word inputs should use match_multi_word() with proper thresholds
        input_words = input_norm.split()
        if len(input_words) > 1:
            # Multi-word inputs are not handled by this method to prevent
            # incorrect matches like "mesiale vlak" -> "mesiale radix"
            return None
        
        # Generate phonetic representations
        input_phonetics = self.to_phonetic(input_text)
        
        # PASS 1: Calculate base scores and gather candidate data
        cand_rows = []
        for candidate in candidates:
            candidate_norm = self.normalize_text(candidate)
            
            # Direct match
            if input_norm == candidate_norm:
                return candidate, 1.0
            
            # Calculate base fuzzy score (without any phonetic boost)
            base_score = self._fuzzy_match_raw(input_text, candidate)
            
            # Check if phonetically equal
            candidate_phonetics = self.to_phonetic(candidate)
            phonetic_match = False
            if self.phonetic_enabled:
                for inp_phon in input_phonetics:
                    for cand_phon in candidate_phonetics:
                        if inp_phon == cand_phon:
                            phonetic_match = True
                            break
                    if phonetic_match:
                        break
            
            # Calculate Soundex score for blending
            soundex_score = 0.0
            if self.phonetic_enabled and phonetic_match:
                soundex_score = self.fuzzy_match(
                    self._dutch_soundex(input_text),
                    self._dutch_soundex(candidate)
                )
            
            cand_rows.append({
                "candidate": candidate,
                "base": base_score,
                "phonetic_match": phonetic_match,
                "soundex": soundex_score
            })
        
        if not cand_rows:
            return None
        
        # Find best base score
        best_base = max(r["base"] for r in cand_rows)
        
        # PASS 2: Apply phonetic boost only to top candidates
        for r in cand_rows:
            # Start with capped base score
            r["final"] = min(r["base"], 1.0)
            
            # Check if this candidate is within epsilon of the best base score
            is_top = (best_base - r["base"]) <= self.boost_top_epsilon
            
            # Only apply phonetic boost to top candidates
            # Reject boosts that cross morphological families
            if is_top and r["phonetic_match"] and not self._families_compatible(input_text, r["candidate"]):
                r["phonetic_match"] = False  # block boost

            if is_top and r["phonetic_match"] and self.phonetic_enabled:
                phonetic_boost_floor = 0.70
                min_len_for_boost = 5
                
                # Only boost if base score is already decent and tokens are long enough
                if r["final"] >= phonetic_boost_floor and len(input_text) >= min_len_for_boost and len(r["candidate"]) >= min_len_for_boost:
                    # Gentle boost as tie-breaker, not catapult
                    r["final"] = max(r["final"], 0.95)
                    
                    # Blend with Soundex score
                    r["final"] = (r["final"] + r["soundex"] * 0.3) / 1.3
            # No Soundex blend for non-top candidates
        
        # Find best final score
        best_row = max(cand_rows, key=lambda x: x["final"])
        
        if best_row["final"] >= self.fuzzy_threshold:
            return best_row["candidate"], best_row["final"]
        
        return None
    
    def match_multi_word(self, input_text: str, multi_word_terms: Dict[str, Dict], 
                         word_to_multi: Dict[str, List[str]]) -> Optional[Tuple[str, float]]:
        """
        Match input against multi-word canonical terms using phonetic matching
        """
        input_words = input_text.lower().split()
        best_match = None
        best_score = 0.0
        
        # Strategy 1: Try to match full input against full canonical terms
        if len(input_words) <= 5:  # Only for reasonable lengths
            input_normalized = ' '.join(input_words)
            # Check exact match first
            if input_normalized in multi_word_terms:
                return input_normalized, 1.0
            
            # Try phonetic match on full phrase
            for term in multi_word_terms:
                if len(term.split()) == len(input_words):  # Same word count
                    score = self._multi_word_phonetic_score(input_normalized, term)
                    if score > best_score:
                        best_score = score
                        best_match = term
        
        # Strategy 2: Find multi-word terms containing phonetic matches of input words
        candidates = set()
        for word in input_words:
            # Get phonetic representations
            word_phonetics = self.to_phonetic(word)
            
            # Find canonical words that match phonetically using pre-built index
            for phonetic in word_phonetics:
                if phonetic in self._phonetic_index:
                    matched_words = self._phonetic_index[phonetic]
                    # For each matched word, find multi-word terms containing it
                    for matched_word in matched_words:
                        if matched_word in word_to_multi:
                            candidates.update(word_to_multi[matched_word])
        
        # Score each candidate
        for candidate in candidates:
            candidate_info = multi_word_terms[candidate]
            if abs(len(input_words) - candidate_info['word_count']) <= 1:  # Similar length
                score = self._multi_word_phonetic_score(' '.join(input_words), candidate)
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        if best_score >= self.fuzzy_threshold:
            return best_match, best_score
        
        return None

    def _multi_word_phonetic_score(self, input_phrase: str, canonical_phrase: str) -> float:
        """Calculate phonetic similarity score between two multi-word phrases with strict thresholds"""
        input_words = input_phrase.split()
        canonical_words = canonical_phrase.split()
        
        # Get configurable thresholds
        multi_word_config = self.config.get('matching', {}).get('multi_word', {})
        word_veto_threshold = multi_word_config.get('word_veto_threshold', 0.6)
        two_word_min = multi_word_config.get('two_word_min', 0.7)
        overall_min = multi_word_config.get('overall_min', 0.75)
        require_all_words = multi_word_config.get('require_all_words', True)
        
        # If different word counts, apply penalty or reject
        if len(input_words) != len(canonical_words):
            length_penalty = 1 - (abs(len(input_words) - len(canonical_words)) * 0.2)
            if length_penalty <= 0:
                return 0.0
        else:
            length_penalty = 1.0
        
        # Calculate word-by-word phonetic similarity with strict checking
        total_score = 0.0
        word_scores = []
        
        for i, input_word in enumerate(input_words):
            if i < len(canonical_words):
                # Direct fuzzy match
                word_score = self.fuzzy_match(input_word, canonical_words[i])
                
                # Bonus if phonetically similar
                input_phonetics = set(self.to_phonetic(input_word))
                canonical_phonetics = set(self.to_phonetic(canonical_words[i]))
                
                if input_phonetics & canonical_phonetics:  # Intersection
                    word_score = min(1.0, word_score + 0.2)
                
                # VETO CHECK: If any word is too different, reject entire match
                if word_score < word_veto_threshold:
                    return 0.0  # Immediate rejection
                
                word_scores.append(word_score)
                total_score += word_score
            else:
                # Extra word in input = automatic fail for exact matching
                if require_all_words:
                    return 0.0
                else:
                    total_score += 0.3  # Small penalty (old behavior)
        
        # Additional check: For 2-word terms, both words must be good matches
        if len(word_scores) == 2:
            # For 2-word terms, require higher minimum score
            if min(word_scores) < two_word_min:
                return 0.0
        
        # Average score with length penalty
        avg_score = total_score / max(len(input_words), len(canonical_words))
        
        # Final score must also pass overall threshold
        final_score = avg_score * length_penalty
        
        # For multi-word, we want higher confidence
        if final_score < overall_min:
            return 0.0
        
        return final_score
    
    def fast_phonetic_lookup(self, word: str, phonetic_index: Dict[str, List[str]]) -> List[str]:
        """Ultra-fast phonetic lookup using pre-built index"""
        word_phonetics = self.to_phonetic(word)
        candidates = set()
        
        for phonetic in word_phonetics:
            if phonetic in phonetic_index:
                candidates.update(phonetic_index[phonetic])
        
        return list(candidates)
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    def _build_default_phonetic_table(self):
        """Build default phonetic table when config is missing phonetic_patterns"""
        print("🔧 Building default Dutch phonetic table")
        
        # Basic Dutch phonetic patterns for fallback
        default_patterns = {
            'ij': ['ei', 'y'],
            'ei': ['ij', 'ai'], 
            'ou': ['au'],
            'ch': ['g', 'x'],
            'sch': ['s'],
            'dt': ['t']
        }
        
        for sound, variants in default_patterns.items():
            self.phonetic_table[sound] = variants
            
        print(f"✅ Default phonetic table built: {len(self.phonetic_table)} patterns")
    
    def normalize(self, text: str, canonicals: List[str]) -> str:
        """
        Normalize text by replacing misspelled tokens with canonical terms in-place.
        This is the pipeline-compatible interface that uses fuzzy/phonetic matching.
        
        Args:
            text: Input text to normalize
            canonicals: List of canonical terms to match against
            
        Returns:
            Text with tokens replaced in-place (no appending)
        """
        if not text or not canonicals:
            return text
            
        # Tokenize input text
        tokens = self.tokenizer.tokenize(text)
        modified_tokens = []
        
        for token in tokens:
            # Skip punctuation and separators (whitespace, punctuation)
            if not token.strip() or not token.replace(' ', '').isalpha():
                modified_tokens.append(token)
                continue
                
            # Clean token for matching (lowercase, strip)
            clean_token = token.strip().lower()
            if not clean_token or len(clean_token) <= 2:
                modified_tokens.append(token)
                continue
                
            # Skip fuzzy matching for very short tokens (≤2 chars) to prevent unwanted transformations
            if len(clean_token) <= 2:
                modified_tokens.append(token)
                continue
                
            # Try to find a match using existing match method
            match_result = self.match(clean_token, canonicals)
            
            if match_result and match_result[1] >= self.fuzzy_threshold:
                # Replace with the matched canonical term, preserving case if original was capitalized
                matched_canonical = match_result[0]
                if token[0].isupper() and matched_canonical:
                    matched_canonical = matched_canonical[0].upper() + matched_canonical[1:]
                modified_tokens.append(matched_canonical)
            else:
                # No match found, keep original token
                modified_tokens.append(token)
        
        # Detokenize back to string
        return self.tokenizer.detokenize(modified_tokens)

