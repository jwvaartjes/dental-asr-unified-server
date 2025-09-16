#!/usr/bin/env python3
"""
Fix Supabase config upsert - specify the conflict resolution properly
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import SupabaseManager from the old workspace (as used by the loader)
sys.path.append('/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace')
from supabase_manager import SupabaseManager

def fixed_save_config(supabase_mgr, user_id: str, config_data: dict) -> bool:
    """Fixed save_config using proper upsert with conflict resolution"""
    try:
        print(f"🔧 Using fixed upsert method...")

        # Use upsert with explicit conflict resolution on user_id
        result = supabase_mgr.supabase.table("configs")\
            .upsert({
                "user_id": user_id,
                "config_data": config_data,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="user_id")\
            .execute()

        print(f"✅ Upsert successful: {len(result.data)} rows affected")
        return True

    except Exception as e:
        print(f"❌ Fixed upsert also failed: {e}")
        # Try UPDATE instead
        try:
            print(f"🔧 Trying direct UPDATE instead...")
            result = supabase_mgr.supabase.table("configs")\
                .update({
                    "config_data": config_data,
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("user_id", user_id)\
                .execute()

            print(f"✅ UPDATE successful: {len(result.data)} rows affected")
            return True

        except Exception as e2:
            print(f"❌ UPDATE also failed: {e2}")
            return False

def main():
    print("🔧 Fixed Supabase config upsert...")
    print("=" * 70)

    # Initialize SupabaseManager directly
    supabase_mgr = SupabaseManager()
    admin_id = supabase_mgr.get_admin_id()
    print(f"📋 Admin ID: {admin_id}")

    # Load the cleaned config we prepared earlier
    backup_file = "supabase_config_backup_20250914_160307.json"
    if not os.path.exists(backup_file):
        print(f"❌ Backup file {backup_file} not found!")
        return False

    with open(backup_file, 'r') as f:
        full_config = json.load(f)

    # Create the cleaned config (remove unused sections)
    unused_sections = [
        "ct2", "train", "transcription", "user_training",
        "buffering", "spsc_queue", "oversampling", "logging"
    ]

    cleaned_config = {k: v for k, v in full_config.items() if k not in unused_sections}

    print(f"📊 Cleaned config has {len(cleaned_config)} sections")
    print(f"🗑️  Removing sections: {unused_sections}")

    # Try the fixed save method
    try:
        success = fixed_save_config(supabase_mgr, admin_id, cleaned_config)

        if success:
            print("\n✅ Config saved successfully!")

            # Verify by loading it back
            print("\n🔍 Verifying saved config...")
            loaded_config = supabase_mgr.load_config(admin_id)

            if set(loaded_config.keys()) == set(cleaned_config.keys()):
                print("✅ Verification successful!")
                print(f"📊 Verified {len(loaded_config)} sections")
                return True
            else:
                print("❌ Verification failed - sections don't match")
                return False
        else:
            print("❌ Save failed")
            return False

    except Exception as e:
        print(f"💥 Exception: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Config cleanup completed!")
    else:
        print("\n❌ Config cleanup failed!")
        sys.exit(1)