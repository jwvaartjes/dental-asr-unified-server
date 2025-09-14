#!/usr/bin/env python3
"""
Dutch Post-Processing Module for Whisper Transcriptions
Corrects common Dutch transcription errors and word formations
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DutchCorrection:
    """Represents a Dutch text correction"""
    original: str
    corrected: str
    correction_type: str  # 'filler', 'compound', 'spelling', 'pronoun'
    confidence: float = 1.0


class DutchPostProcessor:
    """
    Post-processes Whisper transcriptions for Dutch-specific corrections
    Handles common misrecognitions, compound words, and Dutch language patterns
    """
    
    def __init__(self, canonical_terms: set = None):
        """Initialize Dutch post-processor with correction rules"""
        
        # Canonical terms with specific capitalization that must be preserved
        self.canonical_terms = canonical_terms or set()
        # Create lowercase mapping for fast lookup
        self.canonical_terms_lower_map = {}
        if canonical_terms:
            for term in canonical_terms:
                self.canonical_terms_lower_map[term.lower()] = term
        
        # Protected abbreviations that should never be capitalized
        self.PROTECTED_ABBREVIATIONS = {
            # Medical/dental abbreviations
            'ca.', 'etc.', 'vs.', 'i.e.', 'e.g.', 'bijv.', 'bv.', 
            # Titles and honorifics
            'dhr.', 'mw.', 'dr.', 'prof.', 'ing.',
            # Common abbreviations
            'nl.', 'eng.', 'enz.', 'resp.', 'incl.', 'excl.',
            # Units that might start sentences
            'mm.', 'cm.', 'kg.', 'gr.', 'ml.'
        }
        
        # Common filler sound corrections
        self.filler_corrections = {
            " uh ": " eh ",   # Dutch filler sound
            " um ": " ehm ",  # Dutch version
            " uhm ": " ehm ",
            " euh ": " eh ",  # Alternative spelling
            " hmm ": " hm ",  # Simplified
        }
        
        # Common English → Dutch corrections
        self.english_to_dutch = {
            "okay": "oké",
            "ok": "oké",
            "yeah": "ja",
            "yes": "ja",
            "no": "nee",
            "please": "alstublieft",
            "thanks": "bedankt",
            "thank you": "dank je",
            "sorry": "sorry",  # Same but ensure consistency
            "bye": "doei",
            "hello": "hallo",
            "hi": "hoi",
        }
        
        # Common pronoun errors
        self.pronoun_corrections = {
            " i ": " ik ",     # Very common error
            " i'm ": " ik ben ",
            " i'll ": " ik zal ",
            " i've ": " ik heb ",
            " u ": " u ",      # Keep formal 'u'
            " you ": " je ",   # English to Dutch
            " he ": " hij ",
            " she ": " zij ",
            " we ": " wij ",
            " they ": " zij ",
        }
        
        # Dutch compound words that Whisper often splits
        self.compound_words = {
            "voor beeld": "voorbeeld",
            "daar om": "daarom",
            "waar om": "waarom",
            "hier voor": "hiervoor",
            "daar voor": "daarvoor",
            "waar voor": "waarvoor",
            "hier door": "hierdoor",
            "daar door": "daardoor",
            "waar door": "waardoor",
            "hier mee": "hiermee",
            "daar mee": "daarmee",
            "waar mee": "waarmee",
            "hier in": "hierin",
            "daar in": "daarin",
            "waar in": "waarin",
            "hier op": "hierop",
            "daar op": "daarop",
            "waar op": "waarop",
            "hier over": "hierover",
            "daar over": "daarover",
            "waar over": "waarover",
            "hier bij": "hierbij",
            "daar bij": "daarbij",
            "waar bij": "waarbij",
            "hier na": "hierna",
            "daar na": "daarna",
            "waar na": "waarna",
            "hier uit": "hieruit",
            "daar uit": "daaruit",
            "waar uit": "waaruit",
            "hier aan": "hieraan",
            "daar aan": "daaraan",
            "waar aan": "waaraan",
            "hier van": "hiervan",
            "daar van": "daarvan",
            "waar van": "waarvan",
            "hier toe": "hiertoe",
            "daar toe": "daartoe",
            "waar toe": "waartoe",
            "hier tegen": "hiertegen",
            "daar tegen": "daartegen",
            "waar tegen": "waartegen",
            "hier onder": "hieronder",
            "daar onder": "daaronder",
            "waar onder": "waaronder",
            "hier boven": "hierboven",
            "daar boven": "daarboven",
            "waar boven": "waarboven",
            "hier tussen": "hiertussen",
            "daar tussen": "daartussen",
            "waar tussen": "waartussen",
            "hier langs": "hierlangs",
            "daar langs": "daarlangs",
            "waar langs": "waarlangs",
            "hier heen": "hierheen",
            "daar heen": "daarheen",
            "waar heen": "waarheen",
            "hier vandaan": "hiervandaan",
            "daar vandaan": "daarvandaan",
            "waar vandaan": "waarvandaan",
            # Time compounds
            "van daag": "vandaag",
            "van morgen": "vanmorgen",
            "van middag": "vanmiddag",
            "van avond": "vanavond",
            "van nacht": "vannacht",
            "van ochtend": "vanochtend",
            # Other common compounds
            "aan tal": "aantal",
            "aan deel": "aandeel",
            "aan dacht": "aandacht",
            "aan vraag": "aanvraag",
            "aan bod": "aanbod",
            "aan leiding": "aanleiding",
            "aan wezig": "aanwezig",
            "af spraak": "afspraak",
            "af stand": "afstand",
            "al gemeen": "algemeen",
            "al tijd": "altijd",
            "ant woord": "antwoord",
            "be drijf": "bedrijf",
            "be lang": "belang",
            "be langrijk": "belangrijk",
            "be roep": "beroep",
            "be staan": "bestaan",
            "be zoek": "bezoek",
            "bij voor beeld": "bijvoorbeeld",
            "eigen lijk": "eigenlijk",
            "ge bruik": "gebruik",
            "ge zicht": "gezicht",
            "mis schien": "misschien",
            "name lijk": "namelijk",
            "natuur lijk": "natuurlijk",
            "onder werp": "onderwerp",
            "ont wikkeling": "ontwikkeling",
            "over al": "overal",
            "tegen woordig": "tegenwoordig",
            "tussen door": "tussendoor",
            "uit eindelijk": "uiteindelijk",
            "voor al": "vooral",
            "waar schijnlijk": "waarschijnlijk",
        }
        
        # Common spelling variations to normalize
        self.spelling_corrections = {
            "zoo": "zo",
            "heel": "heel",  # Keep as is
            "heele": "hele",
            "goeie": "goede",
            "jullie": "jullie",  # Keep as is
            "hunnie": "hun",
            "zeg maar": "zegmaar",
            "dus ja": "dus",
            "ofzo": "of zo",
            "enzo": "en zo",
            "gwn": "gewoon",
            "idd": "inderdaad",
            "btw": "trouwens",
            "omg": "oh mijn god",
            "ff": "even",
            "dr": "er",
            "d'r": "er",
            "m'n": "mijn",
            "z'n": "zijn",
        }
        
        # Track all corrections for reporting
        self.corrections_made: List[DutchCorrection] = []
    
    def process(self, text: str, return_corrections: bool = False) -> Union[str, Tuple[str, List[DutchCorrection]]]:
        """
        Process text with all Dutch corrections
        
        Args:
            text: Input text to correct
            return_corrections: If True, return list of corrections made
            
        Returns:
            Corrected text, optionally with list of corrections
        """
        self.corrections_made = []
        original_text = text
        
        # Convert to lowercase for processing
        text_lower = text.lower()
        
        # Apply corrections in specific order
        text_lower = self._apply_filler_corrections(text_lower)
        text_lower = self._apply_pronoun_corrections(text_lower)
        text_lower = self._apply_compound_corrections(text_lower)
        text_lower = self._apply_english_corrections(text_lower)
        text_lower = self._apply_spelling_corrections(text_lower)
        
        # Fix punctuation spacing
        text_lower = self._fix_punctuation(text_lower)
        
        # Capitalize sentences
        corrected_text = self._capitalize_sentences(text_lower)
        
        # Log if corrections were made
        if corrected_text != original_text:
            logger.debug(f"Dutch corrections applied: {len(self.corrections_made)} changes")
            for correction in self.corrections_made[:5]:  # Log first 5
                logger.debug(f"  {correction.original} → {correction.corrected} ({correction.correction_type})")
        
        if return_corrections:
            return corrected_text, self.corrections_made
        return corrected_text
    
    def _apply_filler_corrections(self, text: str) -> str:
        """Apply Dutch filler sound corrections"""
        for old, new in self.filler_corrections.items():
            if old in text:
                count = text.count(old)
                text = text.replace(old, new)
                self.corrections_made.append(
                    DutchCorrection(old.strip(), new.strip(), 'filler')
                )
        return text
    
    def _apply_pronoun_corrections(self, text: str) -> str:
        """Fix common pronoun errors"""
        for old, new in self.pronoun_corrections.items():
            if old in text:
                count = text.count(old)
                text = text.replace(old, new)
                self.corrections_made.append(
                    DutchCorrection(old.strip(), new.strip(), 'pronoun')
                )
        return text
    
    def _apply_compound_corrections(self, text: str) -> str:
        """Fix Dutch compound words that were split"""
        for old, new in self.compound_words.items():
            if old in text:
                count = text.count(old)
                text = text.replace(old, new)
                self.corrections_made.append(
                    DutchCorrection(old, new, 'compound')
                )
        return text
    
    def _apply_english_corrections(self, text: str) -> str:
        """Replace English words with Dutch equivalents"""
        # Use word boundaries for more accurate replacement
        for eng, dutch in self.english_to_dutch.items():
            pattern = r'\b' + re.escape(eng) + r'\b'
            if re.search(pattern, text):
                text = re.sub(pattern, dutch, text)
                self.corrections_made.append(
                    DutchCorrection(eng, dutch, 'translation')
                )
        return text
    
    def _apply_spelling_corrections(self, text: str) -> str:
        """Normalize Dutch spelling variations"""
        for old, new in self.spelling_corrections.items():
            pattern = r'\b' + re.escape(old) + r'\b'
            if re.search(pattern, text):
                text = re.sub(pattern, new, text)
                self.corrections_made.append(
                    DutchCorrection(old, new, 'spelling')
                )
        return text


    def _fix_punctuation(self, text: str) -> str:
        """Fix spacing around punctuation"""
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        # Add space after punctuation if missing
        text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)
        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _capitalize_sentences(self, text: str) -> str:
        """Capitalize first letter of sentences, respecting protected abbreviations"""
        
        # Helper function to check if a position should be protected from capitalization
        def should_protect_position(text: str, pos: int) -> bool:
            """Check if the character at position should not be capitalized"""
            # Extract the word that would be capitalized
            remaining = text[pos:].split()
            if not remaining:
                return False
            
            first_word = remaining[0].lower()
            
            # Check if it's a protected abbreviation
            if first_word in self.PROTECTED_ABBREVIATIONS:
                return True
                
            # Check if it's a canonical term that should preserve its exact case
            if first_word in self.canonical_terms_lower_map:
                return True
                
            return False
        
        # Capitalize after sentence endings, but respect protected abbreviations
        def capitalize_match(m):
            sentence_end = m.group(1)  # ". ", "! ", "? "
            char_to_cap = m.group(2)   # The lowercase letter
            
            # Find position in original text
            pos = text.find(sentence_end + char_to_cap)
            if pos >= 0 and should_protect_position(text, pos + len(sentence_end)):
                # Don't capitalize - it's a protected abbreviation
                return sentence_end + char_to_cap
            else:
                # Normal capitalization
                return sentence_end + char_to_cap.upper()
        
        text = re.sub(r'([.!?]\s+)([a-z])', capitalize_match, text)
        
        # Capitalize first character, but only if it's not a protected abbreviation
        if text and text[0].islower():
            if not should_protect_position(text, 0):
                text = text[0].upper() + text[1:]
        
        # Restore canonical term capitalization throughout the text
        text = self._restore_canonical_capitalization(text)
        
        # Don't capitalize standalone 'i' as it's likely an error for 'ik'
        return text
    
    def _restore_canonical_capitalization(self, text: str) -> str:
        """Restore the correct capitalization for canonical terms throughout the text"""
        if not self.canonical_terms_lower_map:
            return text
            
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Check if this word (stripped of punctuation) is a canonical term
            word_clean = word.strip('.,!?:;').lower()
            if word_clean in self.canonical_terms_lower_map:
                # Replace with canonical capitalization, preserving punctuation
                canonical = self.canonical_terms_lower_map[word_clean]
                # Preserve punctuation at the end
                punctuation = ''
                for char in reversed(word):
                    if char in '.,!?:;':
                        punctuation = char + punctuation
                    else:
                        break
                corrected_words.append(canonical + punctuation)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def get_corrections_summary(self) -> Dict[str, int]:
        """Get summary of corrections made by type"""
        summary = {}
        for correction in self.corrections_made:
            if correction.correction_type not in summary:
                summary[correction.correction_type] = 0
            summary[correction.correction_type] += 1
        return summary


# Convenience function for direct use
def process_dutch_text(text: str) -> str:
    """
    Quick function to process Dutch text
    
    Args:
        text: Input text to correct
        
    Returns:
        Corrected text
    """
    processor = DutchPostProcessor()
    return processor.process(text)


if __name__ == "__main__":
    # Test examples
    test_texts = [
        "Uh, i think voor beeld dat waar om we daar om okay moeten zeggen.",
        "Van daag gaan we naar de tand arts voor een af spraak.",
        "I'm heel blij met de ont wikkeling van dit project.",
        "Um, waar voor is dit be langrijk? Mis schien voor al voor de test.",
        "De patiënt heeft last van zijn kies , dus we moeten een foto maken .",
    ]
    
    processor = DutchPostProcessor()
    
    print("Dutch Post-Processing Tests")
    print("=" * 60)
    
    for text in test_texts:
        corrected, corrections = processor.process(text, return_corrections=True)
        print(f"\nOriginal:  {text}")
        print(f"Corrected: {corrected}")
        if corrections:
            print(f"Changes:   {len(corrections)} corrections")
            for c in corrections[:3]:
                print(f"  - {c.original} → {c.corrected} ({c.correction_type})")
    
    print("\n" + "=" * 60)
    print("Post-processor ready for use!")