"""
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from app.deps import setup_dependencies
from app.pairing import router, websocket_endpoint
from app.pairing.security import SecurityMiddleware
from app.lexicon import router as lexicon_router
from app.ai import ai_router
from app.ai.normalization import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.loader_supabase import SupabaseLoader
from app.data.cache.cache_memory import InMemoryCache

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_security_middleware(request: Request) -> SecurityMiddleware:
    """Dependency to get security middleware from app state."""
    return request.app.state.security_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown tasks."""
    # Startup
    logger.info("🚀 Starting pairing server lifespan...")
    
    # Hydrate cache with admin user data for faster access
    try:
        data_registry = app.state.data_registry
        supabase_loader = data_registry.loader
        
        # Get admin user ID for cache hydration
        admin_id = supabase_loader.get_admin_id()
        logger.info(f"🔄 Hydrating cache for admin user: {admin_id}")
        
        # Hydrate cache with admin data
        await data_registry.hydrate_cache(admin_id)
        logger.info("✅ Cache hydration completed successfully")
        
        # Initialize normalization pipeline for admin user
        logger.info("🔄 Initializing normalization pipeline...")
        pipeline = await NormalizationFactory.create_for_admin(data_registry)
        app.state.normalization_pipeline = pipeline
        logger.info("✅ Normalization pipeline initialized successfully")
        
    except Exception as e:
        logger.warning(f"⚠️  Startup initialization failed (will continue): {e}")
    
    logger.info("✅ Pairing server startup completed")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down pairing server...")


def create_app(settings=None) -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Use provided settings or get default
    if settings is None:
        from app.settings import get_settings
        settings = get_settings()
    
    # Setup dependencies with settings
    deps = setup_dependencies(settings)
    
    # Construct DataRegistry for normalization
    cache = InMemoryCache()
    loader = SupabaseLoader()
    data_registry = DataRegistry(cache=cache, loader=loader)
    
    # Create FastAPI app
    app = FastAPI(
        title="Mondplan Speech - Pairing Server", 
        version="1.0.0",
        description=f"Running in {settings.app_env} mode",
        lifespan=lifespan
    )
    
    # Store dependencies in app state
    app.state.settings = settings
    app.state.connection_manager = deps["connection_manager"]
    app.state.pairing_service = deps["pairing_service"]
    app.state.pairing_store = deps["pairing_store"]
    app.state.security_middleware = deps["security_middleware"]
    app.state.ws_rate_limiter = deps["ws_rate_limiter"]
    app.state.http_rate_limiter = deps["http_rate_limiter"]
    app.state.connection_tracker = deps["connection_tracker"]
    app.state.data_registry = data_registry
    
    # Configure CORS with environment-specific origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(router)
    app.include_router(lexicon_router)
    app.include_router(ai_router)
    
    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket):
        """WebSocket endpoint handler."""
        await websocket_endpoint(
            websocket,
            app.state.connection_manager,
            app.state.security_middleware
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check(
        request: Request,
        security: SecurityMiddleware = Depends(get_security_middleware)
    ):
        """Health check endpoint."""
        await security.validate_request(request)
        return {"status": "healthy", "service": "mondplan-speech"}
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with test page."""
        return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Pairing Server</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #333; }
        .links { margin-top: 20px; }
        .links a { display: block; margin: 10px 0; color: #007bff; }
        .status { margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🦷 Mondplan Speech - Pairing Server</h1>
        <div class="status">
            <p><strong>Status:</strong> Running</p>
            <p><strong>Version:</strong> 1.0.0</p>
        </div>
        <div class="links">
            <h3>Test Pages:</h3>
            <a href="/api-test">🔬 Complete API Test Suite</a>
            <a href="/test-rate-limiter">🚦 Rate Limiter Test Suite</a>
            <a href="/test-desktop.html">Desktop Test Page</a>
            <a href="/test-mobile.html">Mobile Test Page</a>
            <a href="/test-mobile-local.html">Mobile Local Test Page</a>
            <a href="/docs">API Documentation</a>
            <a href="/health">Health Check</a>
        </div>
    </div>
</body>
</html>
        """)
    
    # Mount static files if directory exists
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Test pages directory - correct path to test_pages folder
    test_pages_dir = os.path.join(os.path.dirname(__file__), "..", "test_pages")
    
    # Serve test HTML files
    @app.get("/test-desktop.html")
    async def test_desktop():
        file_path = os.path.join(test_pages_dir, "test-desktop.html")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return HTMLResponse(f.read())
        return HTMLResponse(f"Test page not found at {file_path}", status_code=404)
    
    @app.get("/test-mobile.html")
    async def test_mobile():
        file_path = os.path.join(test_pages_dir, "test-mobile.html")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return HTMLResponse(f.read())
        return HTMLResponse(f"Test page not found at {file_path}", status_code=404)
    
    @app.get("/test-mobile-local.html")
    async def test_mobile_local():
        file_path = os.path.join(test_pages_dir, "test-mobile-local.html")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return HTMLResponse(f.read())
        return HTMLResponse(f"Test page not found at {file_path}", status_code=404)
    
    @app.get("/api-test")
    async def api_test_suite():
        """Complete API test suite with ALL available endpoints on the unified server."""
        file_path = os.path.join(test_pages_dir, "api_test_complete.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse("API test page not found", status_code=404)
    
    @app.get("/test-rate-limiter")
    async def rate_limiter_test():
        """Rate limiter test suite for HTTP and WebSocket rate limiting."""
        file_path = os.path.join(test_pages_dir, "test-rate-limiter.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse("Rate limiter test page not found", status_code=404)
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    from app.settings import get_settings
    
    # Get settings instance
    settings = get_settings()
    
    # Configure logging based on settings
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Log startup information
    logger.info(f"🚀 Starting Pairing Server in {settings.app_env.upper()} mode")
    logger.info(f"🌐 Server: {settings.host}:{settings.get_port()}")
    logger.info(f"🔗 Allowed origins: {settings.get_allowed_origins()}")
    logger.info(f"💾 Storage: {'Redis' if settings.should_use_redis() else 'In-Memory'}")
    logger.info(f"⚡ Rate limiting: {'Enabled' if settings.rate_limit_enabled else 'Disabled'}")
    
    # Create app with current settings
    app = create_app(settings)
    
    if settings.is_development:
        # In development, use import string for reload support
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.get_port(),
            reload=True,
            log_level=settings.log_level.lower()
        )
    else:
        # In production, use app instance (no reload)
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.get_port(),
            reload=False,
            log_level=settings.log_level.lower()
        )