# Frontend API Integration Guide - Dental ASR System

## 🔑 **AUTHENTICATION SETUP (CRITICAL)**

**ALL REST API calls MUST include `credentials: 'include'` for httpOnly cookie authentication:**

```typescript
// ✅ CORRECT - Include httpOnly cookies:
const response = await fetch('http://localhost:8089/api/lexicon/categories', {
  credentials: 'include'  // Required for authentication!
});

// ❌ WRONG - Will get 401 Unauthorized:
fetch('http://localhost:8089/api/lexicon/categories')  // No cookies sent
```

### **Global API Client Setup**

```typescript
// Option 1: Axios global configuration
import axios from 'axios';
axios.defaults.withCredentials = true;
axios.defaults.baseURL = 'http://localhost:8089';

// Option 2: Custom fetch wrapper
const apiCall = async (url: string, options: RequestInit = {}) => {
  return fetch(`http://localhost:8089${url}`, {
    ...options,
    credentials: 'include'  // Always include httpOnly cookies
  });
};

// Option 3: React hook
const useAuthenticatedFetch = () => {
  return useCallback((url: string, options: RequestInit = {}) => {
    return fetch(`http://localhost:8089${url}`, {
      ...options,
      credentials: 'include'
    });
  }, []);
};
```

---

## 🔐 **AUTHENTICATION API**

### **Login Flow**

```typescript
// 1. Check if email exists and get role
const emailCheck = await fetch(`/api/auth/check-email?email=${email}`, {
  credentials: 'include'
});
const { exists, role, is_admin } = await emailCheck.json();

if (is_admin) {
  // Admin accounts: show password field immediately
  // NO magic link attempts for admin/super_admin accounts
} else {
  // Regular users: can use magic link
}

// 2a. Regular login (required for admin accounts)
const loginResponse = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ email, password })
});

// 2b. Magic link login (blocked for admin accounts)
const magicResponse = await fetch('/api/auth/login-magic', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ email })
});
```

### **Authentication Status**

```typescript
// Check authentication status
const statusResponse = await fetch('/api/auth/status', {
  credentials: 'include'
});
const { authenticated, user } = await statusResponse.json();
// user: { id, email, name, role, permissions }

// Check token validity and expiration
const tokenStatus = await fetch('/api/auth/token-status', {
  credentials: 'include'
});
const { valid, expired, expires_at, should_refresh_soon } = await tokenStatus.json();
```

### **Logout**

```typescript
const logoutResponse = await fetch('/api/auth/logout', {
  method: 'POST',
  credentials: 'include'
});
// Clears all httpOnly cookies securely
```

---

## 📚 **LEXICON MANAGEMENT API**

**All lexicon endpoints require admin or super_admin role**

### **Categories**

```typescript
// Get all categories
const categories = await fetch('/api/lexicon/categories', {
  credentials: 'include'
});
const { categories } = await categories.json();

// Add new category
await fetch('/api/lexicon/add-category', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ category: 'new_category_name' })
});

// Delete category
await fetch('/api/lexicon/delete-category', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ category: 'category_to_delete' })
});
```

### **Canonical Terms**

```typescript
// Add canonical term
await fetch('/api/lexicon/add-canonical', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    term: 'new_term',
    category: 'rx_findings'
  })
});

// Remove canonical term
await fetch('/api/lexicon/remove-canonical', {
  method: 'DELETE',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    term: 'term_to_remove',
    category: 'rx_findings'
  })
});

// Get terms in category
const terms = await fetch('/api/lexicon/terms/rx_findings', {
  credentials: 'include'
});
const { category, terms, count } = await terms.json();
```

### **Search & Full Lexicon**

```typescript
// Search lexicon
const searchResults = await fetch('/api/lexicon/search?q=element', {
  credentials: 'include'
});
const { query, count, results } = await searchResults.json();

// Get complete lexicon (cached - very fast)
const fullLexicon = await fetch('/api/lexicon/full', {
  credentials: 'include'
});
const { lexicon, categories, source } = await fullLexicon.json();
```

### **Variants & Abbreviations**

```typescript
// Add variant with auto-detection
await fetch('/api/lexicon/add-variant-auto', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    canonical_term: 'cariës',
    variant: 'caries'
  })
});

// Add multi-word variant
await fetch('/api/lexicon/add-multiword-variant-auto', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    canonical_term: 'endodontische behandeling',
    variant_phrase: 'wortel kanaal behandeling'
  })
});

// Get variants for category
const variants = await fetch('/api/lexicon/variants/rx_findings', {
  credentials: 'include'
});
const { category, variants, count } = await variants.json();
```

### **Protected Words**

```typescript
// Get protected words
const protectedWords = await fetch('/api/protect_words', {
  credentials: 'include'
});
const { protected_words } = await protectedWords.json();

// Save protected words
await fetch('/api/protect_words', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    protected_words: ['Paro', 'Cito', 'new_word']
  })
});

// Delete single protected word
await fetch('/api/protect_words/word_to_delete', {
  method: 'DELETE',
  credentials: 'include'
});
```

---

## 👥 **USER MANAGEMENT API**

**All user endpoints require admin role. Some require super_admin role.**

### **User Listing & Stats**

```typescript
// Get user statistics (admin required)
const stats = await fetch('/api/users/stats', {
  credentials: 'include'
});
const { total_users, active_users, admin_users } = await stats.json();

// Get paginated user list with filtering (admin required)
const users = await fetch('/api/users/?page=1&limit=20&search=dental&role=all&status=active', {
  credentials: 'include'
});
const { users, pagination } = await users.json();

// Get specific user details (admin required)
const user = await fetch('/api/users/76c7198e-710f-41dc-b26d-ce728571a546?include_activity=true', {
  credentials: 'include'
});
const { data } = await user.json();
```

### **User Operations (Admin Required)**

```typescript
// Update user information
await fetch('/api/users/user-id', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    name: 'New Name',
    email: 'new@email.com'
  })
});

// Activate user account
await fetch('/api/users/user-id/activate', {
  method: 'POST',
  credentials: 'include'
});

// Deactivate user account
await fetch('/api/users/user-id/deactivate', {
  method: 'POST',
  credentials: 'include'
});
```

### **Super Admin Operations (Super Admin Required)**

```typescript
// Grant admin privileges (super_admin only)
await fetch('/api/users/user-id/make-admin', {
  method: 'POST',
  credentials: 'include'
});

// Remove admin privileges (super_admin only)
await fetch('/api/users/user-id/remove-admin', {
  method: 'POST',
  credentials: 'include'
});

// Delete user account (super_admin only)
await fetch('/api/users/user-id', {
  method: 'DELETE',
  credentials: 'include'
});
```

### **Bulk Operations**

```typescript
// Bulk operations (admin required, some actions need super_admin)
await fetch('/api/users/bulk', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    action: 'activate',  // activate, deactivate, delete, make_admin, remove_admin
    user_ids: ['user-id-1', 'user-id-2']
  })
});
// Note: delete, make_admin, remove_admin require super_admin role
```

---

## 🎵 **AUDIO TRANSCRIPTION API**

### **File Upload Transcription**

```typescript
// Upload audio file for transcription
const formData = new FormData();
formData.append('file', audioFile);
formData.append('language', 'nl');
formData.append('prompt', 'Dutch dental terminology');

const transcription = await fetch('/api/ai/transcribe', {
  method: 'POST',
  credentials: 'include',  // Include cookies
  body: formData
});
const { text, raw, normalized, language, duration } = await transcription.json();
```

### **Real-time WebSocket Streaming**

```typescript
// 1. Get WebSocket token (uses httpOnly cookies for auth)
const tokenResponse = await fetch('/api/auth/ws-token', {
  method: 'POST',
  credentials: 'include'
});
const { token } = await tokenResponse.json();

// 2. Connect WebSocket with Bearer token
const ws = new WebSocket('ws://localhost:8089/ws', ['Bearer', token]);

// 3. Identify as desktop
ws.send(JSON.stringify({
  type: 'identify',
  device_type: 'desktop',
  session_id: 'desktop-' + Date.now()
}));

// 4. Send binary audio data
ws.send(audioBuffer);  // Raw PCM or WAV data

// 5. Receive transcription results with session formatting
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcription_result') {
    console.log('Current chunk:', data.text);
    console.log('Raw chunk:', data.raw);
    console.log('Normalized chunk:', data.normalized);

    // NEW: Complete session with automatic line breaks between speech segments
    console.log('Full session:', data.session_text);  // Paragraph formatted!
    console.log('Chunk count:', data.chunk_count);     // Number of speech segments

    // Frontend options:
    // Option 1: Show real-time chunks
    displayCurrentChunk(data.text);

    // Option 2: Show complete session with paragraph formatting
    displayCompleteTranscription(data.session_text);

    // Option 3: Both - real-time + formatted session
    showChunkNotification(data.text);
    updateMainTranscription(data.session_text);
  }
};
```

---

## 📱 **MOBILE PAIRING API**

### **Desktop Pairing Flow**

```typescript
// 1. Generate pairing code (desktop)
const codeResponse = await fetch('/api/generate-pair-code', {
  method: 'POST',
  credentials: 'include'
});
const { code, channelId, expiresIn } = await codeResponse.json();

// 2. Show code to user for 5 minutes
// User enters code on mobile device
```

### **Mobile Pairing Flow**

```typescript
// 1. Pair with code (mobile)
const pairResponse = await fetch('/api/pair-device', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code: '123456' })
});
const { success, channelId } = await pairResponse.json();

// 2. Get mobile WebSocket token
const tokenResponse = await fetch('/api/auth/ws-token-mobile', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pair_code: '123456' })
});
const { token } = await tokenResponse.json();

// 3. Connect WebSocket (mobile inherits desktop auth)
const ws = new WebSocket('ws://localhost:8089/ws', ['Bearer', token]);
```

---

## 🏥 **AI PROVIDER & CONFIG API**

```typescript
// Get AI provider status
const aiStatus = await fetch('/api/ai/status', {
  credentials: 'include'
});

// Get model information
const modelInfo = await fetch('/api/ai/model-info', {
  credentials: 'include'
});

// Get normalization config
const normConfig = await fetch('/api/ai/normalization/config', {
  credentials: 'include'
});
```

---

## 📋 **CONSULTATION TEMPLATES API**

```typescript
// Get all templates
const templates = await fetch('/api/consultation-templates/', {
  credentials: 'include'
});

// Get active template
const activeTemplate = await fetch('/api/consultation-templates/active/current', {
  credentials: 'include'
});

// Create new template
await fetch('/api/consultation-templates/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    name: 'Template Name',
    structure: { sections: [] }
  })
});
```

---

## 🚨 **ERROR HANDLING**

```typescript
const handleApiCall = async (url: string, options: RequestInit = {}) => {
  try {
    const response = await fetch(`http://localhost:8089${url}`, {
      ...options,
      credentials: 'include'
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Authentication required - redirect to login
        window.location.href = '/login';
        return;
      }

      if (response.status === 403) {
        // Insufficient privileges
        throw new Error('Insufficient privileges for this operation');
      }

      const errorData = await response.json();
      throw new Error(errorData.detail || 'API request failed');
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};
```

---

## 🎯 **ROLE-BASED ACCESS**

### **User Roles & Permissions**

```typescript
interface UserPermissions {
  canManageUsers: boolean;      // Admin + Super Admin
  canDeleteUsers: boolean;      // Admin + Super Admin
  canModifyAdminRoles: boolean; // Super Admin only
  isSuperAdmin: boolean;        // Super Admin only
}

// Check user permissions from auth status
const { user } = await fetch('/api/auth/status', { credentials: 'include' }).then(r => r.json());

if (user.role === 'super_admin') {
  // Can access: user management, lexicon, all operations
} else if (user.role === 'admin') {
  // Can access: lexicon, most user operations (not make/remove admin, delete)
} else {
  // Regular user: limited access
}
```

### **Frontend Component Logic**

```typescript
const LexiconManagement = () => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check auth status on component mount
    fetch('/api/auth/status', { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        if (data.authenticated && data.user.role === 'super_admin') {
          setUser(data.user);
        } else {
          // Redirect or show access denied
        }
      });
  }, []);

  const loadCategories = async () => {
    const response = await fetch('/api/lexicon/categories', {
      credentials: 'include'
    });
    return response.json();
  };
};
```

---

## 🔧 **WEBSOCKET AUTHENTICATION**

```typescript
// WebSocket requires Bearer token (not httpOnly cookies)
class AudioStreaming {
  private ws: WebSocket | null = null;

  async connect() {
    // 1. Get WebSocket token using httpOnly cookies
    const tokenResponse = await fetch('/api/auth/ws-token', {
      method: 'POST',
      credentials: 'include'  // Uses httpOnly cookies for auth
    });
    const { token } = await tokenResponse.json();

    // 2. Connect WebSocket with Bearer token
    this.ws = new WebSocket('ws://localhost:8089/ws', ['Bearer', token]);

    this.ws.onopen = () => {
      // 3. Identify device
      this.ws.send(JSON.stringify({
        type: 'identify',
        device_type: 'desktop',
        session_id: `desktop-${Date.now()}`
      }));
    };
  }

  sendAudio(audioBuffer: ArrayBuffer) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(audioBuffer);  // Send binary audio
    }
  }
}
```

---

## 🎯 **COMPLETE ENDPOINT REFERENCE**

### **Authentication Endpoints**
- `POST /api/auth/login` - Regular login (httpOnly cookies)
- `POST /api/auth/login-magic` - Magic link (blocked for admins)
- `GET /api/auth/check-email?email=` - Check email existence and role
- `GET /api/auth/status` - Authentication status
- `GET /api/auth/token-status` - Token validity check
- `POST /api/auth/logout` - Secure logout
- `POST /api/auth/ws-token` - WebSocket token for desktop
- `POST /api/auth/ws-token-mobile` - WebSocket token for mobile

### **Lexicon Endpoints (Admin + Super Admin)**
- `GET /api/lexicon/categories` - List categories
- `GET /api/lexicon/terms/{category}` - Get category terms
- `GET /api/lexicon/full` - Complete lexicon (cached)
- `GET /api/lexicon/search?q=` - Search terms
- `POST /api/lexicon/add-canonical` - Add canonical term
- `DELETE /api/lexicon/remove-canonical` - Remove canonical term
- `POST /api/lexicon/add-category` - Add category
- `POST /api/lexicon/delete-category` - Delete category
- `POST /api/lexicon/add-variant-auto` - Add variant (auto-detect category)
- `POST /api/lexicon/add-multiword-variant-auto` - Add multi-word variant
- `GET /api/protect_words` - Get protected words
- `POST /api/protect_words` - Save protected words
- `DELETE /api/protect_words/{word}` - Delete protected word

### **User Management Endpoints**
**Admin Required:**
- `GET /api/users/` - List users (paginated, filterable)
- `GET /api/users/stats` - User statistics
- `GET /api/users/{user_id}` - Get user details
- `PUT /api/users/{user_id}` - Update user
- `POST /api/users/{user_id}/activate` - Activate user
- `POST /api/users/{user_id}/deactivate` - Deactivate user
- `POST /api/users/bulk` - Bulk operations

**Super Admin Required:**
- `POST /api/users/{user_id}/make-admin` - Grant admin privileges
- `POST /api/users/{user_id}/remove-admin` - Remove admin privileges
- `DELETE /api/users/{user_id}` - Delete user account
- `POST /api/users/bulk` (delete, make_admin, remove_admin actions)

### **AI & Transcription Endpoints**
- `POST /api/ai/transcribe` - File transcription
- `GET /api/ai/status` - Provider status
- `GET /api/ai/model-info` - Model information

### **WebSocket Endpoints**
- `WS /ws` - Real-time audio streaming (Bearer token auth)

---

## 🎯 **QUICK START EXAMPLE**

```typescript
// Complete example: Add dental term to lexicon
const addDentalTerm = async (term: string, category: string) => {
  try {
    const response = await fetch('/api/lexicon/add-canonical', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // 🔑 Critical for authentication!
      body: JSON.stringify({ term, category })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Failed to add dental term:', error);
    throw error;
  }
};

// Usage
await addDentalTerm('periapicaal', 'rx_findings');
```

---

## 🔒 **SECURITY NOTES**

1. **HttpOnly Cookies**: XSS protection, automatic management
2. **Admin Magic Login**: BLOCKED for security (use password)
3. **Role Separation**: Admin vs Super Admin privileges enforced
4. **WebSocket Tokens**: Short-lived (2 minutes), audio-only scope
5. **CORS Enabled**: For localhost:5173, localhost:8080, etc.

**Remember**: Always use `credentials: 'include'` for REST API calls! 🔑