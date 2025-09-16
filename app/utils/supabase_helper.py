"""
Supabase helper utilities with fixed upsert functionality
"""
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SupabaseConfigManager:
    """Helper class with fixed upsert for config management"""

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def save_config_fixed(self, user_id: str, config_data: Dict[str, Any]) -> bool:
        """
        Save configuration with fixed upsert using on_conflict parameter.
        This fixes the duplicate key constraint error.
        """
        try:
            # Fixed upsert with explicit conflict resolution on user_id
            result = self.supabase.table("configs")\
                .upsert({
                    "user_id": user_id,
                    "config_data": config_data,
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="user_id")\
                .execute()

            logger.info(f"✅ Config saved successfully for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save config: {e}")
            return False

    def backup_config(self, user_id: str) -> Dict[str, Any]:
        """Create a backup of current config"""
        try:
            result = self.supabase.table("configs")\
                .select("config_data")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            if result.data:
                return {
                    "backup_info": {
                        "created_at": datetime.now().isoformat(),
                        "user_id": user_id,
                        "version": "1.0"
                    },
                    "config": result.data[0]["config_data"]
                }
            else:
                return {}

        except Exception as e:
            logger.error(f"❌ Failed to backup config: {e}")
            return {}