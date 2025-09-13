#!/usr/bin/env python3
"""
Add "bot verlies" -> "botverlies" variant mapping to Supabase
This fixes the failing test where "bot verlies" should normalize to "botverlies"
"""

import os
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def add_variant_mappings():
    """Add missing variant mappings for compound words with spaces/hyphens"""
    
    # Admin user UUID
    admin_user_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    try:
        # First, fetch current lexicon data
        result = supabase.table("lexicons").select("*").eq("user_id", admin_user_id).execute()
        
        if result.data:
            lexicon = result.data[0]
            lexicon_data = lexicon.get("lexicon_data", {})
            
            # Get or create variants section
            if "variants" not in lexicon_data:
                lexicon_data["variants"] = {}
            
            # Add the missing mappings for compound words
            # These should map the spaced/hyphenated forms to the compound form
            new_variants = {
                "bot verlies": "botverlies",
                "bot-verlies": "botverlies",
                "hand verlies": "handverlies",
                "hand-verlies": "handverlies",
                "been verlies": "beenverlies",
                "been-verlies": "beenverlies",
                "kaas verlies": "kaasverlies",
                "kaas-verlies": "kaasverlies",
                # Add more common dental compound terms
                "wortel kanaal": "wortelkanaal",
                "wortel-kanaal": "wortelkanaal",
                "tand vlees": "tandvlees",
                "tand-vlees": "tandvlees",
                "kaak gewricht": "kaakgewricht",
                "kaak-gewricht": "kaakgewricht",
                "mond bodem": "mondbodem",
                "mond-bodem": "mondbodem",
                "tand steen": "tandsteen",
                "tand-steen": "tandsteen",
            }
            
            # Merge with existing variants
            lexicon_data["variants"].update(new_variants)
            
            # Update the lexicon
            update_result = supabase.table("lexicons").update({
                "lexicon_data": lexicon_data
            }).eq("user_id", admin_user_id).execute()
            
            print("✅ Successfully added variant mappings!")
            print("\nAdded mappings:")
            for src, dst in new_variants.items():
                print(f"  '{src}' → '{dst}'")
                
        else:
            print("❌ No lexicon found for admin user")
            print("Creating new lexicon with variants...")
            
            # Create new lexicon with variants
            new_lexicon = {
                "user_id": admin_user_id,
                "lexicon_data": {
                    "variants": {
                        "bot verlies": "botverlies",
                        "bot-verlies": "botverlies",
                        "hand verlies": "handverlies",
                        "hand-verlies": "handverlies",
                        "been verlies": "beenverlies",
                        "been-verlies": "beenverlies",
                        "wortel kanaal": "wortelkanaal",
                        "wortel-kanaal": "wortelkanaal",
                        "tand vlees": "tandvlees",
                        "tand-vlees": "tandvlees",
                    }
                }
            }
            
            insert_result = supabase.table("lexicons").insert(new_lexicon).execute()
            print("✅ Successfully created lexicon with variant mappings!")
            
    except Exception as e:
        print(f"❌ Error updating lexicon: {str(e)}")
        sys.exit(1)

def verify_mappings():
    """Verify the mappings are correctly loaded"""
    admin_user_id = "76c7198e-710f-41dc-b26d-ce728571a546"
    
    try:
        result = supabase.table("lexicons").select("lexicon_data").eq("user_id", admin_user_id).execute()
        
        if result.data:
            variants = result.data[0].get("lexicon_data", {}).get("variants", {})
            
            print("\n📋 Current variant mappings:")
            test_keys = ["bot verlies", "bot-verlies", "botverlies"]
            
            for key in test_keys:
                if key in variants:
                    print(f"  ✅ '{key}' → '{variants[key]}'")
                else:
                    print(f"  ❌ '{key}' not found")
                    
    except Exception as e:
        print(f"❌ Error verifying mappings: {str(e)}")

if __name__ == "__main__":
    print("🔧 Adding variant mappings for compound words...")
    print("=" * 60)
    
    add_variant_mappings()
    verify_mappings()
    
    print("\n✨ Done! The 'bot verlies' → 'botverlies' normalization should now work.")
    print("Run the test to verify: python3 -m pytest unittests/normalization/test_normalization.py -k 'bot verlies'")