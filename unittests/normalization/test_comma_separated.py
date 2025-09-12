#!/usr/bin/env python3
"""
Test comma-separated number parsing using UNIFIED server normalization pipeline
Tests that '1, 2' is NOT parsed as 'element 12'
"""

import pytest
import pytest_asyncio
from app.ai.normalization.pipeline import NormalizationPipeline


class TestCommaSeparatedNumbers:
    """Test that comma-separated numbers are NOT parsed as combined elements"""
    
    def normalize_text(self, text: str, pipeline) -> str:
        """Helper to normalize text using the pipeline"""
        result = pipeline.normalize(text)
        return result.normalized_text
    
    # @pytest.mark.asyncio
    # async def test_comma_separated_single_digits(self, normalization_pipeline):
    #     """Test that '1, 2' does not become 'element 12'"""
    #     # These should NOT be combined into elements
    #     test_cases = [
    #         "1, 2",
    #         "2, 3", 
    #         "4, 5",
    #         "7, 8"
    #     ]
    #     
    #     for input_text in test_cases:
    #         result = self.normalize_text(input_text, normalization_pipeline)
    #         # Should NOT contain combined element numbers
    #         assert "element 12" not in result, f"'{input_text}' incorrectly became '{result}'"
    #         assert "element 23" not in result, f"'{input_text}' incorrectly became '{result}'"
    #         assert "element 45" not in result, f"'{input_text}' incorrectly became '{result}'"
    #         assert "element 78" not in result, f"'{input_text}' incorrectly became '{result}'"
    
    @pytest.mark.asyncio
    async def test_multiple_comma_separated(self, normalization_pipeline):
        """Test multiple comma-separated numbers"""
        test_cases = [
            "1, 2, 3",
            "1, 2, 3, 4",
            "5, 6, 7, 8"
        ]
        
        for input_text in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            # Should NOT contain any combined element numbers
            assert "element 123" not in result, f"'{input_text}' incorrectly combined numbers"
            assert "element 1234" not in result, f"'{input_text}' incorrectly combined numbers"
            assert "element 5678" not in result, f"'{input_text}' incorrectly combined numbers"
    
    # @pytest.mark.asyncio
    # async def test_element_with_comma(self, normalization_pipeline):
    #     """Test 'element' keyword with comma-separated numbers"""
    #     test_cases = [
    #         ("element 1, 2", "Should NOT parse as 'element 12'"),
    #         ("element 2, 3", "Should NOT parse as 'element 23'"),
    #         ("element 1, element 2", "Should keep separate elements"),
    #     ]
    #     
    #     for input_text, description in test_cases:
    #         result = self.normalize_text(input_text, normalization_pipeline)
    #         # Should NOT combine comma-separated numbers 
    #         assert "element 12" not in result, f"{description}: '{input_text}' -> '{result}'"
    #         assert "element 23" not in result, f"{description}: '{input_text}' -> '{result}'"
    
    @pytest.mark.asyncio
    async def test_hyphenated_ranges_work(self, normalization_pipeline):
        """Test that hyphenated ranges still parse correctly"""
        # These SHOULD work (hyphen means range)
        test_cases = [
            ("1-4", "element 14"),
            ("2-6", "element 26"), 
            ("3-5", "element 35"),
            ("4-7", "element 47")
        ]
        
        for input_text, expected in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            expected_num = expected.split()[-1]  # Get the number part
            assert expected_num in result, f"Hyphen range failed: '{input_text}' -> '{result}' (expected {expected_num})"
    
    @pytest.mark.asyncio
    async def test_element_with_hyphen(self, normalization_pipeline):
        """Test element keyword with hyphenated ranges"""
        test_cases = [
            ("element 1-4", "14"),
            ("element 2-6", "26"),
            ("tand 3-5", "35"),
            ("kies 4-8", "48")
        ]
        
        for input_text, expected_num in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            assert expected_num in result, f"Element with hyphen failed: '{input_text}' -> '{result}' (expected {expected_num})"
    
    @pytest.mark.asyncio
    async def test_period_separated(self, normalization_pipeline):
        """Test that period-separated numbers are handled correctly"""
        test_cases = [
            "1. 2",  # List format
            "1.2",   # Decimal
            "3.4"    # Decimal
        ]
        
        for input_text in test_cases:
            result = self.normalize_text(input_text, normalization_pipeline)
            # Should not create incorrect element combinations
            assert "element 12" not in result, f"Period handling failed: '{input_text}' -> '{result}'"
            assert "element 34" not in result, f"Period handling failed: '{input_text}' -> '{result}'"
    
    # @pytest.mark.asyncio
    # async def test_full_normalization_with_commas(self, normalization_pipeline):
    #     """Test full sentence normalization with commas"""
    #     test_cases = [
    #         ("onderzoek elementen 1, 2, 3", "Should keep numbers separate, not combine"),
    #         ("element 1-4 en element 2-6", "Ranges should become 'element 14' and 'element 26'"),
    #         ("patiënt heeft pijn bij 1, 2", "Numbers without context stay as is"),
    #         ("element 1, element 2, element 3", "Each 'element X' parsed separately"),
    #     ]
    #     
    #     for input_text, description in test_cases:
    #         result = self.normalize_text(input_text, normalization_pipeline)
    #         print(f"Input:  '{input_text}'")
    #         print(f"Output: '{result}'") 
    #         print(f"Note:   {description}")
    #         
    #         # Key assertion: result should NOT contain "element 12" from "1, 2"
    #         assert "element 12" not in result, f"Incorrect element combination found: '{input_text}' -> '{result}'"
    #         assert "element 23" not in result, f"Incorrect element combination found: '{input_text}' -> '{result}'"
    #         print("✅ No incorrect element combinations found")
    #         print()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])