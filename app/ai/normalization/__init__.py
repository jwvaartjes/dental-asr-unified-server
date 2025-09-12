"""
Dental Normalization Module

Provides unified normalization functionality for dental ASR systems.
Includes text processing, learnable rules, and Dutch language support.
"""

from .pipeline import NormalizationPipeline
from .factory import NormalizationFactory

__all__ = ['NormalizationPipeline', 'NormalizationFactory']