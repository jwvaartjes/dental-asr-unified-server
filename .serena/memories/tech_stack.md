# Tech Stack & Architecture

## Core Technologies
- **Backend**: FastAPI (Python) - Modern async web framework
- **WebSocket**: Real-time communication for device pairing
- **Database**: Supabase (PostgreSQL) - Cloud database for user data, lexicons
- **AI/ASR**: OpenAI GPT-4o-transcribe - State-of-the-art speech recognition
- **Authentication**: JWT tokens with magic link support
- **Testing**: pytest with custom markers (slow, integration, normalization)

## Key Dependencies
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
supabase==2.0.2
pydantic==2.5.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
httpx==0.25.2
openai==1.3.5
```

## Server Architecture (Port 8089)
```
app/
├── main.py              # FastAPI application entry point
├── settings.py          # Environment-based configuration
├── deps.py              # Dependency injection setup
├── pairing/             # Device pairing module
│   ├── router.py        # API routes & WebSocket handler
│   ├── service.py       # Business logic (ConnectionManager, PairingService)
│   ├── store.py         # Storage interfaces (InMemory/Redis)
│   ├── security.py      # JWT, origin validation, rate limiting
│   └── schemas.py       # Pydantic models
├── ai/                  # AI/ASR module
│   ├── routes.py        # AI API endpoints (/api/ai/*)
│   ├── config.py        # AI provider configuration
│   ├── factory.py       # Provider factory pattern
│   ├── interfaces.py    # ASR/LLM provider interfaces
│   ├── normalization/   # Dutch dental term normalization
│   └── providers/       # Provider implementations
├── lexicon/             # Lexicon management module
├── data/                # Data layer architecture
│   ├── registry.py      # DataRegistry (central orchestrator)
│   ├── cache/           # Cache abstraction & implementation
│   └── loaders/         # Supabase loader implementation
└── middleware/          # Rate limiting, security
```

## Environment Requirements
- **SUPABASE_URL**: Supabase project URL
- **SUPABASE_SERVICE_KEY**: Service role key
- **SUPABASE_ANON_KEY**: Anonymous key
- **OPENAI_API_KEY**: OpenAI API key
- **JWT_SECRET**: JWT signing secret
- **MODEL_ID**: openai/gpt-4o-transcribe