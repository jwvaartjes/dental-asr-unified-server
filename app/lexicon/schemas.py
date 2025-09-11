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