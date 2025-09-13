#!/usr/bin/env python3
"""
Comprehensive unit tests for dental normalization - MIGRATED TO NEW ARCHITECTURE
Run this to ensure no regressions when adding new patterns to the unified server
"""

import pytest
import pytest_asyncio
import time


class TestDentalNormalization:
    """Test suite for dental normalization using new unified architecture with pytest-asyncio"""
    
    def run_test_cases_with_timing(self, test_name: str, test_cases: list, pipeline):
        """Helper method to run test cases with detailed timing output"""
        print(f"\n🧪 {test_name}")
        print("=" * 60)
        
        total_time = 0
        passed = 0
        failed = 0
        
        for i, case in enumerate(test_cases, 1):
            if isinstance(case, tuple) and len(case) >= 2:
                input_text, expected = case[0], case[1]
                
                # Time the normalization
                start_time = time.time()
                try:
                    # Use new NormalizationPipeline
                    result = pipeline.normalize(input_text)
                    # Extract normalized text from result
                    actual = result.normalized_text
                    elapsed_ms = (time.time() - start_time) * 1000
                    total_time += elapsed_ms
                    
                    # Check result
                    if actual == expected:
                        status = "✅"
                        passed += 1
                    else:
                        status = "❌"
                        failed += 1
                    
                    print(f"{status} {elapsed_ms:6.1f}ms: \"{input_text}\" → \"{actual}\"")
                    if status == "❌":
                        print(f"              Expected: \"{expected}\"")
                    
                except Exception as e:
                    elapsed_ms = (time.time() - start_time) * 1000
                    total_time += elapsed_ms
                    failed += 1
                    print(f"💥 {elapsed_ms:6.1f}ms: \"{input_text}\" → ERROR: {e}")
        
        # Summary
        avg_time = total_time / len(test_cases) if test_cases else 0
        print(f"\n📊 {test_name} Summary:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏱️  Average time: {avg_time:.1f}ms")
        print(f"   ⏱️  Total time: {total_time:.1f}ms")
        
        return failed == 0
    
    def _assert_equal_ignore_first_capital(self, actual, expected, msg=None):
        """Helper to compare strings ignoring first letter capitalization"""
        if actual == expected:
            return
        
        # Check if they're equal when both lowercase
        if actual and expected and actual.lower() == expected.lower():
            return
        
        # Check if only first letter differs in capitalization
        if actual and expected and len(actual) == len(expected):
            if actual[0].lower() == expected[0].lower() and actual[1:] == expected[1:]:
                return
        
        # If none of the above, raise assertion error
        raise AssertionError(f"{msg}: '{actual}' != '{expected}'")
    
    def normalize_text(self, text: str, pipeline) -> str:
        """Helper to normalize text using the pipeline"""
        result = pipeline.normalize(text)
        return result.normalized_text
    
    @pytest.mark.asyncio
    async def test_element_parsing_basic(self, normalization_pipeline):
        """Test basic element number parsing"""
        test_cases = [
            ("element 14", "element 14"),
            ("element 26", "element 26"),
            ("1-4", "element 14"),
            # Test "de" removal before element
            ("de 11", "element 11"),
            ("de 46", "element 46"),
            ("de element 14", "element 14"),
            ("cariës distaal van de 1-4", "cariës distaal van element 14"),
            ("1 -4", "element 14"),
            ("14", "element 14"),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            self._assert_equal_ignore_first_capital(result, expected, f"Failed: {input_text} -> {result} (expected {expected})")
    
    @pytest.mark.asyncio
    async def test_dutch_number_words(self, normalization_pipeline):
        """Test Dutch number word parsing"""
        test_cases = [
            ("element een vier", "element 14"),
            ("element twee zes", "element 26"),
            ("element drie vijf", "element 35"),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            self._assert_equal_ignore_first_capital(result, expected, f"Failed: {input_text} -> {result} (expected {expected})")
    
    @pytest.mark.asyncio
    async def test_dental_context_triggers(self, normalization_pipeline):
        """Test dental context-aware parsing"""
        test_cases = [
            ("tand een vier", "tand 14"),
            ("kies twee zes", "kies 26"),
            ("tand 14", "tand 14"),
            ("kies 1-4", "kies 14"),
            ("molaar drie vijf", "molaar 35"),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            self._assert_equal_ignore_first_capital(result, expected, f"Failed: {input_text} -> {result} (expected {expected})")
    
    @pytest.mark.asyncio
    async def test_element_with_surfaces(self, normalization_pipeline):
        """Test element parsing combined with surface terms - maintains word order"""
        test_cases = [
            ("element 14 distaal", "element 14 distaal"),  # Maintains original order
            ("tand een vier distaal", "tand 14 distaal"),
            ("1-4 mesiopalatinaal", "element 14 mesiopalatinaal"),
            ("kies 26 buccaal", "kies 26 buccaal"),
            ("distaal element 14", "distaal element 14"),  # Already in desired order
            ("mesiopalatinaal tand 26", "mesiopalatinaal tand 26"),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            self._assert_equal_ignore_first_capital(result, expected, f"Failed: {input_text} -> {result} (expected {expected})")
    
    @pytest.mark.asyncio
    async def test_custom_patterns(self, normalization_pipeline):
        """Test custom pattern mappings"""
        test_cases = [
            ("karius", "cariës"),
            ("Karius", "cariës"),
            ("KARIUS", "cariës"),
            ("karius!", "cariës"),
            ("karius,", "cariës"),
            ("bukkaal", "buccaal"),
            ("festubilair", "vestibulair"),
            # Test period preservation in canonical terms
            ("circa", "ca."),
            ("Circa", "ca."),
            ("CIRCA", "ca."),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            # Custom patterns should be exact matches
            assert result.lower() == expected.lower(), f"Failed: {input_text} -> {result} (expected {expected})"
    
    @pytest.mark.asyncio
    async def test_hyphen_normalization_from_stable(self, normalization_pipeline):
        """Test hyphen normalization from stable baseline (CRITICAL TESTS)"""
        test_cases = [
            # Key hyphen removal tests from stable normalization
            ('licht-mucosale', 'licht mucosale'),        # Remove hyphen  
            ('licht-mucosaal', 'licht mucosaal'),        # Remove hyphen
            ('mesio-occlusaal', 'mesio occlusaal'),      # Remove hyphen
            ('mesio-buccaal', 'mesio buccaal'),          # Remove hyphen
            ('disto-occlusaal', 'disto occlusaal'),      # Remove hyphen
            ('disto-buccaal', 'disto buccaal'),          # Remove hyphen
            
            # Hyphenated terms that should get hyphens
            ('veriapicaal', 'peri-apicaal'),             # Add hyphen
            ('periapicaal', 'peri-apicaal'),             # Add hyphen
            ('peri-apicaal', 'peri-apicaal'),            # Keep hyphen
            
            # Should stay as is
            ('verticaal', 'verticaal'),
            ('apicaal', 'apicaal'),
            ('radiaal', 'radiaal'),
            ('occlusaal', 'occlusaal'),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            assert result.lower() == expected.lower(), f"CRITICAL: {input_text} -> {result} (expected {expected})"
    
    @pytest.mark.asyncio
    async def test_phonetic_false_positives_from_stable(self, normalization_pipeline):
        """Test that phonetic matching doesn't create false positives (CRITICAL)"""
        test_cases = [
            # Important phonetic fixes - should NOT create false matches
            ('interproximaal', 'interproximaal'),        # NOT intermaxillair
            ('lich', 'lich'),                           # NOT laesie
            ('lich mucosaal', 'lich mucosaal'),         # Keep as-is
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            assert result.lower() == expected.lower(), f"PHONETIC CRITICAL: {input_text} -> {result} (expected {expected})"
    
    @pytest.mark.asyncio
    async def test_comma_separated_elements_from_stable(self, normalization_pipeline):
        """Test comma-separated element parsing (CRITICAL REGEX FIX)"""
        test_cases = [
            ('1, 2, 3', '1, 2, 3'),                     # Should NOT become "element 12, 3"
            ('14;15;16', 'element 14; element 15; element 16'),
            ('element 1, 2', 'element 12'),             
            ('1-4 en 2-3', 'element 14 en element 23'),
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            assert result.lower() == expected.lower(), f"COMMA CRITICAL: {input_text} -> {result} (expected {expected})"
    
    @pytest.mark.asyncio
    async def test_comprehensive_stable_baseline_cases(self, normalization_pipeline):
        """ALL TEST CASES from stable_baseline_workspace"""

        test_cases = [
            # Basic element parsing tests - from test_baseline.py
            ('element een vier', 'element 14'),
            ('karius', 'cariës'),
            ('1-4', 'element 14'),
            ('messial', 'mesiaal'),
            ('30 procent', '30%'),

            ("Element 26:", "element 26:"),  # Should preserve colon
            ("Element 26", "element 26"),    # No colon to preserve
            ("26:", "element 26:"),          # Direct number with colon
            ("26", "element 26"),            # Direct number without colon
            ("element 26:", "element 26:"),  # Lowercase with colon
            ("element 26", "element 26"),    # Lowercase without colon
          
            
            # Element parsing from stable tests
            ('14', 'element 14'),
            ('de 11', 'element 11'),                    
            ('tand een vier', 'tand 14'),               
            ('kies twee drie', 'kies 23'),              
            ('element 14 element 14', 'element 14'),     # Deduplication
            
            # Number words and context
            ('element een vier', 'element 14'),         # NOT "element element 14"
            ('de element 11', 'element 11'),            # Lidwoord cleanup
            ('molaar 6 7', 'molaar 67'),                # Context combination
            ('premolaar 4 5', 'premolaar 45'),          # Context combination
            
            # Abbreviations and variants
            ('circa', 'ca.'),
            ('botverlies', 'botverlies'),
            ('bot verlies', 'botverlies'),               # Compound
            ('bot-verlies', 'botverlies'), 


            # Protected words should remain unchanged
            ('Paro', 'Paro'),
            ('30% botverlies', '30% botverlies'),        # No fuzzy on percentages
            
            # Additional stable baseline tests
            ('linguaal', 'linguaal'),
            ('palatinaal', 'palatinaal'),
            ('bucaal', 'buccaal'),                      # Variant correction
            ('vestibuleer', 'vestibulair'),             # Variant correction
            ('gingivale', 'gingivale'),
            ('subgingivaal', 'subgingivaal'),
            ('supragingival', 'supragingivaal'),         # Variant correction
            
            # Composite and restoration terms
            ('composiet', 'composiet'),
            ('amalgaam', 'amalgaam'),
            ('kroon', 'kroon'),          
            ('endo', 'endodontische behandeling'), # Expansion
            
            # Periodontal terms
            ('parodontitis', 'parodontitis'),
            ('gingivitis', 'gingivitis'),
            ('tandvlees', 'tandvlees'),
            ('pocket', 'pocket'),
            
            
            # Anatomical terms
            ('maxilla', 'maxilla'),
            ('mandibula', 'mandibula'),
            ('processus', 'processus'),
            ('alveolaire', 'alveolaire'),
            ('bovenkaak', 'bovenkaak'),

             # measerements
            ("15 mm", "15mm"),
            ("1,5 jaar", "1,5 jaar"),
            ("12 weken", "12 weken"),
            ("1-4 mm", "1-4mm"),
              
            # Custom patterns
            ("karius", "cariës"),
            ("bukkaal", "buccaal"),
            ("festubilair", "vestibulair"),

            
            # Complex combinations
            ("cariës distaal van de 1-4", "cariës distaal van element 14"),
            ("element een vier distaal", "element 14 distaal"),
            ("karius op kies twee zes", "cariës op kies 26"),

            ("element 41: cariës distaal", "element 41: cariës distaal"),
            ("41: cariës", "element 41: cariës distaal"),
            ("element vijfenveertig: occlusaal", "element 45: cariës distaal"),


    ("cariës distaal van 1-4",                  "cariës distaal van element 14"),
    ("cariës op 1 2",                           "cariës op element 12"),
    ("cariës op een vier",                      "cariës op element 14"),
    ("de 11 is gevoelig",                       "element 11 is gevoelig"),
    ("element 1, 2 vertoont contact",           "element 12 vertoont contact"),
    ("de 1 2 interfereert",                     "element 12 interfereert"),  # lijst van 3 NIET samenvoegen

    # --- Fuzzy met diacritics & punct ---
    ("karius!",                                 "cariës"),
    ("karius-achtige laesie",                   "cariës-achtige laesie"),
    ("cariüs distaal",                          "cariës distaal"),

    # --- Hyphens: canoniek behouden, niet-canoniek splitsen ---
    ("mesio-occlusaal contact",                 "mesio-occlusaal contact"),  # canoniek hyphen
    ("licht-mucosale zwelling",                 "licht mucosale zwelling"),     # niet-canoniek → split vóór fuzzy
    ("distobuccaal is oké",                     "distobuccaal is oké"),      # canoniek 1-woord (geen split)
    ("1-4 is zichtbaar",                        "element 14 is zichtbaar"),  # cijferpaar blijft element

    # --- Units & spacing ---
    ("30 procent botverlies",                   "30% botverlies"),
    ("15 mm pocket",                            "15mm pocket"),
    ("1-4 mm overlap",                          "1-4mm overlap"),            # unit-guard voorkomt element-conversie
    ("0.5 mm incisale slijtage",                   "0.5mm incisale slijtage"),     # decimaal blijft, unit compact

    # --- Röntgen: begrippen & combinaties ---
    ("bitewing rechts: cariës distaal 1-4",     "bitewing rechts: cariës distaal element 14"),
    ("periapicaal apicaal beeld element 12",    "periapicaal apicaal beeld element 12"),
    ("PA regio 13 toont overlap",               "PA regio 13 toont overlap"),
    ("overlap bij 1, 2 (contactpunten)",        "overlap bij 1, 2 (contactpunten)"),

    # --- Multi-woord fuzzy met veto/minima ---
    ("parodontale pocket bij 2 4",                     "parodontale pocket bij element 24"),   # let op: 'Paro' is protected → alleen 'pocket' blijft
    ("bot verlies element 35",                  "botverlies element 35"),        # samenvoeging tot canoniek 1-woord
    ("interproximaal is schoon",                "interproximaal is schoon"),     # mag NIET naar intermaxillair
    ("vestibuleer oppervlakkig",                "vestibulair oppervlakkig"),     # wél naar adj., niet naar 'vestibulum'

    # --- Edge-cases die vroeger misgingen ---
    ("een vierkant bestaat",                    "een vierkant bestaat"),         # 'een vier' binnen 'vierkant' mag NIET
    ("de element 14 is gevuld",                 "element 14 is gevuld"),         # cleanup 'de element '
    ("elemet occlusaal",                        "element occlusaal"),    
        
            
        ]
        
        assert self.run_test_cases_with_timing("Comprehensive Stable Baseline Test", test_cases, normalization_pipeline)
    
    @pytest.mark.asyncio
    async def test_comprehensive_performance(self, normalization_pipeline):
        """Test comprehensive set of cases with performance measurement"""
        test_cases = [
            # Element parsing
            ("1-4", "element 14"),
            ("2-6", "element 26"),
            ("de 11", "element 11"),
            
            # Dutch numbers
            ("element een vier", "element 14"),
            ("tand twee zes", "tand 26"),
            
            # Custom patterns
            ("karius", "cariës"),
            ("bukkaal", "buccaal"),
            ("festubilair", "vestibulair"),
            
            # Complex combinations
            ("cariës distaal van de 1-4", "cariës distaal van element 14"),
            ("element een vier distaal", "element 14 distaal"),
            ("karius op kies twee zes", "cariës op kies 26"),
        ]
        
        assert self.run_test_cases_with_timing("Comprehensive Performance Test", test_cases, normalization_pipeline)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])  # Stop on first failure for debugging
