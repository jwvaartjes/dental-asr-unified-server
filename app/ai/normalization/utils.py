#!/usr/bin/env python3
"""
Centralized normalization utilities to eliminate code duplication
This module contains all shared logic used by multiple normalizers
"""

import json
import re
from typing import List, Optional, Dict, Tuple

# Tokenization regex for separating punctuation from core text
_TOKEN_RE = re.compile(
    r"""^
        (?P<pre>[\(\[\{\'\"\u201c\u201d]*)          # Optional opening punctuation
        (?P<core>[^\s\(\)\[\]\{\}\'\"\u201c\u201d:;,.!?\u2014-]+(?:[./-][^\s:;,.!?\u2014-]+)*)?  # Core text
        (?P<mid>[\)\]\}\'\"\u201c\u201d]*)          # Optional closing punctuation
        (?P<post>[:;,.!?\u2014-]*)                  # Trailing punctuation (including ; and :)
    $""",
    re.VERBOSE
)


class NormalizationUtils:
    """Centralized utilities for normalization operations"""
    
    # Single source of truth for units
    UNIT_WORDS = ['procent', 'percent', 'millimeter', 'milimeter', 'centimeter', 
                  'mm', 'cm', 'm', 'ml', 'mg', 'kg', '%']
    
    UNIT_SYMBOLS = ['%', 'mm', 'cm', 'm', 'ml', 'mg', 'kg']
    
    # Temporal words that indicate time context
    TEMPORAL_WORDS = ['jaar', 'jaren', 'maand', 'maanden', 'week', 'weken', 
                      'dag', 'dagen', 'uur', 'uren', 'minuut', 'minuten',
                      'seconde', 'seconden', 'geleden', 'sinds', 'voor']
    
    @classmethod
    def load_units_from_lexicon(cls, lexicon_data: Dict) -> Dict:
        """Load unit definitions from lexicon data (from DataRegistry)"""
        try:
            units = {
                'canonical': lexicon_data.get('units', []),
                'mappings': {}
            }
            
            # Build mappings from abbreviations
            if 'units_abbr' in lexicon_data:
                for abbr, variants in lexicon_data['units_abbr'].items():
                    for variant in variants:
                        units['mappings'][variant.lower()] = abbr
                            
            return units
        except Exception as e:
            print(f"Warning: Could not load units from lexicon: {e}")
            return {'canonical': cls.UNIT_SYMBOLS, 'mappings': {}}
    
    @staticmethod
    def is_unit(word: str, custom_mappings: Dict[str, str] = None) -> bool:
        """
        Check if a word is a unit or maps to a unit
        
        Args:
            word: Word to check
            custom_mappings: Optional custom mappings dictionary
            
        Returns:
            True if word is a unit
        """
        if not word:
            return False
        
        # Special case for % symbol
        if word == '%':
            return True
            
        word_normalized = ''.join(c.lower() for c in word if c.isalnum())
        
        # Check against known units
        if word_normalized in NormalizationUtils.UNIT_WORDS:
            return True
        if word_normalized in NormalizationUtils.UNIT_SYMBOLS:
            return True
        # Also check temporal words (to prevent element parsing of "1.5 jaar")
        if word_normalized in NormalizationUtils.TEMPORAL_WORDS:
            return True
            
        # Check custom mappings
        if custom_mappings:
            mapped = custom_mappings.get(word_normalized)
            if mapped in NormalizationUtils.UNIT_SYMBOLS:
                return True
                
        return False
    
    @staticmethod
    def should_attach_unit(previous_token: str, unit_token: str) -> bool:
        """
        Determine if a unit should be attached to the previous token
        
        Args:
            previous_token: The token before the unit
            unit_token: The unit token
            
        Returns:
            True if unit should be attached without space
        """
        if not previous_token or not unit_token:
            return False
            
        # Check if previous token is a number
        cleaned = previous_token.replace('.', '').replace(',', '')
        if not cleaned.replace('%', '').replace('mm', '').replace('cm', '').replace('m', '').replace('ml', '').replace('mg', '').replace('kg', '').isdigit():
            return False
            
        # Check if current token is a unit or unit symbol
        # Special handling for % symbol
        if unit_token in ['%', 'mm', 'cm', 'm', 'ml', 'mg', 'kg']:
            return True
        
        # Don't attach temporal words - they should keep the space ("1.5 jaar" not "1.5jaar")
        unit_normalized = ''.join(c.lower() for c in unit_token if c.isalnum())
        if unit_normalized in NormalizationUtils.TEMPORAL_WORDS:
            return False
            
        # Check if current token is a unit
        return NormalizationUtils.is_unit(unit_token)
    
    @staticmethod
    def attach_unit_to_number(number: str, unit: str, 
                             custom_mappings: Dict[str, str] = None) -> str:
        """
        Attach a unit to a number, converting to abbreviation if needed
        
        Args:
            number: The number to attach to
            unit: The unit to attach
            custom_mappings: Optional mappings for unit conversion
            
        Returns:
            Number with unit attached (e.g., "30%")
        """
        # Get unit abbreviation if available
        if custom_mappings:
            unit_normalized = ''.join(c.lower() for c in unit if c.isalnum())
            unit = custom_mappings.get(unit_normalized, unit)
            
        return number + unit
    
    @staticmethod
    def normalize_units(unit_word: str) -> str:
        """Convert unit words to abbreviations (procent→%, millimeter→mm)"""
        unit_mappings = {
            'procent': '%', 'percent': '%',
            'millimeter': 'mm', 'milimeter': 'mm', 
            'centimeter': 'cm'
        }
        return unit_mappings.get(unit_word.lower(), unit_word)
    
    @staticmethod
    def is_followed_by_unit(words: List[str], current_index: int,
                           custom_mappings: Dict[str, str] = None) -> bool:
        """
        Check if the word at current_index is followed by a unit
        
        Args:
            words: List of words
            current_index: Index of current word
            custom_mappings: Optional custom mappings
            
        Returns:
            True if next word is a unit
        """
        if current_index + 1 >= len(words):
            return False
            
        next_word = words[current_index + 1]
        return NormalizationUtils.is_unit(next_word, custom_mappings)
    
    @staticmethod
    def has_decimal_separator(text: str) -> bool:
        """
        Check if text contains a decimal separator (. or ,) with digits
        
        Args:
            text: Text to check
            
        Returns:
            True if text has decimal separator between digits
        """
        return bool(re.match(r'^\d+[.,]\d+', text.strip()))
    
    @staticmethod
    def process_unit_attachment(words: List[str], index: int, result: List[str],
                               custom_mappings: Dict[str, str] = None) -> bool:
        """
        Process potential unit attachment at given index
        
        Args:
            words: List of words being processed
            index: Current word index
            result: Result list being built
            custom_mappings: Optional custom mappings
            
        Returns:
            True if unit was attached and processed
        """
        if index >= len(words):
            return False
            
        word = words[index]
        word_normalized = ''.join(c.lower() for c in word if c.isalnum())
        
        # Check if this word maps to a unit
        mapped = None
        if custom_mappings and word_normalized in custom_mappings:
            mapped = custom_mappings[word_normalized]
            
        # If mapped to a unit and previous result is a number, attach
        if mapped in NormalizationUtils.UNIT_SYMBOLS and result:
            last_result = result[-1]
            if last_result.replace('.', '').replace(',', '').isdigit():
                result[-1] = last_result + mapped
                return True
                
        # Check if current word is already a unit symbol
        if word_normalized in NormalizationUtils.UNIT_SYMBOLS and result:
            last_result = result[-1]
            if last_result.replace('.', '').replace(',', '').isdigit():
                result[-1] = last_result + word
                return True
                
        return False
    
    @staticmethod
    def should_parse_as_element(word: str, next_word: Optional[str] = None,
                               custom_mappings: Dict[str, str] = None) -> bool:
        """
        Determine if a word should be parsed as an element number
        
        Args:
            word: Word to check
            next_word: Optional next word for context
            custom_mappings: Optional custom mappings
            
        Returns:
            False if word should NOT be parsed as element
        """
        # Don't parse if followed by a unit
        if next_word and NormalizationUtils.is_unit(next_word, custom_mappings):
            return False
            
        # Don't parse numbers with decimal separators
        if NormalizationUtils.has_decimal_separator(word):
            return False
            
        return True
    
    @staticmethod
    def is_temporal_context(words: List[str], current_index: int) -> bool:
        """
        Check if the current position has temporal context
        
        Args:
            words: List of words
            current_index: Index of current word
            
        Returns:
            True if in temporal context (e.g., "1.5 jaar")
        """
        # Check if next word is temporal
        if current_index + 1 < len(words):
            next_word = words[current_index + 1].lower()
            if next_word in NormalizationUtils.TEMPORAL_WORDS:
                return True
                
        # Check if previous word indicates temporal context
        if current_index > 0:
            prev_word = words[current_index - 1].lower()
            if prev_word in ['sinds', 'voor', 'na', 'over']:
                return True
                
        return False
    
    @staticmethod
    def normalize_text_for_matching(text: str) -> str:
        """
        Normalize text for matching/comparison
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text (lowercase, alphanumeric only)
        """
        return ''.join(c.lower() for c in text if c.isalnum())
    
    @staticmethod
    def split_token(word: str) -> Tuple[str, str, str]:
        """
        Split a token into prefix punctuation, core text, and suffix punctuation
        
        Args:
            word: Word to split (e.g., "(element26:" or "16;")
            
        Returns:
            Tuple of (prefix, core, suffix) where:
            - prefix: Opening punctuation like (, [, {, quotes
            - core: The actual word/number without punctuation
            - suffix: Closing punctuation including :, ;, ., !, ?, ), ], }
            
        Examples:
            "element26:" → ("", "element26", ":")
            "(16;" → ("(", "16", ";")
            "test." → ("", "test", ".")
        """
        if not word:
            return "", "", ""
            
        match = _TOKEN_RE.match(word)
        if not match:
            # Fallback: return the word as core
            return "", word, ""
            
        pre = match.group('pre') or ""
        core = match.group('core') or ""
        mid = match.group('mid') or ""
        post = match.group('post') or ""
        
        # Combine mid and post as suffix
        return pre, core, mid + post
    
    @staticmethod
    def join_token(prefix: str, core: str, suffix: str) -> str:
        """
        Reassemble a token from its parts
        
        Args:
            prefix: Opening punctuation
            core: Core text
            suffix: Closing punctuation
            
        Returns:
            Reassembled token with punctuation preserved
            
        Examples:
            ("", "element 26", ":") → "element 26:"
            ("(", "element 16", ";") → "(element 16;"
        """
        return f"{prefix}{core}{suffix}"
    
    @staticmethod
    def parse_elements(text: str) -> str:
        """
        Parse and normalize element patterns in text
        
        Converts dental element patterns like "1-4", "14", "de 11" to "element 14" format.
        Handles various input formats:
        - "1-4" → "element 14"
        - "14" → "element 14" 
        - "de 11" → "element 11"
        - "element 26" → "element 26" (unchanged)
        
        Args:
            text: Input text containing potential element patterns
            
        Returns:
            Text with element patterns normalized to "element XX" format
        """
        if not text:
            return text
            
        # Valid dental element numbers (adult teeth)
        valid_elements = {
            '11', '12', '13', '14', '15', '16', '17', '18',  # Upper right
            '21', '22', '23', '24', '25', '26', '27', '28',  # Upper left
            '31', '32', '33', '34', '35', '36', '37', '38',  # Lower left
            '41', '42', '43', '44', '45', '46', '47', '48'   # Lower right
        }
        
        # Split text into words for processing
        words = text.split()
        result = []
        i = 0
        
        while i < len(words):
            word = words[i]
            
            # Handle "de [number]" pattern - convert to element
            if word.lower() == 'de' and i + 1 < len(words):
                next_word = words[i + 1]
                # Check if next word is a valid element number
                if next_word in valid_elements:
                    result.append(f"element {next_word}")
                    i += 2  # Skip both "de" and the number
                    continue
                    
            # Handle patterns like "1-4", "1.4", "1,4", "1/4"
            element_patterns = [
                r'^([1-8])\s*-\s*([1-8])$',    # "1-4", "1 - 4"
                r'^([1-8])\.([1-8])$',         # "1.4"
                r'^([1-8]),([1-8])$',          # "1,4"  
                r'^([1-8])/([1-8])$',          # "1/4"
                r'^([1-8])([1-8])$'            # "14"
            ]
            
            element_match = None
            for pattern in element_patterns:
                match = re.match(pattern, word)
                if match:
                    # Combine the two digits
                    element_num = match.group(1) + match.group(2)
                    if element_num in valid_elements:
                        element_match = element_num
                        break
                        
            if element_match:
                result.append(f"element {element_match}")
                i += 1
                continue
                
            # Skip if word is "element" and followed by a valid element number
            if (word.lower() == 'element' and 
                i + 1 < len(words) and 
                words[i + 1] in valid_elements):
                result.append(word)  # Keep "element" as is, will process next word normally
                i += 1
                continue
                
            # Handle standalone numbers that are valid elements (but not if already prefixed with "element")
            if (word in valid_elements and 
                (i == 0 or words[i-1].lower() != 'element')):
                result.append(f"element {word}")
                i += 1
                continue
                
            # Keep word as-is if no element pattern matched
            result.append(word)
            i += 1
            
        return ' '.join(result)