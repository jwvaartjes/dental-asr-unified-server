"""
Loader interface for the data layer.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LoaderInterface(ABC):
    """Abstract base class for data loaders."""
    
    @abstractmethod
    async def load_lexicon(self, user_id: str) -> Dict[str, Any]:
        """Load lexicon data for user."""
        pass
    
    @abstractmethod
    async def load_custom_patterns(self, user_id: str) -> Dict[str, Any]:
        """Load custom patterns for user."""
        pass
    
    @abstractmethod
    async def load_protected_words(self, user_id: str) -> Dict[str, Any]:
        """Load protected words for user."""
        pass
    
    @abstractmethod
    async def load_config(self, user_id: str) -> Dict[str, Any]:
        """Load configuration for user."""
        pass
    
    @abstractmethod
    async def save_config(self, user_id: str, config_data: Dict[str, Any]) -> bool:
        """Save configuration for user."""
        pass
    
    @abstractmethod
    async def save_custom_patterns(self, user_id: str, patterns: Dict[str, Any]) -> bool:
        """Save custom patterns for user."""
        pass
    
    @abstractmethod
    async def save_lexicon(self, user_id: str, lexicon_data: Dict[str, Any]) -> bool:
        """Save lexicon data for user."""
        pass
    
    @abstractmethod
    async def save_protected_words(self, user_id: str, protected_words: Dict[str, Any]) -> bool:
        """Save protected words for user."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if loader connection is working."""
        pass