#!/usr/bin/env python3
"""
Get VAD configuration from Supabase to see what settings were working well
"""

import asyncio
import json
from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader

async def get_vad_settings():
    """Get current VAD settings from Supabase"""

    print("🔍 RETRIEVING VAD SETTINGS FROM SUPABASE")
    print("=" * 50)

    try:
        # Setup data registry
        cache = InMemoryCache()
        loader = SupabaseLoader()
        registry = DataRegistry(loader=loader, cache=cache)

        # Get admin configuration
        admin_id = loader.get_admin_id()
        config_data = await registry.get_config(admin_id)

        if not config_data:
            print("❌ No configuration found in Supabase")
            return

        print(f"📊 Configuration loaded: {len(config_data)} sections")

        # Extract VAD settings
        vad_sections = {}
        for key in ['silero_vad', 'frontend_vad']:
            if key in config_data:
                vad_sections[key] = config_data[key]
                print(f"\n✅ Found {key}:")
                print(json.dumps(config_data[key], indent=2))
            else:
                print(f"\n❌ Missing {key} section")

        # Also check for any other VAD-related settings
        other_vad_keys = [k for k in config_data.keys() if 'vad' in k.lower()]
        if other_vad_keys:
            print(f"\n🔍 Other VAD-related keys found:")
            for key in other_vad_keys:
                if key not in vad_sections:
                    print(f"   {key}: {config_data[key]}")

        # Check OpenAI prompt settings too (might affect quality)
        if 'openai_prompt' in config_data:
            prompt = config_data['openai_prompt']
            print(f"\n🤖 OpenAI Prompt ({len(prompt)} chars):")
            print(f"   '{prompt[:100]}{'...' if len(prompt) > 100 else ''}'")
        else:
            print(f"\n⚠️  No OpenAI prompt found - this could affect quality!")

        # Save to file for easy reference
        vad_config = {
            'silero_vad': config_data.get('silero_vad', {}),
            'frontend_vad': config_data.get('frontend_vad', {}),
            'openai_prompt': config_data.get('openai_prompt', '')
        }

        with open('/tmp/vad_settings.json', 'w') as f:
            json.dump(vad_config, f, indent=2)

        print(f"\n💾 VAD settings saved to: /tmp/vad_settings.json")

    except Exception as e:
        print(f"❌ Error retrieving VAD settings: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(get_vad_settings())