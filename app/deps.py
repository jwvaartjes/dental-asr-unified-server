"""
Dependencies and dependency injection setup.
"""
import sys
import os
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings import Settings
from app.pairing import (
    ConnectionManager,
    PairingService,
    InMemoryPairingStore,
    RedisPairingStore,
    OriginValidator,
    SecurityMiddleware
)
from app.data import (
    DataRegistry,
    InMemoryCache,
    SupabaseLoader
)

logger = logging.getLogger(__name__)


def get_pairing_store(settings: Settings):
    """Get the appropriate pairing store based on settings."""
    if settings.should_use_redis():
        try:
            import redis
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            logger.info("Using Redis pairing store")
            return RedisPairingStore(redis_client)
        except ImportError:
            logger.warning("Redis not available, falling back to in-memory store")
            return InMemoryPairingStore()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}, falling back to in-memory store")
            return InMemoryPairingStore()
    else:
        logger.info("Using in-memory pairing store")
        return InMemoryPairingStore()


def get_rate_limiter(settings: Settings):
    """Get rate limiter if enabled."""
    if not settings.rate_limit_enabled:
        return None, None
    
    try:
        from app.middleware import WebSocketRateLimiter, RateLimiter
        
        ws_limiter = WebSocketRateLimiter(
            max_connections_per_ip=settings.max_connections_per_ip,
            max_messages_per_second=settings.max_messages_per_second,
            max_pairing_attempts=settings.max_pairing_attempts,
            pairing_window_seconds=settings.pairing_window_seconds
        )
        
        http_limiter = RateLimiter(
            max_requests=settings.max_requests_per_minute,
            window_seconds=60
        )
        
        logger.info("Rate limiting enabled")
        return ws_limiter, http_limiter
    except ImportError:
        logger.warning("Rate limiter modules not found, rate limiting disabled")
        return None, None


def get_connection_tracker():
    """Get connection tracker if available."""
    try:
        from app.middleware import ConnectionTracker
        logger.info("Connection tracking enabled")
        return ConnectionTracker()
    except ImportError:
        logger.warning("Connection tracker not available")
        return None


def get_data_registry():
    """Get data registry with cache and loader."""
    try:
        # Initialize cache (InMemory for now, Redis later)
        cache = InMemoryCache(cleanup_interval=300)  # 5 min cleanup
        logger.info("InMemory cache initialized")
        
        # Initialize Supabase loader
        loader = SupabaseLoader()
        logger.info("SupabaseLoader initialized")
        
        # Create data registry
        registry = DataRegistry(loader, cache)
        logger.info("DataRegistry initialized")
        
        return registry
    except Exception as e:
        logger.error(f"Failed to initialize data layer: {e}")
        raise RuntimeError(f"Data layer initialization failed: {e}")


def setup_dependencies(settings: Settings):
    """Setup all dependencies and return them."""
    # Setup logging
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    
    # Create core components
    connection_manager = ConnectionManager()
    pairing_store = get_pairing_store(settings)
    pairing_service = PairingService(connection_manager, pairing_store)
    
    # Create security components
    origin_validator = OriginValidator(settings.get_allowed_origins())
    ws_rate_limiter, http_rate_limiter = get_rate_limiter(settings)
    connection_tracker = get_connection_tracker()
    
    # Create security middleware
    security_middleware = SecurityMiddleware(
        origin_validator=origin_validator,
        http_rate_limiter=http_rate_limiter,
        ws_rate_limiter=ws_rate_limiter
    )
    
    # Create data layer
    data_registry = get_data_registry()
    
    return {
        "connection_manager": connection_manager,
        "pairing_service": pairing_service,
        "pairing_store": pairing_store,
        "security_middleware": security_middleware,
        "ws_rate_limiter": ws_rate_limiter,
        "http_rate_limiter": http_rate_limiter,
        "connection_tracker": connection_tracker,
        "data_registry": data_registry,
        "settings": settings
    }