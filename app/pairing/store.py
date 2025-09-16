"""
Storage abstraction for pairing data.
Provides interface and implementations for in-memory and Redis storage.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Set
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PairingStore(ABC):
    """Abstract interface for pairing data storage."""
    
    @abstractmethod
    async def store_pairing(self, code: str, desktop_session_id: str, ttl: int = 3600,
                           desktop_auth_info: Optional[Dict] = None) -> bool:
        """Store a pairing code with desktop session ID and optional auth info."""
        pass
    
    @abstractmethod
    async def get_pairing(self, code: str) -> Optional[str]:
        """Get desktop session ID for a pairing code."""
        pass
    
    @abstractmethod
    async def consume_pairing(self, code: str) -> Optional[str]:
        """Get and remove pairing code (one-time use)."""
        pass

    @abstractmethod
    async def get_pairing_with_auth(self, code: str) -> Optional[Dict]:
        """Get desktop session ID and auth info for a pairing code."""
        pass
    
    @abstractmethod
    async def add_to_channel(self, channel_id: str, client_id: str, device_type: str) -> bool:
        """Add a client to a channel."""
        pass
    
    @abstractmethod
    async def get_channel_clients(self, channel_id: str) -> Dict[str, str]:
        """Get all clients in a channel."""
        pass
    
    @abstractmethod
    async def remove_from_channel(self, channel_id: str, client_id: str) -> bool:
        """Remove a client from a channel."""
        pass


class InMemoryPairingStore(PairingStore):
    """In-memory implementation for development/testing."""
    
    def __init__(self):
        self.pairings: Dict[str, tuple[str, datetime, Optional[Dict]]] = {}  # code -> (desktop_id, expiry, auth_info)
        self.channels: Dict[str, Dict[str, str]] = {}  # channel_id -> {client_id: device_type}
    
    async def store_pairing(self, code: str, desktop_session_id: str, ttl: int = 3600,
                           desktop_auth_info: Optional[Dict] = None) -> bool:
        """Store pairing with expiry and optional auth info."""
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self.pairings[code] = (desktop_session_id, expiry, desktop_auth_info)
        logger.info(f"Stored pairing {code} -> {desktop_session_id} with auth: {bool(desktop_auth_info)} (expires: {expiry})")
        return True
    
    async def get_pairing(self, code: str) -> Optional[str]:
        """Get desktop session ID if not expired."""
        if code in self.pairings:
            desktop_id, expiry, _ = self.pairings[code]
            if datetime.utcnow() < expiry:
                return desktop_id
            else:
                # Clean up expired pairing
                del self.pairings[code]
                logger.info(f"Pairing {code} expired")
        return None
    
    async def consume_pairing(self, code: str) -> Optional[str]:
        """Get and remove pairing (one-time use)."""
        desktop_id = await self.get_pairing(code)
        if desktop_id and code in self.pairings:
            del self.pairings[code]
            logger.info(f"Consumed pairing {code}")
        return desktop_id

    async def get_pairing_with_auth(self, code: str) -> Optional[Dict]:
        """Get desktop session ID and auth info if not expired."""
        if code in self.pairings:
            desktop_id, expiry, auth_info = self.pairings[code]
            if datetime.utcnow() < expiry:
                return {
                    "desktop_session_id": desktop_id,
                    "auth_info": auth_info or {}
                }
            else:
                # Clean up expired pairing
                del self.pairings[code]
                logger.info(f"Pairing {code} expired")
        return None

    async def add_to_channel(self, channel_id: str, client_id: str, device_type: str) -> bool:
        """Add client to channel."""
        if channel_id not in self.channels:
            self.channels[channel_id] = {}
        self.channels[channel_id][client_id] = device_type
        logger.info(f"Added {client_id} ({device_type}) to channel {channel_id}")
        return True
    
    async def get_channel_clients(self, channel_id: str) -> Dict[str, str]:
        """Get all clients in channel."""
        return self.channels.get(channel_id, {})
    
    async def remove_from_channel(self, channel_id: str, client_id: str) -> bool:
        """Remove client from channel."""
        if channel_id in self.channels and client_id in self.channels[channel_id]:
            del self.channels[channel_id][client_id]
            if not self.channels[channel_id]:
                del self.channels[channel_id]
            logger.info(f"Removed {client_id} from channel {channel_id}")
            return True
        return False
    
    def cleanup_expired(self):
        """Remove expired pairings."""
        now = datetime.utcnow()
        expired = [code for code, (_, expiry) in self.pairings.items() if expiry < now]
        for code in expired:
            del self.pairings[code]
            logger.info(f"Cleaned up expired pairing {code}")


class RedisPairingStore(PairingStore):
    """Redis implementation for production (future)."""
    
    def __init__(self, redis_client):
        """
        Initialize with Redis client.
        redis_client should be an instance of redis.Redis or redis.asyncio.Redis
        """
        self.redis = redis_client
        self.prefix = "pairing:"
    
    async def store_pairing(self, code: str, desktop_session_id: str, ttl: int = 3600) -> bool:
        """Store pairing with TTL in Redis."""
        key = f"{self.prefix}code:{code}"
        result = await self.redis.setex(key, ttl, desktop_session_id)
        logger.info(f"Stored pairing {code} in Redis with TTL {ttl}s")
        return bool(result)
    
    async def get_pairing(self, code: str) -> Optional[str]:
        """Get desktop session ID from Redis."""
        key = f"{self.prefix}code:{code}"
        value = await self.redis.get(key)
        return value.decode() if value else None
    
    async def consume_pairing(self, code: str) -> Optional[str]:
        """Get and delete pairing from Redis (atomic)."""
        key = f"{self.prefix}code:{code}"
        value = await self.redis.getdel(key)
        if value:
            logger.info(f"Consumed pairing {code} from Redis")
            return value.decode()
        return None
    
    async def add_to_channel(self, channel_id: str, client_id: str, device_type: str) -> bool:
        """Add client to channel hash in Redis."""
        key = f"{self.prefix}channel:{channel_id}"
        result = await self.redis.hset(key, client_id, device_type)
        # Set expiry on channel (1 hour)
        await self.redis.expire(key, 3600)
        logger.info(f"Added {client_id} ({device_type}) to Redis channel {channel_id}")
        return bool(result)
    
    async def get_channel_clients(self, channel_id: str) -> Dict[str, str]:
        """Get all clients in channel from Redis."""
        key = f"{self.prefix}channel:{channel_id}"
        result = await self.redis.hgetall(key)
        return {k.decode(): v.decode() for k, v in result.items()} if result else {}
    
    async def remove_from_channel(self, channel_id: str, client_id: str) -> bool:
        """Remove client from channel in Redis."""
        key = f"{self.prefix}channel:{channel_id}"
        result = await self.redis.hdel(key, client_id)
        logger.info(f"Removed {client_id} from Redis channel {channel_id}")
        return bool(result)