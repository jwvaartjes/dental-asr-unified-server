"""
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocket, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
import os

from app.deps import setup_dependencies
from app.pairing import router, websocket_endpoint
from app.pairing.auth_endpoints import auth_router
from app.pairing.security import SecurityMiddleware
from app.lexicon import router as lexicon_router
from app.ai import ai_router
from app.templates.router import router as templates_router
from app.users.router import router as users_router
from app.test_router import router as test_router
from app.ai.normalization import NormalizationFactory
from app.data.registry import DataRegistry
from app.data.loaders.loader_supabase import SupabaseLoader
from app.data.cache.cache_memory import InMemoryCache
from app.monitoring.dashboard import MonitoringDashboard

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

        # Initialize AI factory for streaming transcription
        logger.info("🔄 Initializing AI factory...")
        from app.ai.factory import ProviderFactory
        ai_factory = ProviderFactory()
        app.state.ai_factory = ai_factory
        logger.info("✅ AI factory initialized successfully")

        # Initialize transcriber manager for hot-swapping
        logger.info("🔄 Initializing transcriber manager...")
        from app.ai.transcriber_manager import initialize_transcriber_manager
        app.state.transcriber_manager = initialize_transcriber_manager(
            app.state.ai_factory,
            app.state.normalization_pipeline,
            app.state.data_registry
        )
        logger.info("✅ Transcriber manager initialized successfully")

        # Initialize monitoring dashboard
        logger.info("🔄 Initializing monitoring dashboard...")
        monitoring_dashboard = MonitoringDashboard()
        app.state.monitoring_dashboard = monitoring_dashboard

        # Add monitoring routes to the app
        app.include_router(monitoring_dashboard.router)
        logger.info("✅ Monitoring dashboard initialized successfully")
        
    except Exception as e:
        logger.warning(f"⚠️  Startup initialization failed (will continue): {e}")
    
    logger.info("✅ Pairing server startup completed")

    # Start heartbeat monitoring system
    logger.info("🔄 Starting heartbeat monitoring system...")
    try:
        await app.state.connection_manager.heartbeat.start_heartbeat(app.state.connection_manager)
        logger.info("✅ Heartbeat monitoring system started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start heartbeat monitoring: {e}")

    logger.info("🚀 All systems operational")
    
    yield

    # Shutdown
    logger.info("🔄 Shutting down heartbeat monitoring system...")
    try:
        await app.state.connection_manager.heartbeat.stop_heartbeat()
        logger.info("✅ Heartbeat monitoring system stopped")
    except Exception as e:
        logger.error(f"❌ Failed to stop heartbeat monitoring: {e}")
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
    app.state.template_service = deps["template_service"]
    
    # Configure CORS - conditionally enable for debugging
    if settings.cors_enabled:
        logger.info("CORS middleware ENABLED")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.get_allowed_origins(),
            allow_origin_regex=r"https://.*\.lovable\.app|https://.*\.lovable\.dev|https://.*\.lovableproject\.com|https://.*\.ngrok\.app|https://.*\.ngrok\.io|https://.*\.mondplan\.com|https://.*\.vercel\.app",
            allow_credentials=True,  # Enable credentials for httpOnly cookies
            allow_methods=["*"],
            allow_headers=["*"],
            max_age=3600,
        )
    else:
        logger.info("CORS middleware DISABLED for development")

    # Add security headers middleware for development
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers that allow localhost development."""
        response = await call_next(request)

        # Development-friendly CSP that allows localhost connections
        if settings.cors_enabled or not settings.cors_enabled:  # For all environments
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "media-src 'self' blob:; "
                "connect-src 'self' "
                "http://localhost:8089 https://localhost:8089 "
                "http://127.0.0.1:8089 https://127.0.0.1:8089 "
                "http://localhost:5173 https://localhost:5173 "
                "https://dental-scribe-glow-aa18kq1s8-mond-plan.vercel.app "
                "ws://localhost:8089 wss://localhost:8089 "
                "ws://127.0.0.1:8089 wss://127.0.0.1:8089 "
                "https://*.supabase.co https://*.openai.com; "
                "font-src 'self' data:; "
                "frame-ancestors 'self' http://localhost:* https://localhost:* https://*.lovable.dev https://*.vercel.app; "
                "object-src 'none'; "
                "base-uri 'self'"
            )
            response.headers["Content-Security-Policy"] = csp_policy
            logger.debug(f"Added CSP header for {request.url.path}")

        return response

    # Include API routers
    app.include_router(router)
    app.include_router(auth_router)  # Clean auth endpoints with httpOnly cookies
    app.include_router(lexicon_router)
    app.include_router(ai_router)
    app.include_router(users_router)
    app.include_router(templates_router)
    app.include_router(test_router)

    # Add monitoring dashboard after app state is configured
    # (Will be added dynamically after lifespan startup)
    
    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket):
        """WebSocket endpoint handler."""
        # Get AI factory and normalization pipeline if available
        ai_factory = getattr(app.state, 'ai_factory', None)
        normalization_pipeline = getattr(app.state, 'normalization_pipeline', None)

        await websocket_endpoint(
            websocket,
            app.state.connection_manager,
            app.state.security_middleware,
            app.state.template_service,
            app.state.data_registry,
            ai_factory=ai_factory,
            normalization_pipeline=normalization_pipeline
        )

    # Monitoring WebSocket endpoint
    @app.websocket("/ws-monitor")
    async def websocket_monitor_route(websocket: WebSocket):
        """WebSocket endpoint for real-time monitoring"""
        monitoring_dashboard = getattr(app.state, 'monitoring_dashboard', None)
        if monitoring_dashboard:
            await monitoring_dashboard.websocket_monitor(websocket)
        else:
            await websocket.close(code=1011, reason="Monitoring not available")
    
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
            <h3>Configuration & Management:</h3>
            <a href="/config-editor">⚙️ Supabase Config Editor (Monaco)</a>
            <a href="/config-editor-simple">⚙️ Supabase Config Editor (Simple)</a>

            <h3>Monitoring & Observability:</h3>
            <a href="/monitoring-dashboard">🚀 Visual Monitoring Dashboard</a>
            <a href="/api/monitoring/dashboard">📊 Monitoring Dashboard (JSON)</a>
            <a href="/api/monitoring/clients">👥 Active Clients</a>
            <a href="/api/monitoring/performance">⚡ Performance Summary</a>
            <a href="/api/monitoring/health">🏥 System Health</a>
            <a href="/api/monitoring/events">📋 Recent Events</a>

            <h3>Test Pages:</h3>
            <a href="/api-test">🔬 Complete API Test Suite</a>
            <a href="/test-rate-limiter">🚦 Rate Limiter Test Suite</a>
            <a href="/test-normalization">🧪 Normalization Test Runner</a>
            <a href="/test-desktop.html">Desktop Test Page</a>
            <a href="/test-desktop-streaming.html">🎤 Desktop Streaming Test</a>
            <a href="/test-mobile.html">Mobile Test Page</a>
            <a href="/test-mobile-local.html">Mobile Local Test Page</a>

            <h3>Documentation:</h3>
            <a href="/docs">📚 API Documentation</a>
            <a href="/health">🏥 Health Check</a>
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

    @app.get("/test-desktop-streaming.html")
    async def test_desktop_streaming():
        """Desktop audio streaming test page based on old server logic."""
        file_path = os.path.join(test_pages_dir, "test-desktop-streaming.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse(f"Desktop streaming test page not found at {file_path}", status_code=404)

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

    @app.get("/monitoring-dashboard")
    async def visual_monitoring_dashboard():
        """Visual real-time monitoring dashboard with charts and metrics."""
        file_path = os.path.join(test_pages_dir, "monitoring_dashboard_visual.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse("Visual monitoring dashboard not found", status_code=404)

    @app.get("/config-editor")
    async def config_editor():
        """Supabase configuration editor with Monaco editor interface."""
        file_path = os.path.join(test_pages_dir, "config_editor.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse("Config editor page not found", status_code=404)

    @app.get("/config-editor-simple")
    async def config_editor_simple():
        """Simple Supabase configuration editor with textarea interface."""
        file_path = os.path.join(test_pages_dir, "config_editor_simple.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse("Simple config editor page not found", status_code=404)

    @app.get("/api-monitoring")
    async def api_monitoring_dashboard():
        """API monitoring dashboard with comprehensive test suite."""
        file_path = os.path.join(test_pages_dir, "api_monitoring_dashboard.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as f:
                return HTMLResponse(f.read())
        return HTMLResponse("API monitoring dashboard not found", status_code=404)

    @app.post("/run-comprehensive-tests")
    async def run_comprehensive_tests(request: Request):
        """Run comprehensive test suite and return results."""
        import subprocess
        import asyncio
        
        try:
            # Run the Python test suite
            result = subprocess.run([
                'python3', 'debug/complete_api_test_suite.py'
            ], capture_output=True, text=True, timeout=120)
            
            # Parse output for structured results
            output_lines = result.stdout.split('\n')
            
            # Extract key metrics
            summary = {
                "total": 0,
                "passed": 0, 
                "failed": 0,
                "success_rate": 0,
                "status": "unknown"
            }
            
            for line in output_lines:
                if "Total Tests:" in line:
                    summary["total"] = int(line.split("Total Tests:")[1].strip())
                elif "Passed:" in line:
                    summary["passed"] = int(line.split("Passed:")[1].strip())
                elif "Failed:" in line:
                    summary["failed"] = int(line.split("Failed:")[1].strip())
                elif "Success Rate:" in line:
                    rate_str = line.split("Success Rate:")[1].strip().replace('%', '')
                    summary["success_rate"] = float(rate_str)
                elif "EXCELLENT" in line:
                    summary["status"] = "excellent"
                elif "CRITICAL" in line:
                    summary["status"] = "critical"
                elif "GOOD" in line:
                    summary["status"] = "good"
            
            return {
                "success": result.returncode == 0,
                "summary": summary,
                "full_output": result.stdout,
                "errors": result.stderr,
                "timestamp": datetime.now().isoformat(),
                "total_endpoints": len(allEndpoints) if 'allEndpoints' in globals() else summary["total"]
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test suite timed out after 120 seconds",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

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