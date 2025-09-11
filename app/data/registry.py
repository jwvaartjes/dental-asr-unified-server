"""
DataRegistry - Central orchestrator for pairing server data management.

Coordinates between cache and loader for efficient data access with fail-fast strategy.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .cache.cache_interface import CacheInterface
from .loaders.loader_interface import LoaderInterface

logger = logging.getLogger(__name__)


class DataRegistry:
    """
    Central data registry with cache + loader architecture.
    
    Features:
    - Automatic caching with TTL
    - Fail-fast if loader unavailable
    - Cache-first strategy for performance
    - Background data hydration
    - Cache invalidation support
    """
    
    def __init__(self, loader: LoaderInterface, cache: CacheInterface):
        """Initialize with loader and cache implementations."""
        self.loader = loader
        self.cache = cache
        self._default_ttl = 3600  # 1 hour cache TTL
        
        logger.info("🗄️  DataRegistry initialized")
    
    async def get_lexicon(self, user_id: str, force_reload: bool = False) -> Dict[str, Any]:
        """Get lexicon data with caching."""
        cache_key = f"lexicon:{user_id}"
        
        if not force_reload:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Lexicon cache hit for user {user_id}")
                return cached
        
        logger.debug(f"🔄 Loading lexicon from Supabase for user {user_id}")
        data = await self.loader.load_lexicon(user_id)
        
        if data:
            await self.cache.set(cache_key, data, self._default_ttl)
            logger.debug(f"💾 Cached lexicon for user {user_id}")
        
        return data
    
    async def get_custom_patterns(self, user_id: str, force_reload: bool = False) -> Dict[str, Any]:
        """Get custom patterns with caching."""
        cache_key = f"patterns:{user_id}"
        
        if not force_reload:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Patterns cache hit for user {user_id}")
                return cached
        
        logger.debug(f"🔄 Loading custom patterns from Supabase for user {user_id}")
        data = await self.loader.load_custom_patterns(user_id)
        
        if data:
            await self.cache.set(cache_key, data, self._default_ttl)
            logger.debug(f"💾 Cached patterns for user {user_id}")
        
        return data
    
    async def get_protected_words(self, user_id: str, force_reload: bool = False) -> Dict[str, Any]:
        """Get protected words with caching."""
        cache_key = f"protected:{user_id}"
        
        if not force_reload:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Protected words cache hit for user {user_id}")
                return cached
        
        logger.debug(f"🔄 Loading protected words from Supabase for user {user_id}")
        data = await self.loader.load_protected_words(user_id)
        
        if data:
            await self.cache.set(cache_key, data, self._default_ttl)
            logger.debug(f"💾 Cached protected words for user {user_id}")
        
        return data
    
    async def get_config(self, user_id: str, force_reload: bool = False) -> Dict[str, Any]:
        """Get configuration with caching."""
        cache_key = f"config:{user_id}"
        
        if not force_reload:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Config cache hit for user {user_id}")
                return cached
        
        logger.debug(f"🔄 Loading config from Supabase for user {user_id}")
        data = await self.loader.load_config(user_id)
        
        if data:
            await self.cache.set(cache_key, data, 1800)  # 30 min TTL for configs
            logger.debug(f"💾 Cached config for user {user_id}")
        
        return data
    
    async def save_config(self, user_id: str, config_data: Dict[str, Any]) -> bool:
        """Save configuration and invalidate cache."""
        success = await self.loader.save_config(user_id, config_data)
        
        if success:
            cache_key = f"config:{user_id}"
            await self.cache.delete(cache_key)
            logger.debug(f"🗑️  Invalidated config cache for user {user_id}")
        
        return success
    
    async def save_custom_patterns(self, user_id: str, patterns: Dict[str, Any]) -> bool:
        """Save custom patterns and invalidate cache."""
        success = await self.loader.save_custom_patterns(user_id, patterns)
        
        if success:
            cache_key = f"patterns:{user_id}"
            await self.cache.delete(cache_key)
            logger.debug(f"🗑️  Invalidated patterns cache for user {user_id}")
        
        return success
    
    async def save_lexicon(self, user_id: str, lexicon_data: Dict[str, Any]) -> bool:
        """Save lexicon and invalidate cache."""
        success = await self.loader.save_lexicon(user_id, lexicon_data)
        
        if success:
            cache_key = f"lexicon:{user_id}"
            await self.cache.delete(cache_key)
            logger.debug(f"🗑️  Invalidated lexicon cache for user {user_id}")
        
        return success
    
    async def save_protected_words(self, user_id: str, protected_words: Dict[str, Any]) -> bool:
        """Save protected words and invalidate cache."""
        success = await self.loader.save_protected_words(user_id, protected_words)
        
        if success:
            cache_key = f"protected:{user_id}"
            await self.cache.delete(cache_key)
            logger.debug(f"🗑️  Invalidated protected words cache for user {user_id}")
        
        return success
    
    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached data for a user."""
        cache_keys = [
            f"lexicon:{user_id}",
            f"patterns:{user_id}",
            f"protected:{user_id}",
            f"config:{user_id}"
        ]
        
        for key in cache_keys:
            await self.cache.delete(key)
        
        logger.info(f"🗑️  Invalidated all cache for user {user_id}")
    
    async def hydrate_cache(self, user_id: str) -> None:
        """Pre-load all user data into cache for faster access."""
        logger.info(f"🔄 Hydrating cache for user {user_id}")
        
        try:
            # Load all data types in parallel would be ideal, but keeping simple for now
            await self.get_lexicon(user_id, force_reload=True)
            await self.get_custom_patterns(user_id, force_reload=True)
            await self.get_protected_words(user_id, force_reload=True)
            await self.get_config(user_id, force_reload=True)
            
            logger.info(f"✅ Cache hydrated for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to hydrate cache for user {user_id}: {e}")
            raise
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = await self.cache.get_stats()
        stats["registry_info"] = {
            "default_ttl": self._default_ttl,
            "cache_type": type(self.cache).__name__,
            "loader_type": type(self.loader).__name__
        }
        return stats
    
    async def test_health(self) -> Dict[str, bool]:
        """Test health of cache and loader."""
        health = {}
        
        try:
            health["cache"] = await self.cache.exists("_health_test_key") is not None
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            health["cache"] = False
        
        try:
            health["loader"] = await self.loader.test_connection()
        except Exception as e:
            logger.error(f"Loader health check failed: {e}")
            health["loader"] = False
        
        health["overall"] = health["cache"] and health["loader"]
        return health