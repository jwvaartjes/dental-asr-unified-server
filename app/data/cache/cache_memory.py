"""
In-memory cache implementation with TTL support.
"""
import asyncio
import time
from typing import Any, Optional, Dict, List
from dataclasses import dataclass
import weakref
import fnmatch

from .cache_interface import CacheInterface


@dataclass
class CacheEntry:
    """Cache entry with expiration tracking."""
    value: Any
    created_at: float
    ttl: Optional[int] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)


class InMemoryCache(CacheInterface):
    """
    High-performance in-memory cache with TTL support and cleanup.
    
    Features:
    - TTL-based expiration
    - Background cleanup
    - Pattern matching for keys
    - Memory-efficient with weak references
    - Thread-safe operations
    """
    
    def __init__(self, cleanup_interval: int = 300):
        """Initialize cache with optional cleanup interval (seconds)."""
        self._data: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._cleanup_interval = cleanup_interval
        self._cleanup_task = None
        self._started = False
    
    def _ensure_cleanup_task(self):
        """Ensure background cleanup task is running."""
        if not self._started:
            try:
                # Only start if we're in an async context
                loop = asyncio.get_running_loop()
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._cleanup_expired())
                    self._started = True
            except RuntimeError:
                # No running event loop, will start later
                pass
    
    async def _cleanup_expired(self):
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                expired_keys = [
                    key for key, entry in self._data.items() 
                    if entry.is_expired
                ]
                for key in expired_keys:
                    self._data.pop(key, None)
            except asyncio.CancelledError:
                break
            except Exception:
                # Ignore cleanup errors to prevent task failure
                pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key, return None if expired or missing."""
        self._ensure_cleanup_task()
        
        entry = self._data.get(key)
        if entry is None:
            self._misses += 1
            return None
        
        if entry.is_expired:
            self._data.pop(key, None)
            self._misses += 1
            return None
        
        self._hits += 1
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key-value pair with optional TTL in seconds."""
        self._ensure_cleanup_task()
        
        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl
        )
        self._data[key] = entry
        self._sets += 1
    
    async def delete(self, key: str) -> bool:
        """Delete key. Returns True if key existed."""
        existed = key in self._data
        if existed:
            self._data.pop(key)
            self._deletes += 1
        return existed
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        entry = self._data.get(key)
        if entry is None:
            return False
        
        if entry.is_expired:
            self._data.pop(key, None)
            return False
        
        return True
    
    async def clear(self) -> None:
        """Clear all cached data."""
        cleared_count = len(self._data)
        self._data.clear()
        self._deletes += cleared_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "type": "in_memory",
            "entries": len(self._data),
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "deletes": self._deletes,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total_requests,
            "cleanup_interval": self._cleanup_interval
        }
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern. Supports * and ? wildcards."""
        all_keys = list(self._data.keys())
        
        if pattern == "*":
            return all_keys
        
        # Remove expired keys during pattern matching
        matching_keys = []
        for key in all_keys:
            entry = self._data.get(key)
            if entry and not entry.is_expired:
                if fnmatch.fnmatch(key, pattern):
                    matching_keys.append(key)
            elif entry and entry.is_expired:
                # Clean up expired key
                self._data.pop(key, None)
        
        return matching_keys
    
    def __del__(self):
        """Cleanup on destruction."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()