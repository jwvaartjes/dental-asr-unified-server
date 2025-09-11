# Dental ASR Unified Pairing Server

A modular, high-performance FastAPI server that provides unified API endpoints for dental ASR system functionality, including device pairing, lexicon management, and AI/ASR provider integration.

## 🌟 Features

- **🔗 Device Pairing System**: WebSocket-based pairing between desktop and mobile devices
- **📚 Lexicon Management**: Complete CRUD operations for dental terminology with duplicate detection
- **🤖 AI/ASR Integration**: Multi-provider support (OpenAI GPT-4o, Whisper, Azure)
- **🛡️ Protected Words**: Management of protected dental terminology
- **⚡ Data Layer Architecture**: Cache-first strategy with Supabase backend
- **🔒 Advanced Security**: JWT authentication, rate limiting, origin validation
- **📊 Comprehensive API**: RESTful endpoints with OpenAPI documentation

## 🏗️ Architecture

### Modular Structure
```
app/
├── main.py              # FastAPI application entry
├── settings.py          # Environment-based configuration
├── deps.py             # Dependency injection
├── data/               # Data layer architecture
│   ├── registry.py     # Central data orchestrator
│   ├── cache/          # Cache abstraction layer
│   └── loaders/        # Data loading interfaces
├── ai/                 # AI/ASR provider integration
│   ├── factory.py      # Multi-provider factory
│   ├── providers/      # Provider implementations
│   └── routes.py       # AI API endpoints
├── lexicon/            # Lexicon management
│   ├── router.py       # Lexicon API endpoints
│   └── schemas.py      # Data validation schemas
├── pairing/            # Device pairing system
│   ├── router.py       # Pairing API & WebSocket
│   ├── service.py      # Business logic
│   └── security.py     # Auth & rate limiting
└── middleware/         # Custom middleware
```

### Key Technologies
- **FastAPI**: Modern Python web framework
- **WebSockets**: Real-time bidirectional communication
- **Supabase**: Cloud database and authentication
- **Pydantic**: Data validation and serialization
- **JWT**: Secure token-based authentication

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supabase account and project
- Environment variables configured

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pairing_server
   ```

2. **Install dependencies**
   ```bash
   pip install fastapi uvicorn websockets supabase pydantic
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Run the server**
   ```bash
   python3 -m app.main
   ```

The server will start on `http://localhost:8089`

### Environment Variables

```bash
# Required
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key
JWT_SECRET=your-jwt-secret

# Optional
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
PORT=8089

# AI/ASR (Optional)
OPENAI_API_KEY=your-openai-key
MODEL_ID=openai/gpt-4o-transcribe
```

## 📚 API Documentation

### Core Endpoints

#### Device Pairing
- `POST /api/generate-pair-code` - Generate pairing code
- `POST /api/pair-device` - Complete device pairing
- `WebSocket /ws` - Real-time pairing communication

#### Lexicon Management
- `GET /api/lexicon/categories` - List all categories
- `GET /api/lexicon/terms/{category}` - Get terms by category
- `POST /api/lexicon/add-canonical` - Add term (with duplicate detection)
- `DELETE /api/lexicon/remove-canonical` - Remove term
- `GET /api/lexicon/search?q={query}` - Search lexicon

#### Protected Words
- `GET /api/protect_words` - Get protected words
- `POST /api/protect_words` - Save protected words
- `DELETE /api/protect_words/{word}` - Delete individual word

#### AI/ASR Integration
- `GET /api/ai/model-info` - Get model information
- `GET /api/ai/status` - Check provider status

### Data Formats

#### Protected Words Format
```json
{
  "protected_words": ["word1", "word2", "word3"]
}
```

#### Lexicon Entry Format
```json
{
  "term": "implant",
  "category": "treatments"
}
```

## 🔧 Development

### Project Structure
The server follows a modular architecture with clear separation of concerns:

- **Data Layer**: Centralized data access with caching
- **Business Logic**: Service classes for complex operations
- **API Layer**: FastAPI routers with proper validation
- **Security**: JWT authentication and rate limiting

### Testing
API test pages are available at:
- `/api-test` - Comprehensive API testing interface
- `/test-desktop.html` - Desktop pairing test
- `/test-mobile-local.html` - Mobile pairing test

### Key Features

#### 🔒 Security Features
- JWT token authentication
- Rate limiting (token bucket algorithm)
- Origin validation for WebSocket connections
- Scoped access tokens for different operations

#### ⚡ Performance Features
- Cache-first data strategy
- Connection pooling for database
- Efficient WebSocket message handling
- Background cleanup tasks

#### 🛡️ Data Integrity
- Comprehensive duplicate detection for lexicon terms
- Cross-category validation
- Case-insensitive comparison with smart normalization
- Detailed error messages for conflicts

## 🔄 Migration from Legacy Server

This unified server replaces functionality from the legacy server (`server_windows_spsc.py`) with:

- **✅ Feature Parity**: All lexicon and pairing functionality migrated
- **🚨 Breaking Changes**: New protected words data format required
- **🆕 Enhanced Features**: Individual word deletion, better duplicate detection
- **📊 Better Architecture**: Modular design with proper separation of concerns

### Migration Checklist
- [ ] Update client applications to use new protected words format
- [ ] Test all API endpoints with new server
- [ ] Update WebSocket connection handling
- [ ] Verify authentication flow works correctly

## 📄 License

This project is part of the Dental ASR System - proprietary software for dental practice management.

## 🤝 Contributing

This is a private project. For questions or issues, contact the development team.

---

**Built with ❤️ for modern dental practices**