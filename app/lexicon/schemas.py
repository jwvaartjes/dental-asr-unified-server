"""
Pydantic schemas for lexicon management endpoints.
"""
from typing import Optional
from pydantic import BaseModel


class LexiconTermRequest(BaseModel):
    """Request schema for adding/removing lexicon terms."""
    term: str
    category: str
    
    def model_post_init(self, __context) -> None:
        """Use centralized validation after Pydantic initialization"""
        # Note: In the unified server, we'll add validation via DataRegistry if needed
        pass


class LexiconCategoryRequest(BaseModel):
    """Request schema for adding/deleting lexicon categories."""
    category: str


class ProtectedWordsRequest(BaseModel):
    """Request schema for protected words data."""
    protected_words: list[str]


class VariantRequest(BaseModel):
    """Request schema for adding/removing variants/abbreviations of canonical terms."""
    canonical_term: str
    variant: str
    category: str


class MultiWordVariantRequest(BaseModel):
    """Request schema for adding/removing multi-word variants of canonical terms."""
    canonical_term: str
    variant_phrase: str  # Multi-word phrase that should map to canonical_term
    category: str


class AutoVariantRequest(BaseModel):
    """Request schema for auto-detected variant management."""
    canonical_term: str
    variant: str


class AutoMultiWordVariantRequest(BaseModel):
    """Request schema for auto-detected multi-word variant management."""
    canonical_term: str
    variant_phrase: str


class CanonicalTermInfoRequest(BaseModel):
    """Request schema for finding canonical term information."""
    canonical_term: str