"""
Core normalization components.

Contains the fundamental building blocks for dental text normalization.
"""

from .variant_generator import VariantGenerator, _normalize_text
from .phonetic_matcher import DutchPhoneticMatcher

__all__ = ['VariantGenerator', '_normalize_text', 'DutchPhoneticMatcher']