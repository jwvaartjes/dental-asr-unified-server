# Dental ASR System - Technical Documentation

## System Overview

A unified real-time dental speech recognition system with advanced normalization and file transcription. Built for Dutch dental practices, featuring OpenAI GPT-4o-transcribe integration, custom dental terminology normalization, and complete pairing server infrastructure.

### Key Features
- **Unified Server Architecture**: Single server on port 8089 handles ALL functionality
- **OpenAI GPT-4o-transcribe**: State-of-the-art ASR with dental-specific prompts
- **File Upload Transcription**: Upload audio files for transcription with validation
- **Real-time WebSocket**: Live audio streaming and device pairing
- **Dental Normalization**: Specialized for Dutch dental terminology
- **Device Pairing**: Desktop-mobile pairing system for remote audio capture
- **Supabase Cloud Storage**: Per-user lexicons and configurations (REQUIRED)
- **Complete API Suite**: REST endpoints for all operations
- **Comprehensive Testing**: Built-in test pages for all functionality

## 🎯 **CURRENT UNIFIED SERVER ARCHITECTURE**

### **✅ MAIN SERVER - PORT 8089**
**EVERYTHING runs on the NEW unified pairing server!**
- **Location**: `/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace/pairing_server/`
- **Command**: `cd pairing_server && python3 -m app.main`
- **Port**: 8089 (unified for all operations)
- **Technology**: FastAPI with modular architecture
- **Features**: Pairing, Authentication, AI/ASR, File Upload, WebSocket, Testing

### **⚠️ DEPRECATED - PORT 3001** 
**OLD Windows server is being phased out:**
- **File**: `server_windows_spsc.py` 
- **Status**: LEGACY - only for reference
- **Migration**: All functionality moved to unified server

### **Complete Unified Server Structure**
```
stable_baseline_workspace/pairing_server/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── settings.py          # Environment-based configuration
│   ├── deps.py              # Dependency injection setup
│   ├── pairing/             # PAIRING MODULE
│   │   ├── router.py        # API routes & WebSocket handler
│   │   ├── service.py       # Business logic (ConnectionManager, PairingService)
│   │   ├── store.py         # Storage interfaces (InMemory/Redis)  
│   │   ├── security.py      # JWT, origin validation, rate limiting
│   │   └── schemas.py       # Pydantic models
│   ├── ai/                  # AI/ASR MODULE (COMPLETE!)
│   │   ├── routes.py        # AI API endpoints (/api/ai/*)
│   │   ├── config.py        # AI provider configuration
│   │   ├── factory.py       # Provider factory pattern
│   │   ├── interfaces.py    # ASR/LLM provider interfaces
│   │   └── providers/       # Provider implementations
│   │       ├── openai_provider.py    # OpenAI GPT-4o-transcribe
│   │       ├── whisper_provider.py   # Local Whisper
│   │       └── azure_openai_provider.py # Azure OpenAI
│   ├── lexicon/             # LEXICON MODULE (COMPLETE!)
│   │   ├── router.py        # Lexicon management endpoints
│   │   └── service.py       # Lexicon business logic
│   └── data/                # DATA LAYER ARCHITECTURE
│       ├── registry.py      # DataRegistry (central orchestrator)
│       ├── cache/           # Cache abstraction & implementation
│       └── loaders/         # Supabase loader implementation
├── test_pages/              # HTML test files
│   ├── api_test_complete.html      # COMPREHENSIVE API test suite
│   ├── test-desktop.html           # Desktop pairing test
│   ├── test-mobile-local.html      # Mobile pairing test
│   └── test-rate-limiter.html      # Rate limiting tests
└── static/                  # Static assets (if any)
```

## 🚀 **UNIFIED SERVER CAPABILITIES**

### **✅ FULLY OPERATIONAL MODULES**

#### 1. **AI/ASR Module - OpenAI GPT-4o-transcribe**
- **Status**: PRODUCTION READY ✅
- **Provider**: OpenAI GPT-4o-transcribe (state-of-the-art)
- **Features**:
  - File upload transcription with comprehensive validation
  - Base64 audio encoding/decoding
  - File format support: WAV, MP3, M4A, OGG, FLAC, MP4, WebM
  - File size validation (25MB OpenAI limit)
  - Duration validation (minimum 0.1s OpenAI requirement)
  - Dutch language optimization with dental prompts
  - Error handling for corrupted/unsupported files

**API Endpoints:**
```
GET  /api/ai/model-info      - Get provider details & capabilities
GET  /api/ai/status          - Show comprehensive provider status
POST /api/ai/transcribe      - Transcribe uploaded audio files
```

**Environment Variables:**
```bash
OPENAI_API_KEY=your-openai-api-key
MODEL_ID=openai/gpt-4o-transcribe
```

#### 2. **Authentication & Security**
- **Status**: PRODUCTION READY ✅ 
- **Features**:
  - JWT token authentication
  - Magic link login (no password required)
  - Regular login (email + password)
  - WebSocket token generation
  - Rate limiting (HTTP & WebSocket)
  - Origin validation & CORS
  - Security middleware

**API Endpoints:**
```
POST /api/auth/login              - Regular login
POST /api/auth/login-magic        - Magic link login
GET  /api/auth/check-email        - Email validation (realistic behavior)
POST /api/auth/ws-token           - WebSocket token for desktop
POST /api/auth/ws-token-mobile    - WebSocket token for mobile
GET  /api/auth/verify             - Verify authentication
```

**Fixed Issues:**
- ✅ User role field properly returned (no more `undefined`)
- ✅ Email validation now realistic (known domains only)

#### 3. **Device Pairing System**  
- **Status**: PRODUCTION READY ✅
- **Features**:
  - Desktop generates 6-digit pairing codes
  - Mobile enters code to connect
  - WebSocket-based real-time communication
  - Channel-based messaging (prevents cross-talk)
  - Connection management & cleanup
  - Rate limiting for pairing attempts

**API Endpoints:**
```
POST /api/generate-pair-code      - Generate pairing code for desktop
POST /api/pair-device             - Pair mobile device with code
WS   /ws                          - WebSocket endpoint for real-time communication
```

#### 4. **Lexicon Management**
- **Status**: PRODUCTION READY ✅
- **Features**:
  - Complete CRUD operations for dental terminology
  - Category management
  - Search functionality
  - Duplicate detection with warnings
  - Protected words management
  - Hierarchical lexicon system

**API Endpoints:**
```
GET    /api/lexicon/categories           - Get all categories
GET    /api/lexicon/terms/{category}     - Get terms by category  
GET    /api/lexicon/full                 - Get complete lexicon
GET    /api/lexicon/search               - Search lexicon terms
POST   /api/lexicon/add-canonical        - Add canonical term
DELETE /api/lexicon/remove-canonical     - Remove canonical term
POST   /api/lexicon/add-category         - Add new category
DELETE /api/lexicon/delete-category      - Delete category
GET    /api/protect_words                - Get protected words
POST   /api/protect_words                - Save protected words
DELETE /api/protect_words/{word}         - Delete individual protected word
```

### **🔧 COMPREHENSIVE API TESTING**

#### **Main Test Interface**
- **URL**: http://localhost:8089/api-test
- **File**: `test_pages/api_test_complete.html`
- **Features**: 
  - Tests ALL unified server endpoints
  - Automatic token management
  - File upload testing with validation
  - Live API status monitoring
  - Comprehensive error reporting

#### **Enhanced File Upload Testing**
The test page now includes comprehensive file upload validation:
- ✅ File size validation (25MB OpenAI limit)
- ✅ Format validation (WAV, MP3, M4A, OGG, FLAC, MP4, WebM)
- ✅ Empty file detection
- ✅ Progress reporting during base64 conversion
- ✅ Audio duration warnings (minimum 0.1s)
- ✅ Detailed error messages for troubleshooting

## 🎤 **FILE UPLOAD TRANSCRIPTION WORKFLOW**

### **Complete Technical Flow**

#### 1. **Frontend File Selection**
```javascript
// Enhanced validation in testTranscribe() function
const fileInput = document.getElementById('audioFileInput');
const file = fileInput.files[0];

// Comprehensive validation
- File size check (25MB limit)
- Empty file detection
- Format validation
- Duration estimation
```

#### 2. **Base64 Conversion** 
```javascript
// Handle large files properly
const arrayBuffer = await file.arrayBuffer();
const uint8Array = new Uint8Array(arrayBuffer);

// Convert in chunks to avoid "too many function arguments" error
let binary = '';
const chunkSize = 8192;
for (let i = 0; i < uint8Array.length; i += chunkSize) {
    const chunk = uint8Array.slice(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, chunk);
}
const base64Audio = btoa(binary);
```

#### 3. **API Request**
```javascript
POST /api/ai/transcribe
{
    "audio_data": "UklGRi4AAABXQVZFZm10...",  // Base64 WAV
    "language": "nl",                          // Dutch
    "prompt": "Dutch dental terminology",      // Dental context
    "format": "wav"                           // File format
}
```

#### 4. **Server Processing**
- Base64 decode to audio buffer
- Send to OpenAI GPT-4o-transcribe API
- Apply dental-specific prompts
- Return transcribed text

#### 5. **Response**
```json
{
    "text": "element 26 distale restauratie met composiet",
    "language": "nl", 
    "duration": 3.2,
    "provider": "openai",
    "model": "gpt-4o-transcribe"
}
```

## 🌐 **FRONTEND INTEGRATION**

### **React Frontend Repository**
- **GitHub**: https://github.com/jwvaartjes/dental-asr-unified-server
- **Location**: `/private/tmp/dental-scribe-glow/`
- **Technology Stack**: React 18, TypeScript, Vite, Tailwind CSS
- **Development**: `cd /private/tmp/dental-scribe-glow && npm run dev`

### **⚠️ IMPORTANT: Repository Migration**
The frontend repository has been migrated to a new GitHub location:
- **NEW**: https://github.com/jwvaartjes/dental-asr-unified-server (Current)
- **OLD**: https://github.com/jwvaartjes/dental-scribe-glow.git (Deprecated)

Always use the NEW repository for the latest unified server and frontend code.

### **Key Integration Points**
1. **API Communication**: All endpoints on unified server port 8089
2. **WebSocket Connection**: Real-time pairing and audio streaming
3. **File Upload**: Drag-and-drop audio file transcription
4. **Device Pairing**: Desktop-mobile connection management

## ☁️ **CLOUD INFRASTRUCTURE**

### **Supabase Requirements**
All data storage uses Supabase cloud database:

**Environment Variables:**
```bash
SUPABASE_URL=your-project-url.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
JWT_SECRET=your-secret-key
```

**Database Tables:**
- `users` - User authentication & roles
- `configs` - Application settings (JSONB)
- `lexicons` - Dental terminology (hierarchical)
- `custom_patterns` - User-defined mappings
- `protect_words` - Protected terminology
- `audit_log` - Activity tracking

### **OpenAI Integration**
**Required Environment Variables:**
```bash
OPENAI_API_KEY=your-openai-api-key
MODEL_ID=openai/gpt-4o-transcribe
```

## 🚀 **DEPLOYMENT & USAGE**

### **Starting the Unified Server**
```bash
# Navigate to unified server directory
cd /Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace/pairing_server

# Start unified server (handles EVERYTHING)
python3 -m app.main
```

**Server will start on:**
- **Main Server**: http://localhost:8089
- **API Documentation**: http://localhost:8089/docs
- **Test Suite**: http://localhost:8089/api-test
- **Health Check**: http://localhost:8089/health

### **Complete Feature Access**
Once the server is running, access all features:

1. **File Transcription**: Upload audio files via test page
2. **Device Pairing**: Test desktop-mobile pairing
3. **API Testing**: Comprehensive endpoint testing
4. **WebSocket**: Real-time communication testing
5. **Authentication**: Login and token management
6. **Lexicon Management**: Add/edit dental terminology

## 🧪 **TESTING INFRASTRUCTURE**

### **Built-in Test Pages**
- **API Test Suite**: `/api-test` - Complete endpoint testing
- **Desktop Pairing**: `/test-desktop.html` - Desktop pairing test
- **Mobile Pairing**: `/test-mobile-local.html` - Mobile pairing test  
- **Rate Limiting**: `/test-rate-limiter` - Rate limit testing

### **Test Categories Covered**
- 🔐 Authentication (login, tokens, email validation)
- 🎵 AI/ASR (file transcription, model info, status)
- 📱 Device Pairing (code generation, pairing validation)
- 📚 Lexicon Management (CRUD operations, search)
- 🛡️ Security (rate limiting, origin validation)
- 🔌 WebSocket (real-time communication)

## 📊 **CURRENT STATUS (September 12, 2025)**

### **✅ COMPLETED FEATURES**
- **Unified Server Architecture**: Single server for all operations
- **OpenAI GPT-4o-transcribe**: File upload transcription working
- **Enhanced Validation**: Comprehensive file validation & error handling
- **Authentication System**: Complete JWT-based auth with proper role handling
- **Device Pairing**: Full desktop-mobile pairing system
- **API Test Suite**: Comprehensive testing interface
- **Lexicon Management**: Complete CRUD operations
- **Security**: Rate limiting, origin validation, JWT tokens
- **Normalization Pipeline**: Dutch dental terminology fixes applied
- **Element Parsing**: Fixed comma-separated list regex
- **Web-based Testing**: Complete test runner with comprehensive test suite

### **🔧 RECENT FIXES (September 12, 2025)**
- **Server Restart**: Successfully restarted unified server on port 8089
- **Element Parsing Regex**: Fixed to prevent "1, 2, 3" becoming "element 12, 3" 
- **Phonetic Matching**: Implemented gated boosting to prevent false positives like "lich" → "laesie"
- **Web Test Runner**: Added comprehensive test suite with 25 test cases
- **Git Integration**: Committed and pushed all changes to GitHub
- **Test Coverage**: Added ALL requested tests including "licht-mucosaal" and "interproximaal"

### **📋 TECHNICAL HIGHLIGHTS**
1. **Single Command Deploy**: `python3 -m app.main` starts everything
2. **OpenAI Integration**: State-of-the-art transcription with dental prompts  
3. **Comprehensive Testing**: Built-in test pages for all functionality
4. **Modern Architecture**: FastAPI, modular design, dependency injection
5. **Cloud-First**: Supabase integration for all data persistence
6. **Production Ready**: Rate limiting, security, error handling

## 🔗 **QUICK START COMMANDS**

```bash
# Start unified server (EVERYTHING)
cd /Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace/pairing_server
python3 -m app.main

# Test file transcription
curl -X POST http://localhost:8089/api-test
# Click "Test File Transcription" and upload audio file

# Test device pairing  
# Open: http://localhost:8089/test-desktop.html (desktop)
# Open: http://localhost:8089/test-mobile-local.html (mobile)

# Check API documentation
open http://localhost:8089/docs

# Monitor server logs
tail -f logs/app.log  # If logging to file is configured
```

## 📝 **MIGRATION NOTES**

### **From Legacy Server (server_windows_spsc.py)**
The old Windows server is now DEPRECATED. All functionality has been migrated to the unified server:

**Old (DEPRECATED):**
```bash
python3 server_windows_spsc.py 3001  # ❌ DON'T USE
```

**New (CURRENT):**
```bash
cd pairing_server && python3 -m app.main  # ✅ USE THIS
```

**What Changed:**
- ✅ Port 8089 instead of 3001
- ✅ Modular FastAPI architecture
- ✅ Built-in OpenAI integration
- ✅ Enhanced file upload validation
- ✅ Comprehensive test suite
- ✅ Better error handling
- ✅ Modern dependency injection

---
Version: 5.0.0 | Last Updated: 2025-09-11
**UNIFIED PIPELINE - OpenAI GPT-4o-transcribe Integration Complete**

**Major Changes:**
- **UNIFIED ARCHITECTURE**: Single server (port 8089) handles ALL functionality
- **OPENAI INTEGRATION**: GPT-4o-transcribe with enhanced file upload validation  
- **COMPREHENSIVE TESTING**: Built-in test pages for all features
- **ENHANCED VALIDATION**: File size, format, duration validation
- **FIXED AUTH ISSUES**: Proper role handling, realistic email validation
- **DEPRECATED LEGACY**: Old server_windows_spsc.py no longer needed
- **PRODUCTION READY**: Complete API suite with security & error handling


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

#Normalisatie-pipeline (herschreven + up-to-date)

Deze pipeline zet ruwe transcriptietekst om naar een canonieke medische/dentale vorm. Ze is deterministisch, fail-fast bij onvolledige configuratie, en reproduceert alle “slimmigheden” van het oude systeem.

Volgorde (stap-voor-stap)

Protected wrap

Laadt protected words (uit Supabase).

Wrapt altijd met sentinels op woordgrenzen (zonder lookahead): zo blijven woorden als op, Paro onaangetast (ook midden in de zin).

Protected segmenten worden in alle volgende stappen overgeslagen.

0.5 Unicode normalisatie

Zet input naar NFC (diacritics stabiel: cariüs → cariës).

Preprocessing

Spacefix rond separators voor cijfers (bv. in 1-4), NBSP → spatie, trimmen.

Element parsing (robuust)

Herkent cijferparen 1-4, 1 4, 1,4 → element 14.

Negative lookbehind voorkomt dubbel prefix: element 14 blijft element 14.

Comma-list guard: sequenties als 1, 2, 3 blijven ongemoeid (geen “element 12, 3”).

“de 11”-regel: de 11 → element 11.

Telwoord-paren ook buiten context: twee vier / een vier → element 24 / element 14.

Unit-guard: géén element-conversie als er direct een unit volgt: 15 mm blijft meetwaarde (gaat later naar 15mm).

Learnable / Custom patterns

Regels uit Supabase (regex/patterns).

Matching gebeurt accent-agnostisch; vervangen met canonieke vorm; punctuatie wordt bewaard.

Variant generation (uitgebreid)

Eén- en multi-woord varianten met flexibele gaps (spatie of -, meerdere spaties) en punctuatie-preserve.

Voorbeeld: bot verlies, bot-verlies, bot verlies, → botverlies,

Telwoord→cijfer mapping (bv. één → 1; let op: een alleen contextueel indien geconfigureerd).

Doel: vóór fuzzy al zoveel mogelijk naar canoniek.

4.5 Hyphen-prepass (vóór phonetic)

Niet-canonieke woord-woord hyphens worden gesplitst naar spatie → triggert multi-woord veto in fuzzy.

Canonieke hyphen-termen (uit lexicon/variants/pattern-dst) blijven intact.

Numerieke ranges (1-4) blijven ongemoeid.

Phonetic/Fuzzy normalize (multi-woord, veto, minima)

Verplicht de geavanceerde DutchPhoneticMatcher.normalize(...) (geen fallback).

Kandidaat-set = alleen echte canonicals (keys uit lexicon); géén dict.values() of pattern-dst in canonicals.

Multi-woord scoring met safeguards:

Per-woord veto: als één woordscore < 0.60 ⇒ hele match afwijzen.

Gemiddelde minima: bigrams ≥ 0.70; ≥3 woorden ≥ 0.75.

require_all_words = true (conservatief aligneren).

Phonetic boost = tie-breaker, geen katapult:

Alleen voor top-1 (of near-top) op base-score.

Gated met floor (≥ 0.60), minimale lengte (≥ 5), en core-check (generieke prefixen zoals inter-/mesio-/disto- tellen niet mee).

Morfologie-guard: promoot géén verb/adj. (-eer/-air/-aal/...) naar Latijns znw. (-um/-us/...).

Gated Soundex: alleen mengen wanneer base al ≥ floor.

Uitvoer is canoniek mét diacritics; numerieke tokens en protected blijven ongemoeid.

5.5 Diacritics-restore (defensie)

Token-wise map {fold(canoniek) → canoniek} zet per ongeluk accentloze hits terug naar bv. cariës.

Postprocessing

Spaties/punctuatie opschonen.

Unit-compact: 30 % → 30%, 15 mm → 15mm (symbolisch en alfabetisch afzonderlijk afgehandeld).

Dedupes: element element → element, element 14 element 14 → element 14.

de element → element.

Protected unwrap

Sentinels verwijderen; protected tekst staat exact zoals ingevoerd.
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
