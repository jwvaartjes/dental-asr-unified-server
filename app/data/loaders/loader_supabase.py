"""
Supabase loader implementation for pairing server data layer.
"""
import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .loader_interface import LoaderInterface

logger = logging.getLogger(__name__)


class SupabaseLoader(LoaderInterface):
    """
    Supabase data loader with fail-fast strategy.
    
    Uses the existing SupabaseManager from the main workspace.
    No fallbacks - fails fast if Supabase unavailable.
    """
    
    def __init__(self):
        """Initialize Supabase connection via existing manager."""
        try:
            # Import SupabaseManager from the same directory
            from .supabase_manager import SupabaseManager
            
            logger.info("🔄 Initializing SupabaseLoader...")
            self.supabase_mgr = SupabaseManager()
            logger.info("✅ SupabaseLoader connected successfully")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: SupabaseLoader initialization failed: {e}")
            logger.error("❌ Check Supabase connection and credentials")
            raise RuntimeError(f"SupabaseLoader failed: {e}")
    
    async def load_lexicon(self, user_id: str) -> Dict[str, Any]:
        """Load lexicon data for user."""
        try:
            return self.supabase_mgr.load_lexicon(user_id)
        except Exception as e:
            logger.error(f"❌ Failed to load lexicon for user {user_id}: {e}")
            raise
    
    async def load_custom_patterns(self, user_id: str) -> Dict[str, Any]:
        """Load custom patterns for user."""
        try:
            return self.supabase_mgr.load_custom_patterns(user_id)
        except Exception as e:
            logger.error(f"❌ Failed to load custom patterns for user {user_id}: {e}")
            raise
    
    async def load_protected_words(self, user_id: str) -> Dict[str, Any]:
        """Load protected words for user."""
        try:
            return self.supabase_mgr.load_protect_words(user_id)
        except Exception as e:
            logger.error(f"❌ Failed to load protected words for user {user_id}: {e}")
            raise
    
    async def load_config(self, user_id: str) -> Dict[str, Any]:
        """Load configuration for user."""
        try:
            return self.supabase_mgr.load_config(user_id)
        except Exception as e:
            logger.error(f"❌ Failed to load config for user {user_id}: {e}")
            raise
    
    async def save_config(self, user_id: str, config_data: Dict[str, Any]) -> bool:
        """Save configuration for user."""
        try:
            return self.supabase_mgr.save_config(user_id, config_data)
        except Exception as e:
            logger.error(f"❌ Failed to save config for user {user_id}: {e}")
            return False
    
    async def save_custom_patterns(self, user_id: str, patterns: Dict[str, Any]) -> bool:
        """Save custom patterns for user."""
        try:
            return self.supabase_mgr.save_custom_patterns(user_id, patterns)
        except Exception as e:
            logger.error(f"❌ Failed to save custom patterns for user {user_id}: {e}")
            return False
    
    async def save_lexicon(self, user_id: str, lexicon_data: Dict[str, Any]) -> bool:
        """Save lexicon data for user."""
        try:
            return self.supabase_mgr.save_lexicon(user_id, lexicon_data)
        except Exception as e:
            logger.error(f"❌ Failed to save lexicon for user {user_id}: {e}")
            return False
    
    async def save_protected_words(self, user_id: str, protected_words: Dict[str, Any]) -> bool:
        """Save protected words for user."""
        try:
            return self.supabase_mgr.save_protect_words(user_id, protected_words)
        except Exception as e:
            logger.error(f"❌ Failed to save protected words for user {user_id}: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test if Supabase connection is working."""
        try:
            # Test by trying to get admin user
            admin_id = self.supabase_mgr.get_admin_id()
            return admin_id is not None
        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {e}")
            return False
    
    def get_admin_id(self) -> str:
        """Get admin user ID."""
        return self.supabase_mgr.get_admin_id()
    
    def get_super_admin_id(self) -> str:
        """Get super admin user ID."""
        return self.supabase_mgr.get_super_admin_id()