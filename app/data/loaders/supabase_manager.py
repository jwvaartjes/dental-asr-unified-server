#!/usr/bin/env python3
"""
Supabase Manager - Cloud Storage voor Dental ASR System
NO FALLBACKS - FAIL FAST if Supabase unavailable
"""

import sys
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging
import random
import string

logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Cloud storage manager met fail-fast strategie
    - Geen lokale fallbacks
    - Duidelijke error messages bij problemen
    - Service role voor volledige toegang
    """
    
    def __init__(self):
        """Initialize Supabase client - FAILS if not available"""
        self.url = "https://ibgekvjupkscdnwbxdxr.supabase.co"
        self.service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImliZ2Vrdmp1cGtzY2Rud2J4ZHhyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTY3MjcxOSwiZXhwIjoyMDcxMjQ4NzE5fQ.EAcB-2qENjtZKc_KG9cqCm5weEAy75i12tBBi96NhNE"
        
        try:
            print("🔄 Initializing Supabase connection...")
            self.supabase: Client = create_client(self.url, self.service_key)
            
            # Test connection immediately
            print("🔄 Testing database connection...")
            test_result = self.supabase.table("users").select("id").limit(1).execute()
            
            # Get or create admin user
            admin_user = self._ensure_admin_user()
            print(f"✅ Supabase connected - Admin user: {admin_user['id']}")
            
            print("🎉 Supabase initialization successful!")
            print("🌐 SUPABASE CLOUD STORAGE - CONNECTED")
            
        except Exception as e:
            print(f"❌ CRITICAL: Supabase connection failed: {e}")
            print("❌ Check your internet connection and Supabase credentials")
            print("💥 SERVER STARTUP FAILED")
            sys.exit(1)  # FAIL FAST - No fallbacks!
    
    def _ensure_admin_user(self) -> Dict[str, Any]:
        """Ensure admin user exists - create if missing"""
        try:
            # Try to find existing admin
            admin_result = self.supabase.table("users")\
                .select("*")\
                .eq("role", "admin")\
                .limit(1)\
                .execute()
            
            if admin_result.data:
                return admin_result.data[0]
            
            # Create admin user if doesn't exist
            admin_data = {
                "id": str(uuid.uuid4()),
                "email": "admin@dental-asr.com",
                "name": "System Administrator",
                "role": "admin"
            }
            
            result = self.supabase.table("users")\
                .insert(admin_data)\
                .execute()
            
            print(f"✅ Created admin user: {admin_data['email']}")
            return result.data[0]
            
        except Exception as e:
            print(f"❌ CRITICAL: Admin user setup failed: {e}")
            print("❌ Verify database tables exist with: python create_all_tables.py")
            sys.exit(1)
    
    def get_admin_id(self) -> str:
        """Get admin user ID - returns first admin if multiple exist"""
        try:
            result = self.supabase.table("users")\
                .select("id")\
                .eq("role", "admin")\
                .order('created_at')\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]["id"]
            else:
                print(f"❌ CRITICAL: No admin users found")
                print("❌ Run: python migrate_to_supabase.py to setup database")
                sys.exit(1)
        except Exception as e:
            print(f"❌ CRITICAL: Admin user query failed: {e}")
            sys.exit(1)
    
    def get_super_admin_id(self) -> str:
        """Get the SUPER admin ID (original admin@dental-asr.com)"""
        # This is the original admin with all base lexicons
        SUPER_ADMIN_ID = "76c7198e-710f-41dc-b26d-ce728571a546"
        return SUPER_ADMIN_ID
    
    # ==============================================
    # LEXICON MANAGEMENT
    # ==============================================
    
    def load_lexicon(self, user_id: str) -> Dict[str, Any]:
        """Load hierarchical lexicon: super admin base + user additions"""
        try:
            super_admin_id = self.get_super_admin_id()
            
            # ALWAYS get super admin lexicon as base (has all 208 entries)
            super_admin_result = self.supabase.table("lexicons")\
                .select("lexicon_data")\
                .eq("user_id", super_admin_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .single()\
                .execute()
            
            base_lexicon = super_admin_result.data["lexicon_data"]
            
            # If requesting super admin data, return as-is
            if user_id == super_admin_id:
                return base_lexicon
            
            # For other users (including other admins), merge their additions
            try:
                # Check if user is admin
                user_result = self.supabase.table("users")\
                    .select("role")\
                    .eq("id", user_id)\
                    .single()\
                    .execute()
                
                is_admin = user_result.data.get("role") == "admin"
                
                # Get user's custom additions (if any)
                lexicon_result = self.supabase.table("lexicons")\
                    .select("custom_additions, lexicon_data")\
                    .eq("user_id", user_id)\
                    .single()\
                    .execute()
                
                if is_admin and lexicon_result.data.get("lexicon_data"):
                    # Admin users can have their own full lexicon
                    user_lexicon = lexicon_result.data["lexicon_data"]
                    # Merge with deduplication
                    return self._merge_lexicon_with_dedup(base_lexicon, user_lexicon)
                else:
                    # Regular users only have custom_additions
                    user_additions = lexicon_result.data.get("custom_additions", {})
                    return self._merge_lexicon_data(base_lexicon, user_additions)
                
            except Exception:
                # User has no custom data yet, return base
                return base_lexicon
            
        except Exception as e:
            print(f"❌ CRITICAL: Cannot load lexicon from Supabase: {e}")
            print(f"❌ Ensure super admin (ID: {self.get_super_admin_id()}) has lexicon data")
            raise  # NO FALLBACK - Let it crash!
    
    def save_lexicon(self, user_id: str, lexicon_data: Dict[str, Any]) -> bool:
        """Save lexicon - Admin saves base, users save additions"""
        try:
            admin_id = self.get_admin_id()
            
            if user_id == admin_id:
                # Admin can update base lexicon
                self.supabase.table("lexicons")\
                    .upsert({
                        "user_id": user_id,
                        "lexicon_data": lexicon_data,
                        "updated_at": datetime.now().isoformat()
                    })\
                    .execute()
                
                print(f"✅ Admin lexicon updated in Supabase")
            else:
                # Regular users only save additions
                admin_lexicon = self.load_lexicon(admin_id)
                additions = self._extract_user_additions(admin_lexicon, lexicon_data)
                
                self.supabase.table("lexicons")\
                    .upsert({
                        "user_id": user_id,
                        "custom_additions": additions,
                        "updated_at": datetime.now().isoformat()
                    })\
                    .execute()
                
                print(f"✅ User lexicon additions saved to Supabase")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Cannot save lexicon to Supabase: {e}")
            return False
    
    # ==============================================
    # CUSTOM PATTERNS MANAGEMENT
    # ==============================================
    
    def load_custom_patterns(self, user_id: str) -> Dict[str, Any]:
        """Load custom patterns for user"""
        try:
            admin_id = self.get_admin_id()
            
            # Get admin patterns as base
            admin_result = self.supabase.table("custom_patterns")\
                .select("patterns_data")\
                .eq("user_id", admin_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .single()\
                .execute()
            
            base_patterns = admin_result.data["patterns_data"]
            
            if user_id == admin_id:
                return base_patterns
            
            # Merge with user additions
            try:
                user_result = self.supabase.table("custom_patterns")\
                    .select("custom_additions")\
                    .eq("user_id", user_id)\
                    .single()\
                    .execute()
                
                user_additions = user_result.data.get("custom_additions", {})
                return self._merge_patterns_data(base_patterns, user_additions)
                
            except Exception:
                return base_patterns
            
        except Exception as e:
            print(f"❌ CRITICAL: Cannot load custom patterns: {e}")
            raise
    
    def save_custom_patterns(self, user_id: str, patterns_data: Dict[str, Any]) -> bool:
        """Save custom patterns"""
        try:
            admin_id = self.get_admin_id()
            
            if user_id == admin_id:
                self.supabase.table("custom_patterns")\
                    .upsert({
                        "user_id": user_id,
                        "patterns_data": patterns_data,
                        "updated_at": datetime.now().isoformat()
                    })\
                    .execute()
            else:
                admin_patterns = self.load_custom_patterns(admin_id)
                additions = self._extract_pattern_additions(admin_patterns, patterns_data)
                
                self.supabase.table("custom_patterns")\
                    .upsert({
                        "user_id": user_id,
                        "custom_additions": additions,
                        "updated_at": datetime.now().isoformat()
                    })\
                    .execute()
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Cannot save custom patterns: {e}")
            return False
    
    # ==============================================
    # PROTECTED WORDS MANAGEMENT
    # ==============================================
    
    def load_protect_words(self, user_id: str) -> Dict[str, Any]:
        """Load protected words - ALWAYS from super admin only"""
        try:
            # Only super admin can define protected words
            super_admin_id = self.get_super_admin_id()
            
            super_admin_result = self.supabase.table("protect_words")\
                .select("words_data")\
                .eq("user_id", super_admin_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .single()\
                .execute()
            
            # Always return super admin's protected words for ALL users
            return super_admin_result.data["words_data"]
            
        except Exception as e:
            print(f"❌ CRITICAL: Cannot load protected words from super admin: {e}")
            print(f"❌ Ensure super admin (ID: {self.get_super_admin_id()}) has protected words")
            raise
    
    def save_protect_words(self, user_id: str, words_data: Dict[str, Any]) -> bool:
        """Save protected words - only super admin can save"""
        try:
            super_admin_id = self.get_super_admin_id()
            
            # Only super admin can save protected words
            if user_id != super_admin_id:
                print(f"⚠️ Only super admin can save protected words")
                return False
            
            # For super admin, replace the entire record
            # Delete existing records
            self.supabase.table("protect_words")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()
            
            # Insert new record
            self.supabase.table("protect_words")\
                .insert({
                    "user_id": user_id,
                    "words_data": words_data,
                    "updated_at": datetime.now().isoformat()
                })\
                .execute()
            
            print(f"✅ Saved protected words for super admin")
            
            # Note: Non-super admins cannot save protected words
            # They can only read from super admin's protected words
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Cannot save protected words: {e}")
            print(f"❌ Details: {words_data}")
            return False
    
    # ==============================================
    # CONFIG MANAGEMENT
    # ==============================================
    
    def load_config(self, user_id: str) -> Dict[str, Any]:
        """Load configuration for user"""
        try:
            result = self.supabase.table("configs")\
                .select("config_data")\
                .eq("user_id", user_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .single()\
                .execute()
            
            return result.data["config_data"]
            
        except Exception as e:
            # Try admin config as fallback
            try:
                admin_id = self.get_admin_id()
                if user_id != admin_id:
                    return self.load_config(admin_id)
            except:
                pass
            
            print(f"❌ CRITICAL: Cannot load config: {e}")
            raise
    
    def save_config(self, user_id: str, config_data: Dict[str, Any]) -> bool:
        """Save configuration"""
        try:
            self.supabase.table("configs")\
                .upsert({
                    "user_id": user_id,
                    "config_data": config_data,
                    "updated_at": datetime.now().isoformat()
                })\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Cannot save config: {e}")
            return False
    
    # ==============================================
    # DATA MERGING UTILITIES
    # ==============================================
    
    def _merge_lexicon_data(self, base: Dict[str, Any], additions: Dict[str, Any]) -> Dict[str, Any]:
        """Merge admin lexicon with user additions (with deduplication)"""
        merged = base.copy()
        
        # Merge each category
        for category, terms in additions.items():
            if category in merged:
                # Add user terms to existing category with deduplication
                if isinstance(merged[category], list) and isinstance(terms, list):
                    # Use set for deduplication
                    existing = set(t.lower().strip() for t in merged[category])
                    for term in terms:
                        if term.lower().strip() not in existing:
                            merged[category].append(term)
                            existing.add(term.lower().strip())
                elif isinstance(merged[category], dict) and isinstance(terms, dict):
                    merged[category].update(terms)
            else:
                # New category from user
                merged[category] = terms
        
        return merged
    
    def _merge_lexicon_with_dedup(self, base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two full lexicons with deduplication (for admin users)"""
        merged = {}
        
        # Get all categories from both lexicons
        all_categories = set(base.keys()) | set(other.keys())
        
        for category in all_categories:
            # Start with base terms
            base_terms = base.get(category, [])
            other_terms = other.get(category, [])
            
            if isinstance(base_terms, list) and isinstance(other_terms, list):
                # Use dict for deduplication while preserving order
                seen = {}
                merged_terms = []
                
                # Add base terms first (higher priority)
                for term in base_terms:
                    normalized = term.lower().strip()
                    if normalized not in seen:
                        seen[normalized] = True
                        merged_terms.append(term)
                
                # Add other terms if not duplicates
                for term in other_terms:
                    normalized = term.lower().strip()
                    if normalized not in seen:
                        seen[normalized] = True
                        merged_terms.append(term)
                
                if merged_terms:  # Only add category if it has terms
                    merged[category] = merged_terms
            elif base_terms:  # If only base has terms
                merged[category] = base_terms
            elif other_terms:  # If only other has terms
                merged[category] = other_terms
        
        return merged
    
    def _merge_patterns_data(self, base: Dict[str, Any], additions: Dict[str, Any]) -> Dict[str, Any]:
        """Merge admin patterns with user additions"""
        merged = base.copy()
        
        for pattern_type in ["direct_mappings", "multi_word_mappings"]:
            if pattern_type in additions:
                if pattern_type not in merged:
                    merged[pattern_type] = {}
                merged[pattern_type].update(additions[pattern_type])
        
        return merged
    
    def _merge_words_data(self, base: Dict[str, Any], additions: Dict[str, Any]) -> Dict[str, Any]:
        """Merge admin protected words with user additions"""
        merged = base.copy()
        
        if "categories" in additions:
            if "categories" not in merged:
                merged["categories"] = {}
            
            for category, data in additions["categories"].items():
                if category in merged["categories"]:
                    # Merge words in existing category
                    if "words" in data and "words" in merged["categories"][category]:
                        merged["categories"][category]["words"].extend(data["words"])
                else:
                    # New category
                    merged["categories"][category] = data
        
        return merged
    
    def _extract_user_additions(self, admin_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only the additions user made vs admin data"""
        additions = {}
        
        for category, terms in user_data.items():
            if category not in admin_data:
                # Completely new category
                additions[category] = terms
            elif isinstance(terms, list) and isinstance(admin_data[category], list):
                # Find new terms in list
                new_terms = [term for term in terms if term not in admin_data[category]]
                if new_terms:
                    additions[category] = new_terms
        
        return additions
    
    def _extract_pattern_additions(self, admin_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pattern additions"""
        additions = {}
        
        for pattern_type in ["direct_mappings", "multi_word_mappings"]:
            if pattern_type in user_data:
                admin_patterns = admin_data.get(pattern_type, {})
                user_patterns = user_data[pattern_type]
                
                new_patterns = {k: v for k, v in user_patterns.items() if k not in admin_patterns}
                if new_patterns:
                    if pattern_type not in additions:
                        additions[pattern_type] = {}
                    additions[pattern_type].update(new_patterns)
        
        return additions
    
    def _extract_words_additions(self, admin_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract protected words additions"""
        additions = {}
        
        if "categories" in user_data:
            admin_categories = admin_data.get("categories", {})
            user_categories = user_data["categories"]
            
            for category, data in user_categories.items():
                if category not in admin_categories:
                    # New category
                    if "categories" not in additions:
                        additions["categories"] = {}
                    additions["categories"][category] = data
                elif "words" in data:
                    # Check for new words in existing category
                    admin_words = admin_categories[category].get("words", [])
                    new_words = [word for word in data["words"] if word not in admin_words]
                    if new_words:
                        if "categories" not in additions:
                            additions["categories"] = {}
                        additions["categories"][category] = {
                            "description": data.get("description", ""),
                            "words": new_words
                        }
        
        return additions
    
    # ==============================================
    # STORAGE MANAGEMENT FOR TRAINING AUDIO
    # ==============================================
    
    def ensure_training_bucket(self) -> bool:
        """Ensure training-audio bucket exists"""
        try:
            # Check if bucket exists
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if 'training-audio' not in bucket_names:
                # Create bucket with public access for authenticated users
                self.supabase.storage.create_bucket(
                    'training-audio',
                    options={
                        'public': False,  # Require authentication
                        'file_size_limit': 52428800,  # 50MB limit
                        'allowed_mime_types': ['audio/wav', 'audio/x-wav', 'audio/wave']
                    }
                )
                logger.info("✅ Created training-audio bucket")
            else:
                logger.info("✅ Training-audio bucket exists")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to ensure training bucket: {e}")
            return False
    
    def upload_training_audio(self, file_data: bytes, file_path: str) -> Optional[str]:
        """
        Upload audio file to Supabase storage
        
        Args:
            file_data: WAV file bytes
            file_path: Path in bucket (e.g., 'user_id/session_id/filename.wav')
        
        Returns:
            Storage path if successful, None otherwise
        """
        try:
            # Ensure bucket exists
            if not self.ensure_training_bucket():
                raise Exception("Failed to ensure training bucket exists")
            
            # Check if file already exists and remove it if so
            try:
                existing = self.supabase.storage.from_('training-audio').list(file_path)
                if existing:
                    logger.info(f"File already exists, replacing: {file_path}")
                    self.supabase.storage.from_('training-audio').remove([file_path])
            except:
                pass  # File doesn't exist, which is fine
            
            # Upload file with upsert option
            result = self.supabase.storage.from_('training-audio').upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": "audio/wav",
                    "upsert": "true"  # Allow overwriting if exists
                }
            )
            
            logger.info(f"✅ Uploaded audio to Supabase: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Failed to upload audio: {e}")
            logger.error(f"   File path: {file_path}")
            logger.error(f"   File size: {len(file_data)} bytes")
            # Try to provide more detailed error info
            if hasattr(e, 'response'):
                logger.error(f"   Response: {getattr(e, 'response', 'N/A')}")
            return None
    
    def get_training_audio_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get signed URL for training audio file
        
        Args:
            file_path: Path in bucket
            expires_in: URL expiration in seconds (default 1 hour)
        
        Returns:
            Signed URL if successful, None otherwise
        """
        try:
            result = self.supabase.storage.from_('training-audio').create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            
            if result and 'signedURL' in result:
                return result['signedURL']
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get audio URL: {e}")
            return None
    
    def delete_training_audio(self, file_path: str) -> bool:
        """
        Delete audio file from Supabase storage
        
        Args:
            file_path: Path in bucket
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.storage.from_('training-audio').remove([file_path])
            logger.info(f"✅ Deleted audio from Supabase: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete audio: {e}")
            return False
    
    def download_training_audio(self, file_path: str) -> Optional[bytes]:
        """
        Download audio file from Supabase storage
        
        Args:
            file_path: Path in bucket
        
        Returns:
            File bytes if successful, None otherwise
        """
        try:
            result = self.supabase.storage.from_('training-audio').download(file_path)
            if result:
                return result
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to download audio: {e}")
            return None
    
    # ============================================================================
    # DEVICE PAIRING METHODS
    # ============================================================================
    
    def generate_pairing_code(self) -> str:
        """Generate a unique 6-digit pairing code"""
        while True:
            # Generate 6-digit code
            code = ''.join(random.choices(string.digits, k=6))
            
            # Check if code already exists
            result = self.supabase.table('device_pairs')\
                .select('id')\
                .eq('code', code)\
                .execute()
            
            if not result.data:
                return code
    
    def create_device_pair(self, desktop_session_id: str) -> Dict[str, Any]:
        """Create a new device pairing with 6-digit code"""
        try:
            code = self.generate_pairing_code()
            expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
            
            data = {
                'code': code,
                'desktop_session_id': desktop_session_id,
                'status': 'pending',
                'expires_at': expires_at,
                'settings': {}
            }
            
            result = self.supabase.table('device_pairs')\
                .insert(data)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Created device pair with code: {code}")
                return {
                    'code': code,
                    'channel_id': f'pair-{code}',  # Add channel ID for WebSocket joining
                    'expires_at': expires_at,
                    'status': 'success'
                }
            else:
                raise Exception("Failed to create device pair")
                
        except Exception as e:
            logger.error(f"❌ Failed to create device pair: {e}")
            raise
    
    def pair_mobile_device(self, code: str, mobile_session_id: str) -> Dict[str, Any]:
        """Pair a mobile device using the 6-digit code"""
        try:
            # First check if code exists and is not expired
            result = self.supabase.table('device_pairs')\
                .select('*')\
                .eq('code', code)\
                .single()\
                .execute()
            
            if not result.data:
                return {'status': 'error', 'success': False, 'message': 'Invalid code'}
            
            pair = result.data
            
            # Check if expired
            expires_at = datetime.fromisoformat(pair['expires_at'].replace('Z', '+00:00'))
            if expires_at < datetime.now(expires_at.tzinfo):
                # Update status to expired
                self.supabase.table('device_pairs')\
                    .update({'status': 'expired'})\
                    .eq('id', pair['id'])\
                    .execute()
                return {'status': 'error', 'success': False, 'message': 'Code expired'}
            
            # Update with mobile session ID and status
            update_result = self.supabase.table('device_pairs')\
                .update({
                    'mobile_session_id': mobile_session_id,
                    'status': 'connected',
                    'last_activity': datetime.now().isoformat()
                })\
                .eq('id', pair['id'])\
                .execute()
            
            if update_result.data:
                logger.info(f"✅ Paired mobile device with code: {code}")
                return {
                    'status': 'success',
                    'success': True,  # Client checks for this boolean
                    'channelId': f'pair-{code}',  # Add the missing channelId for WebSocket channel
                    'desktop_session_id': pair['desktop_session_id'],
                    'mobile_session_id': mobile_session_id,
                    'pair_id': pair['id']
                }
            else:
                raise Exception("Failed to update device pair")
                
        except Exception as e:
            logger.error(f"❌ Failed to pair mobile device: {e}")
            return {'status': 'error', 'success': False, 'message': str(e)}
    
    def get_pair_status(self, code: str) -> Dict[str, Any]:
        """Get the status of a device pairing"""
        try:
            result = self.supabase.table('device_pairs')\
                .select('*')\
                .eq('code', code)\
                .single()\
                .execute()
            
            if not result.data:
                return {'status': 'not_found'}
            
            pair = result.data
            
            # Check if expired
            expires_at = datetime.fromisoformat(pair['expires_at'].replace('Z', '+00:00'))
            if expires_at < datetime.now(expires_at.tzinfo):
                # Update status to expired
                self.supabase.table('device_pairs')\
                    .update({'status': 'expired'})\
                    .eq('id', pair['id'])\
                    .execute()
                pair['status'] = 'expired'
            
            return {
                'status': pair['status'],
                'success': True,
                'channelId': f'pair-{code}' if pair['status'] == 'connected' else None,
                'desktop_connected': bool(pair.get('desktop_session_id')),
                'mobile_connected': bool(pair.get('mobile_session_id')),
                'settings': pair.get('settings', {})
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get pair status: {e}")
            return {'status': 'error', 'success': False, 'message': str(e)}
    
    def sync_device_settings(self, code: str, session_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Sync settings between paired devices"""
        try:
            # Get the device pair
            result = self.supabase.table('device_pairs')\
                .select('*')\
                .eq('code', code)\
                .single()\
                .execute()
            
            if not result.data:
                return {'status': 'error', 'success': False, 'message': 'Invalid code'}
            
            pair = result.data
            
            # Verify session_id matches either desktop or mobile
            if session_id not in [pair.get('desktop_session_id'), pair.get('mobile_session_id')]:
                return {'status': 'error', 'message': 'Session not authorized'}
            
            # Update settings
            update_result = self.supabase.table('device_pairs')\
                .update({
                    'settings': settings,
                    'last_activity': datetime.now().isoformat()
                })\
                .eq('id', pair['id'])\
                .execute()
            
            if update_result.data:
                synced_to = []
                if pair.get('desktop_session_id'):
                    synced_to.append('desktop')
                if pair.get('mobile_session_id'):
                    synced_to.append('mobile')
                
                logger.info(f"✅ Synced settings for code: {code}")
                return {
                    'status': 'success',
                    'synced_to': synced_to
                }
            else:
                raise Exception("Failed to update settings")
                
        except Exception as e:
            logger.error(f"❌ Failed to sync settings: {e}")
            return {'status': 'error', 'success': False, 'message': str(e)}
    
    def cleanup_expired_pairs(self) -> int:
        """Clean up expired device pairs"""
        try:
            # Mark expired pairs
            now = datetime.now().isoformat()
            expired_result = self.supabase.table('device_pairs')\
                .update({'status': 'expired'})\
                .lt('expires_at', now)\
                .neq('status', 'expired')\
                .execute()
            
            # Delete very old pairs (older than 1 hour)
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            delete_result = self.supabase.table('device_pairs')\
                .delete()\
                .lt('expires_at', one_hour_ago)\
                .execute()
            
            cleaned = len(delete_result.data) if delete_result.data else 0
            logger.info(f"🧹 Cleaned up {cleaned} expired device pairs")
            return cleaned
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired pairs: {e}")
            return 0


# Test connection on import
if __name__ == "__main__":
    print("🧪 Testing Supabase connection...")
    manager = SupabaseManager()
    print("✅ Supabase Manager test successful!")