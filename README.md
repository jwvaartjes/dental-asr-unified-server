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

# Normalization Pipeline

Deze pipeline zet **ruwe transcriptietekst** om naar een **gestandaardiseerde dentale representatie**.  
Ze is deterministisch, config-gedreven (Supabase) en reproduceert de “slimmigheden” van het oude systeem.

---

## TL;DR (wat doet het?)

- Herkent en normaliseert **tandnummers (1–48)** in vrije tekst en binnen **dental context** (element/tand/kies/molaar/premolaar).
- **Protected words** blijven onaangeroerd.
- **Telwoorden** in context worden gecombineerd: `element een vier` → `element 14`, `tand twee drie` → `tand 23`.
- **Lidwoord-cleanup**: `de 11` → `element 11`.
- **Varianten** en **fuzzy** corrigeren spelfouten (geen matching op cijfers/percentages).
- **Postprocessing** ruimt spaties op en verwijdert dubbele frasen: `element 14 element 14` → `element 14`.

---

## Belangrijke begrippen

### Tokenization (doorlopend)
De pipeline werkt op **tokens** (woorden, cijfers, interpunctie) en voegt ze aan het einde weer netjes samen.
- Preprocessing maakt `14;15;16` token-vriendelijk: `14 ; 15 ; 16`.
- Fuzzy werkt **per token** (interpunctie en cijfers worden overgeslagen).
- NBSP’s (`\u00A0`) worden eerst genormaliseerd naar gewone spaties.

### Protected Words
Woorden uit Supabase worden gewrapt en **niet** genormaliseerd.  
Voorbeeld: `Paro` blijft exact `Paro`.

### Dental Context Words
Dezelfde set als in het oude systeem:

element | tand | kies | molaar | premolaar

Binnen deze context worden telwoorden en getallen gecombineerd tot **elementnummers**.

---

## Stap-voor-stap (pipeline)

0) **Protected wrap**  
   Markeer protected words; alle stappen werken alleen op onbeschermde segmenten.

1) **Preprocessing**  
   - NBSP → spatie.  
   - Scheid separators tussen cijfers (`, ; - /`), zodat `14;15` goed parsebaar wordt.  
   *(Geen lowercasing of inhoudelijke wijzigingen.)*

2) **Element parsing (context & multi-woord)**  
   - Herkent **paren 1..4 + 1..8** in algemene tekst → `element NN`.  
   - **Context-regels (oude slimmigheden):**  
     - `element 1, 2` → `element 12`  
     - `de 11` / `de element 1-4` → `element 11` / `element 14`  
     - `<context> een vier` → `<context> 14` (bv. `tand een vier` → `tand 14`)  
     - `<context> 1 4` / `<context> 1-4` → `<context> 14`  
   - Guard tegen dubbel prefix: bestaand `element 14` blijft `element 14` (nooit `element element 14`).

3) **Learnable normalization (Supabase)**  
   Regex-regels per praktijk/gebruiker (kan multi-woord zijn).

4) **Variant generation (vóór fuzzy)**  
   - Spellingvarianten/afkortingen → canoniek.  
   - **Cijferwoorden (contextgevoelig):**  
     - `één` → altijd `1`  
     - `een` → **alleen** numeriek in relevante context (bv. na contextwoord of tussen element-separators).  
     - Aanbevolen: laat `"een": "1"` **weg** uit Supabase; `"één": "1"` wel opnemen.

5) **Phonetic/fuzzy matching**  
   - Levenshtein per woordtoken tegen canonieke termen.  
   - **Slaat cijfers/percentages over**.  
   - Kan multi-woord samenstellingen corrigeren (bv. `bot verlies` → `botverlies`).

6) **Postprocessing**  
   - Spaties en interpunctie opschonen.  
   - **Dedup** oude-stijl: `element 14 element 14` → `element 14`.  
   - **Lidwoord-cleanup**: `" de element "` → `" element "`; `"de element …"` aan zinbegin → `"element …"`.

7) **Protected unwrap**  
   Verwijder markers; protected words blijven exact zoals ingevoerd.

---

## Voorbeelden (verwachte output)

- `14;15;16` → `element 14; element 15; element 16`  
- `element 1, 2` → `element 12`  
- `de 11` → `element 11`  
- `element een vier` → `element 14`  
- `tand een vier` → `tand 14`  
- `kies twee drie` → `kies 23`  
- `1-4 en 2-3` → `element 14 en element 23`  
- `Paro met parod` → `Paro met parodontitis` (protected + variant)  
- `30% botverlies` → `30% botverlies` (fuzzy negeert percentage)

---

## Config (Supabase) – minimaal vereist

```json
{
  "variant_generation": {
    "separators": ["-", " ", ",", ";", "/"],
    "element_separators": ["-", " ", ",", ";", "/"],
    "digit_words": {
      "één": "1",
      "twee": "2",
      "drie": "3",
      "vier": "4",
      "vijf": "5",
      "zes": "6",
      "zeven": "7",
      "acht": "8"
      // Tip: laat "een" weg; context regelt dit
    }
  },
  "phonetic": { "threshold": 0.84 },
  "normalization": {
    "enable_element_parsing": true,
    "enable_learnable": true,
    "enable_variant_generation": true,
    "enable_phonetic_matching": true,
    "enable_post_processing": true
  },
  "protected_words": ["Paro", "Cito"]
}

Als variant_generation.separators of element_separators ontbreken, faalt de init expliciet met een duidelijke fout—zet ze dus altijd.

Integratie (FastAPI)

Startup (éénmalig):

# main.py
app.state.normalization_pipeline = await NormalizationFactory.create_for_admin(data_registry)

In de route:

norm = request.state.normalization_pipeline.normalize(raw_text, language=result.language or "nl")
return TranscriptionResponse(
  text=raw_text, raw=raw_text, normalized=norm.normalized_text, language=result.language or "nl", ...
)

Debugging

Elke stap logt de tussenstand in NormalizationResult.debug. Typische checks:

Zit \uFFF0…\uFFF1 rond protected words in protected_wrap?

Zie je de separator-spaties in preprocess?

Is de 11 al element 11 in elements?

Zie je varianten/fuzzy pas na variants/phonetic?



```python
norm = pipeline.normalize(raw_text, language="nl")
normalized_text = norm.normalized_text



## 🤝 Contributing

This is a private project. For questions or issues, contact the development team.

---

**Built with ❤️ for modern dental practices**