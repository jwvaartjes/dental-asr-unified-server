"""
Consultation Template Service
"""
# Fixed Supabase client access
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing consultation templates"""

    def __init__(self, supabase_mgr):
        self.supabase_mgr = supabase_mgr

    async def create_template(self, user_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new consultation template"""
        try:
            template_record = {
                "id": str(uuid4()),
                "user_id": user_id,
                "template_name": template_data["template_name"],
                "template_type": template_data.get("template_type", "general"),
                "description": template_data.get("description", ""),
                "is_active": False,  # New templates are not active by default
                "is_default": template_data.get("is_default", False),
                "settings": template_data["settings"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # If this is being set as default, unset other defaults for this user
            if template_data.get("is_default", False):
                await self._unset_default_templates(user_id)

            # Use the existing supabase manager pattern
            result = self.supabase_mgr.client.table("consultation_templates")\
                .insert(template_record)\
                .execute()

            if result.data:
                logger.info(f"✅ Consultation template '{template_data['template_name']}' created")
                return {"success": True, "template": result.data[0]}
            else:
                raise Exception("Failed to create template - no data returned")

        except Exception as e:
            logger.error(f"❌ Failed to create consultation template: {e}")
            return {"success": False, "error": str(e)}

    async def get_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all consultation templates for user"""
        try:
            result = self.supabase_mgr.client.table("consultation_templates")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("template_name")\
                .execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"❌ Failed to load consultation templates: {e}")
            return []

    async def get_template(self, template_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific consultation template"""
        try:
            result = self.supabase_mgr.client.table("consultation_templates")\
                .select("*")\
                .eq("id", template_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"❌ Failed to load consultation template {template_id}: {e}")
            return None

    async def update_template(self, template_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update consultation template"""
        try:
            updates["updated_at"] = datetime.now().isoformat()

            # If this is being set as default, unset other defaults for this user
            if updates.get("is_default", False):
                await self._unset_default_templates(user_id)

            result = self.supabase_mgr.client.table("consultation_templates")\
                .update(updates)\
                .eq("id", template_id)\
                .eq("user_id", user_id)\
                .execute()

            return result.data is not None

        except Exception as e:
            logger.error(f"❌ Failed to update consultation template: {e}")
            return False

    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """Delete consultation template"""
        try:
            result = self.supabase_mgr.client.table("consultation_templates")\
                .delete()\
                .eq("id", template_id)\
                .eq("user_id", user_id)\
                .execute()

            logger.info(f"✅ Consultation template deleted")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete consultation template: {e}")
            return False

    async def get_active_template(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the active consultation template for user"""
        try:
            # First try to get the currently active template
            result = self.supabase_mgr.client.table("consultation_templates")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .single()\
                .execute()

            if result.data:
                return result.data

            # Fallback to default template
            result = self.supabase_mgr.client.table("consultation_templates")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_default", True)\
                .single()\
                .execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"❌ Failed to get active consultation template: {e}")
            return None

    async def set_active_template(self, template_id: str, user_id: str) -> bool:
        """Set template as active for user"""
        try:
            # Deactivate all templates for this user
            self.supabase_mgr.client.table("consultation_templates")\
                .update({"is_active": False})\
                .eq("user_id", user_id)\
                .execute()

            # Activate the specified template
            result = self.supabase_mgr.client.table("consultation_templates")\
                .update({"is_active": True, "updated_at": datetime.now().isoformat()})\
                .eq("id", template_id)\
                .eq("user_id", user_id)\
                .execute()

            return result.data is not None

        except Exception as e:
            logger.error(f"❌ Failed to set active template: {e}")
            return False

    async def duplicate_template(self, template_id: str, user_id: str, new_name: str) -> Dict[str, Any]:
        """Duplicate an existing template with a new name"""
        try:
            # Get the existing template
            original = await self.get_template(template_id, user_id)
            if not original:
                return {"success": False, "error": "Template not found"}

            # Create new template data
            new_template_data = {
                "template_name": new_name,
                "template_type": original["template_type"],
                "description": f"Copy of {original['template_name']}",
                "is_default": False,  # Copies are never default
                "settings": original["settings"]
            }

            return await self.create_template(user_id, new_template_data)

        except Exception as e:
            logger.error(f"❌ Failed to duplicate template: {e}")
            return {"success": False, "error": str(e)}

    async def get_default_settings(self, user_id: str) -> Dict[str, Any]:
        """Get default settings from current config system"""
        try:
            # Import here to avoid circular imports
            from ..data.registry import DataRegistry
            from ..deps import get_data_registry

            data_registry = get_data_registry()
            config = await data_registry.get_config(user_id)

            # Map current config to template settings format
            return {
                "prompt_config": {
                    "system_prompt": config.get("openai_prompt", "Dit is een Nederlandse tandheelkundige consultatie."),
                    "include_base_prompt": True,
                    "additional_context": ""
                },
                "ai_model_config": {
                    "provider": "openai",
                    "model_name": "gpt-4o-transcribe",
                    "language": "nl",
                    "temperature": 0.2
                },
                "vad_config": {
                    "enable_silero": True,
                    "silero_threshold": config.get("silero_vad", {}).get("positive_speech_threshold", 0.9),
                    "enable_frontend_vad": False,
                    "silence_duration": 1.5
                },
                "lexicon_config": {
                    "enabled_categories": [],  # All categories enabled by default
                    "disabled_categories": [],
                    "use_custom_patterns": True,
                    "use_protected_words": True,
                    "custom_additions": {}
                },
                "normalization_config": {
                    "enable_phonetic": config.get("matching", {}).get("phonetic_enabled", True),
                    "phonetic_threshold": config.get("matching", {}).get("fuzzy_threshold", 0.84),
                    "enable_element_parsing": True,
                    "enable_variant_generation": True
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to get default settings: {e}")
            # Return sensible defaults if config fails
            return {
                "prompt_config": {
                    "system_prompt": "Dit is een Nederlandse tandheelkundige consultatie. Gebruik correcte tandheelkundige terminologie.",
                    "include_base_prompt": True,
                    "additional_context": ""
                },
                "ai_model_config": {
                    "provider": "openai",
                    "model_name": "gpt-4o-transcribe",
                    "language": "nl",
                    "temperature": 0.2
                },
                "vad_config": {
                    "enable_silero": True,
                    "silero_threshold": 0.9,
                    "enable_frontend_vad": False,
                    "silence_duration": 1.5
                },
                "lexicon_config": {
                    "enabled_categories": [],
                    "disabled_categories": [],
                    "use_custom_patterns": True,
                    "use_protected_words": True,
                    "custom_additions": {}
                },
                "normalization_config": {
                    "enable_phonetic": True,
                    "phonetic_threshold": 0.84,
                    "enable_element_parsing": True,
                    "enable_variant_generation": True
                }
            }

    async def _unset_default_templates(self, user_id: str):
        """Helper to unset all default templates for a user"""
        try:
            self.supabase_mgr.client.table("consultation_templates")\
                .update({"is_default": False})\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            logger.warning(f"Failed to unset default templates: {e}")

    async def ensure_default_template(self, user_id: str) -> Dict[str, Any]:
        """Ensure user has a default 'General' template"""
        try:
            # Check if user already has templates
            templates = await self.get_templates(user_id)
            if templates:
                # User already has templates
                return {"success": True, "message": "User already has templates"}

            # Create default General template
            default_settings = await self.get_default_settings(user_id)
            default_template = {
                "template_name": "General",
                "template_type": "general",
                "description": "Default general consultation template",
                "is_default": True,
                "settings": default_settings
            }

            result = await self.create_template(user_id, default_template)
            if result["success"]:
                # Also set it as active
                template_id = result["template"]["id"]
                await self.set_active_template(template_id, user_id)
                return {"success": True, "message": "Default template created", "template": result["template"]}
            else:
                return result

        except Exception as e:
            logger.error(f"❌ Failed to ensure default template: {e}")
            return {"success": False, "error": str(e)}