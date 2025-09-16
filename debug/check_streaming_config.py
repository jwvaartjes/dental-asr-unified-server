#!/usr/bin/env python3
"""
Debug script to check what streaming configuration is actually being used
"""

import asyncio
from app.ai.streaming_transcriber import AudioBuffer

async def check_config():
    """Check the actual streaming configuration values"""

    print("🔍 STREAMING CONFIGURATION CHECK")
    print("=" * 50)

    # Check AudioBuffer defaults
    buffer = AudioBuffer()
    print(f"📊 AudioBuffer Default Settings:")
    print(f"   file_chunk_threshold: {buffer.file_chunk_threshold} bytes")
    print(f"   chunk_accumulation_count: {buffer.chunk_accumulation_count}")
    print(f"   max_duration_ms: {buffer.max_duration_ms} ms")
    print(f"   min_duration_ms: {buffer.min_duration_ms} ms")
    print(f"   sample_rate: {buffer.sample_rate} Hz")

    # Calculate timing info
    chunk_duration_ms = (buffer.file_chunk_threshold / 2) / (buffer.sample_rate / 1000)
    max_buffer_time = chunk_duration_ms * buffer.chunk_accumulation_count

    print(f"\n⏱️  Timing Analysis:")
    print(f"   Chunk duration: {chunk_duration_ms:.1f}ms")
    print(f"   Max buffer time: {max_buffer_time:.1f}ms")
    print(f"   Safety timeout: {buffer.max_duration_ms}ms")

    # Expected vs actual
    print(f"\n✅ Expected (Optimized):")
    print(f"   file_chunk_threshold: 2048 bytes (64ms)")
    print(f"   chunk_accumulation_count: 3")
    print(f"   max_duration_ms: 500ms")

    if (buffer.file_chunk_threshold == 2048 and
        buffer.chunk_accumulation_count == 3 and
        buffer.max_duration_ms == 500):
        print(f"\n🎯 SUCCESS: Optimizations are active!")
    else:
        print(f"\n❌ ISSUE: Still using old settings!")
        print(f"   Server may need restart to pick up new defaults")

if __name__ == "__main__":
    asyncio.run(check_config())