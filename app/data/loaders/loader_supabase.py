"""
Supabase loader implementation for pairing server data layer.
"""
import os
import logging
from typing import Dict, Any, Optional

from .loader_interface import LoaderInterface

logger = logging.getLogger(__name__)


class SupabaseLoader(LoaderInterface):
    """
    Supabase data loader with direct implementation.

    Uses Supabase directly without external dependencies.
    No fallbacks - fails fast if Supabase unavailable.
    """

    def __init__(self):
        """Initialize direct Supabase connection."""
        try:
            from supabase import create_client, Client

            logger.info("🔄 Initializing SupabaseLoader...")

            # Get Supabase credentials from environment
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")

            self.client: Client = create_client(supabase_url, supabase_key)
            self._admin_id = None
            self._super_admin_id = None

            # Test connection by getting admin user
            self._load_admin_ids()

            logger.info("✅ SupabaseLoader connected successfully")

        except Exception as e:
            logger.error(f"❌ CRITICAL: SupabaseLoader initialization failed: {e}")
            logger.error("❌ Check Supabase connection and credentials")
            raise RuntimeError(f"SupabaseLoader failed: {e}")

    def _load_admin_ids(self):
        """Load admin and super admin user IDs."""
        try:
            # Get first admin user
            admin_result = self.client.table("users").select("id").eq("role", "admin").order("created_at", desc=False).limit(1).execute()
            if admin_result.data:
                self._admin_id = admin_result.data[0]["id"]

            # Get super admin user
            super_admin_result = self.client.table("users").select("id").eq("role", "super_admin").limit(1).execute()
            if super_admin_result.data:
                self._super_admin_id = super_admin_result.data[0]["id"]

        except Exception as e:
            logger.warning(f"Failed to load admin IDs: {e}")
    
    async def load_lexicon(self, user_id: str) -> Dict[str, Any]:
        """Load lexicon data for user."""
        try:
            result = self.client.table("lexicons").select("lexicon_data").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            return result.data[0]["lexicon_data"] if result.data else {}
        except Exception as e:
            logger.error(f"❌ Failed to load lexicon for user {user_id}: {e}")
            raise

    async def load_custom_patterns(self, user_id: str) -> Dict[str, Any]:
        """Load custom patterns for user."""
        try:
            result = self.client.table("custom_patterns").select("patterns_data").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            return result.data[0]["patterns_data"] if result.data else {}
        except Exception as e:
            logger.error(f"❌ Failed to load custom patterns for user {user_id}: {e}")
            raise

    async def load_protected_words(self, user_id: str) -> Dict[str, Any]:
        """Load protected words for user."""
        try:
            result = self.client.table("protect_words").select("words_data").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            return result.data[0]["words_data"] if result.data else {}
        except Exception as e:
            logger.error(f"❌ Failed to load protected words for user {user_id}: {e}")
            raise

    async def load_config(self, user_id: str) -> Dict[str, Any]:
        """Load configuration for user."""
        try:
            result = self.client.table("configs").select("config_data").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            return result.data[0]["config_data"] if result.data else {}
        except Exception as e:
            logger.error(f"❌ Failed to load config for user {user_id}: {e}")
            raise

    async def save_config(self, user_id: str, config_data: Dict[str, Any]) -> bool:
        """Save configuration for user."""
        try:
            self.client.table("configs").upsert({
                "user_id": user_id,
                "config_data": config_data
            }).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save config for user {user_id}: {e}")
            return False

    async def save_custom_patterns(self, user_id: str, patterns: Dict[str, Any]) -> bool:
        """Save custom patterns for user."""
        try:
            self.client.table("custom_patterns").upsert({
                "user_id": user_id,
                "patterns_data": patterns
            }).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save custom patterns for user {user_id}: {e}")
            return False

    async def save_lexicon(self, user_id: str, lexicon_data: Dict[str, Any]) -> bool:
        """Save lexicon data for user."""
        try:
            self.client.table("lexicons").upsert({
                "user_id": user_id,
                "lexicon_data": lexicon_data
            }).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save lexicon for user {user_id}: {e}")
            return False

    async def save_protected_words(self, user_id: str, protected_words: Dict[str, Any]) -> bool:
        """Save protected words for user."""
        try:
            self.client.table("protect_words").upsert({
                "user_id": user_id,
                "words_data": protected_words
            }).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save protected words for user {user_id}: {e}")
            return False

    def get_admin_id(self) -> str:
        """Get admin user ID - prefer super admin if available."""
        # Always prefer super admin if available
        if self._super_admin_id:
            return self._super_admin_id
        return self._admin_id if self._admin_id else ""

    async def test_connection(self) -> bool:
        """Test if Supabase connection is working."""
        try:
            # Test by trying to get admin user
            admin_id = self.get_admin_id()
            return admin_id is not None and admin_id != ""
        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {e}")
            return False

    def get_super_admin_id(self) -> str:
        """Get super admin user ID."""
        return self._super_admin_id if self._super_admin_id else ""