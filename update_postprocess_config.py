#!/usr/bin/env python3
"""
Update Supabase configuration to add postprocess punctuation removal settings.
"""

import os
import sys
import json
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the current directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def update_postprocess_config():
    """Update the configuration to include postprocess punctuation removal settings."""
    
    # Use the admin user's UUID from the database
    admin_user_id = "76c7198e-710f-41dc-b26d-ce728571a546"  # admin@dental-asr.com
    
    try:
        # Fetch current config for admin user
        result = supabase.table("configs").select("*").eq("user_id", admin_user_id).execute()
        
        if result.data:
            current_config = result.data[0]
            config_data = current_config.get("config_data", {})  # Note: column is config_data, not config
            
            # Add postprocess configuration with safer regex patterns
            config_data["postprocess"] = {
                "remove_exclamations": True,
                "remove_question_marks": True,
                "remove_semicolons": True,
                "remove_trailing_dots": False,  # Keep false by default to preserve decimal numbers
                "remove_trailing_word_commas": True,  # Enable for better normalization
                "remove_trailing_commas_eol": True,  # New safer flag - only removes commas at end of line
                "remove_sentence_dots": True  # New safer flag - removes sentence dots but preserves decimals
            }
            
            # Update the configuration
            update_result = supabase.table("configs").update({
                "config_data": config_data  # Note: column is config_data, not config
            }).eq("user_id", admin_user_id).execute()
            
            print("✅ Successfully updated postprocess configuration in Supabase!")
            print("\nNew postprocess configuration:")
            print(json.dumps(config_data.get("postprocess", {}), indent=2))
            
        else:
            print("❌ No configuration found for admin user")
            print("Creating new configuration...")
            
            # Create new config with postprocess settings
            new_config = {
                "user_id": admin_user_id,
                "config_data": {  # Note: column is config_data, not config
                    "postprocess": {
                        "remove_exclamations": True,
                        "remove_question_marks": True,
                        "remove_semicolons": True,
                        "remove_trailing_dots": False,  # Keep false by default to preserve decimal numbers
                        "remove_trailing_word_commas": True,  # Enable for better normalization
                        "remove_trailing_commas_eol": True,  # New safer flag - only removes commas at end of line
                        "remove_sentence_dots": True  # New safer flag - removes sentence dots but preserves decimals
                    }
                }
            }
            
            insert_result = supabase.table("configs").insert(new_config).execute()
            print("✅ Successfully created new configuration with postprocess settings!")
            
    except Exception as e:
        print(f"❌ Error updating configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Updating Supabase configuration with postprocess punctuation removal settings...")
    update_postprocess_config()