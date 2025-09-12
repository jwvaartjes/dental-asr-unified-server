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
    pytest.main([__file__, "-v"])