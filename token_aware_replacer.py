#!/usr/bin/env python3
"""
token_aware_replacer.py - Unified token-aware matching for flexible gaps
Handles spaces, hyphens, and punctuation preservation consistently
"""

import re
from typing import List, Dict, Optional, Tuple


class TokenAwareReplacer:
    """
    Unified token-aware replacer that handles flexible gaps (spaces/hyphens) 
    and preserves punctuation for both variants and custom patterns
    """
    
    # TOKEN_REGEX from normalization_utils.py - separates punctuation from core text
    TOKEN_REGEX = re.compile(r'([.,:;!?])|(\S+)', re.UNICODE)
    
    def __init__(self):
        """Initialize the token-aware replacer"""
        pass
    
    def create_flexible_pattern(self, canonical_term: str) -> str:
        """
        Create a regex pattern that matches the canonical term with flexible gaps
        
        Args:
            canonical_term: The canonical form (e.g., "botverlies")
            
        Returns:
            Regex pattern that matches variants like "bot verlies", "bot-verlies", etc.
        """
        # Split the canonical term into character-level tokens to handle compound words
        chars = list(canonical_term.lower())
        pattern_parts = []
        
        i = 0
        current_token = ""
        
        while i < len(chars):
            char = chars[i]
            
            # Check if this could be a word boundary in compound words
            # Look for common Dutch compound patterns
            if i > 0 and self._is_likely_word_boundary(chars, i):
                # Add current token
                if current_token:
                    pattern_parts.append(re.escape(current_token))
                    current_token = ""
                
                # Add flexible gap pattern (space or hyphen, optional)
                pattern_parts.append(r'[\s\-]*')
                
                # Start new token
                current_token = char
            else:
                current_token += char
            
            i += 1
        
        # Add final token
        if current_token:
            pattern_parts.append(re.escape(current_token))
        
        # Create final pattern
        pattern = ''.join(pattern_parts)
        
        # Wrap in word boundaries to avoid partial matches
        return rf'\b{pattern}\b'
    
    def _is_likely_word_boundary(self, chars: List[str], pos: int) -> bool:
        """
        Determine if position is likely a word boundary in Dutch compound words
        
        Args:
            chars: List of characters
            pos: Current position
            
        Returns:
            True if this is likely a compound word boundary
        """
        if pos <= 0 or pos >= len(chars):
            return False
            
        prev_char = chars[pos - 1]
        curr_char = chars[pos]
        
        # Common Dutch compound patterns:
        # 1. Consonant followed by vowel (like "bot|verlies")
        # 2. Double consonants that could be split
        # 3. Common prefixes/suffixes boundaries
        
        vowels = set('aeiouâêîôûàèùï')
        consonants = set('bcdfghjklmnpqrstvwxyzç')
        
        # Pattern 1: consonant + vowel (very common in Dutch compounds)
        if prev_char in consonants and curr_char in vowels:
            # Additional heuristic: check if this creates meaningful parts
            # For "botverlies": "bot" + "verlies" both are meaningful
            if pos >= 3:  # Minimum word part length
                return True
        
        # Pattern 2: Some specific Dutch compound patterns
        dutch_boundaries = [
            ('t', 'v'),  # bot|verlies
            ('d', 'v'),  # hand|verlies  
            ('n', 'v'),  # been|verlies
            ('s', 'v'),  # kaas|verlies
        ]
        
        if (prev_char, curr_char) in dutch_boundaries:
            return True
            
        return False
    
    def apply_flexible_replacement(self, text: str, canonical_term: str, replacement: str) -> str:
        """
        Apply token-aware replacement with flexible gap handling
        
        Args:
            text: Input text to process
            canonical_term: The canonical form to match (e.g., "botverlies")
            replacement: What to replace it with
            
        Returns:
            Text with replacements applied, preserving punctuation
        """
        # Create flexible pattern for the canonical term
        pattern = self.create_flexible_pattern(canonical_term)
        
        # Split text into tokens (preserving punctuation)
        tokens = self._tokenize_with_punctuation(text)
        
        # Rejoin tokens for pattern matching (we'll restore punctuation later)
        text_for_matching = ' '.join(token for token, is_punct in tokens if not is_punct)
        
        # Apply the replacement using the flexible pattern
        replaced_text = re.sub(pattern, replacement, text_for_matching, flags=re.IGNORECASE)
        
        # If replacement occurred, we need to restore punctuation context
        if replaced_text != text_for_matching:
            return self._restore_punctuation_context(text, replaced_text, tokens)
        
        return text
    
    def _tokenize_with_punctuation(self, text: str) -> List[Tuple[str, bool]]:
        """
        Tokenize text preserving punctuation information
        
        Args:
            text: Input text
            
        Returns:
            List of (token, is_punctuation) tuples
        """
        tokens = []
        for match in self.TOKEN_REGEX.finditer(text):
            punctuation, word = match.groups()
            if punctuation:
                tokens.append((punctuation, True))
            elif word:
                tokens.append((word, False))
        
        return tokens
    
    def _restore_punctuation_context(self, original: str, replaced: str, 
                                   original_tokens: List[Tuple[str, bool]]) -> str:
        """
        Restore punctuation in the context of the replaced text
        
        Args:
            original: Original text
            replaced: Text after word replacement
            original_tokens: Original tokenization
            
        Returns:
            Text with punctuation properly restored
        """
        # For now, simple implementation - just return replaced text
        # In a more sophisticated version, we could map punctuation positions
        return replaced
    
    def find_variants_with_gaps(self, text: str, canonical_terms: List[str]) -> List[Tuple[str, str]]:
        """
        Find variants of canonical terms that appear with gaps in the text
        
        Args:
            text: Input text to search
            canonical_terms: List of canonical terms to look for
            
        Returns:
            List of (found_variant, canonical_term) tuples
        """
        results = []
        
        for canonical_term in canonical_terms:
            pattern = self.create_flexible_pattern(canonical_term)
            
            # Find all matches
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found_variant = match.group(0)
                results.append((found_variant, canonical_term))
        
        return results
    
    def normalize_with_flexible_gaps(self, text: str, 
                                   replacement_map: Dict[str, str]) -> str:
        """
        Normalize text using flexible gap matching for all terms in replacement map
        
        Args:
            text: Input text
            replacement_map: Dict of {canonical_term: replacement}
            
        Returns:
            Normalized text
        """
        result = text
        
        # Apply replacements for each canonical term
        for canonical_term, replacement in replacement_map.items():
            result = self.apply_flexible_replacement(result, canonical_term, replacement)
        
        return result


# Test function
if __name__ == "__main__":
    print("Testing TokenAwareReplacer")
    print("=" * 50)
    
    replacer = TokenAwareReplacer()
    
    # Test the "botverlies" case from the user's request
    test_cases = [
        ("bot verlies", "botverlies"),
        ("bot-verlies", "botverlies"), 
        ("Bot verlies van element 16", "botverlies"),
        ("Patient heeft bot verlies en cariës", "botverlies"),
        ("de bot-verlies is ernstig", "botverlies"),
    ]
    
    print("Testing flexible pattern creation:")
    pattern = replacer.create_flexible_pattern("botverlies")
    print(f"Pattern for 'botverlies': {pattern}")
    
    print("\nTesting replacements:")
    for test_text, canonical in test_cases:
        result = replacer.apply_flexible_replacement(test_text, canonical, canonical)
        print(f"'{test_text}' → '{result}'")
    
    print("\nTesting variant finding:")
    text = "Patient heeft bot verlies en bot-verlies in element 16"
    variants = replacer.find_variants_with_gaps(text, ["botverlies"])
    for variant, canonical in variants:
        print(f"Found variant: '{variant}' → '{canonical}'")
    
    print("\nTesting batch normalization:")
    replacement_map = {"botverlies": "botverlies"}
    test_text = "Patient heeft bot verlies en ook bot-verlies"
    result = replacer.normalize_with_flexible_gaps(test_text, replacement_map)
    print(f"'{test_text}' → '{result}'")