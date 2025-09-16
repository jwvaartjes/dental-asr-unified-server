# Code Style & Conventions

## Python Style Guidelines
- **Type Hints**: Used throughout the codebase (Pydantic models, function signatures)
- **Docstrings**: Google-style docstrings for classes and methods
- **Async/Await**: FastAPI uses async functions extensively
- **Pydantic Models**: For data validation and API schemas
- **Dependency Injection**: FastAPI dependency system used in routes

## Naming Conventions
- **Classes**: PascalCase (e.g., `NormalizationPipeline`, `ConnectionManager`)
- **Functions/Methods**: snake_case (e.g., `normalize`, `create_app`)
- **Variables**: snake_case (e.g., `data_registry`, `connection_manager`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `CANONICAL_HYPHENATED`)
- **Private Methods**: Leading underscore (e.g., `_apply_on_unprotected`)

## Project Structure Patterns
- **Modular Architecture**: Clear separation by domain (pairing/, ai/, lexicon/)
- **Factory Pattern**: Used for provider creation (AI providers)
- **Interface Pattern**: Abstract base classes for providers and loaders
- **Router Pattern**: FastAPI routers for API endpoints
- **Dependency Registry**: Central data registry for shared resources

## Code Organization
- **app/**: Main application code
- **test_pages/**: HTML test interfaces
- **debug/**: Debug scripts and test utilities
- **unittests/**: pytest test files
- Root level scripts for specific operations

## Testing Patterns
- **pytest**: Primary testing framework
- **Markers**: Custom markers (slow, integration, normalization)
- **Test Files**: `test_*.py` naming convention
- **Debug Scripts**: Specific issue testing in `/debug/` folder
- **HTML Test Pages**: Browser-based testing for full functionality

## Error Handling
- **Fail-Fast**: Configuration validation fails early with clear messages
- **Async Context**: Proper async/await error handling
- **Logging**: Structured logging throughout the application
- **Rate Limiting**: Built-in rate limiting with proper error responses

## Configuration Management
- **Environment Variables**: `.env` file support with `python-dotenv`
- **Settings Class**: Centralized configuration management
- **Supabase Integration**: Cloud-based configuration storage
- **Default Values**: Fallback configurations for development

## API Design
- **REST Endpoints**: Clear resource-based URLs
- **WebSocket**: Real-time communication for pairing
- **Pydantic Schemas**: Request/response validation
- **Status Codes**: Proper HTTP status code usage
- **CORS**: Environment-specific origin handling