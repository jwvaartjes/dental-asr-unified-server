#!/usr/bin/env python3
"""
Fix Supabase config save by directly using SupabaseManager
"""

import asyncio
import sys
import os
import json
from pprint import pprint

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import SupabaseManager from the old workspace (as used by the loader)
sys.path.append('/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace')
from supabase_manager import SupabaseManager

def main():
    print("🔧 Direct Supabase config save fix...")
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

    print(f"📊 Original config sections: {len(full_config)}")
    print(f"📊 Cleaned config sections: {len(cleaned_config)}")
    print(f"🗑️  Removed sections: {unused_sections}")

    print("\n🔍 Remaining sections:")
    for section in sorted(cleaned_config.keys()):
        print(f"   ✅ {section}")

    # Try to save directly with SupabaseManager
    try:
        print(f"\n💾 Saving cleaned config directly...")
        success = supabase_mgr.save_config(admin_id, cleaned_config)

        if success:
            print("✅ Config saved successfully!")

            # Verify by loading it back
            print("\n🔍 Verifying saved config...")
            loaded_config = supabase_mgr.load_config(admin_id)

            if set(loaded_config.keys()) == set(cleaned_config.keys()):
                print("✅ Verification successful - config matches!")
                print(f"📊 Verified sections: {sorted(loaded_config.keys())}")
                return True
            else:
                print("❌ Verification failed - sections don't match")
                print(f"   Expected: {sorted(cleaned_config.keys())}")
                print(f"   Actual: {sorted(loaded_config.keys())}")
                return False
        else:
            print("❌ Save failed")
            return False

    except Exception as e:
        print(f"💥 Exception during save: {e}")
        print(f"   Exception type: {type(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Config cleanup completed successfully!")
    else:
        print("\n❌ Config cleanup failed!")
        sys.exit(1)