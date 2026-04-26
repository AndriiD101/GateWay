# GateWay - Architecture Diagrams

## 1. High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Vanilla JavaScript + HTML/CSS (nginx reverse proxy)              │  │
│  │ - Single Page App (SPA)                                          │  │
│  │ - JWT token management                                          │  │
│  │ - Image upload & chat interface                                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    HTTPS/HTTP (Docker Network Bridge)
                                    │
┌────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Python 3.11 + FastAPI + Uvicorn                                 │  │
│  │ ┌──────────────────────────────────────────────────────────┐    │  │
│  │ │ Authentication Router (/api)                             │    │  │
│  │ │ - Register, Login, User Management                       │    │  │
│  │ │ - JWT token creation, bcrypt validation                 │    │  │
│  │ └──────────────────────────────────────────────────────────┘    │  │
│  │ ┌──────────────────────────────────────────────────────────┐    │  │
│  │ │ Chat Router (/api/chat)                                  │    │  │
│  │ │ - Message persistence, history retrieval                │    │  │
│  │ └──────────────────────────────────────────────────────────┘    │  │
│  │ ┌──────────────────────────────────────────────────────────┐    │  │
│  │ │ AI Router (/ai/process)                                  │    │  │
│  │ │ - Image upload, Bedrock inference, PDF generation       │    │  │
│  │ └──────────────────────────────────────────────────────────┘    │  │
│  │ ┌──────────────────────────────────────────────────────────┐    │  │
│  │ │ Trip Router (/trips)                                     │    │  │
│  │ │ - CRUD operations for trips                             │    │  │
│  │ └──────────────────────────────────────────────────────────┘    │  │
│  │ ┌──────────────────────────────────────────────────────────┐    │  │
│  │ │ Utility Routers (/blob, /db)                            │    │  │
│  │ │ - Health checks, test endpoints                         │    │  │
│  │ └──────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
  │                    │                     │
  │                    │                     │
  ▼                    ▼                     ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Azure SQL   │  │ Azure Blob   │  │  AWS Bedrock     │
│ Database    │  │ Storage      │  │  (Nova Lite)     │
│             │  │              │  │                  │
│ • users     │  │ • Images     │  │ • AI Inference   │
│ • trips     │  │ • PDFs       │  │ • Itinerary gen  │
│ • chat_msgs │  │ • Signed URLs│  │ • JSON parsing   │
└─────────────┘  └──────────────┘  └──────────────────┘
```

## 2. API Request Flow Diagram

```
USER REQUEST → NGINX (Reverse Proxy)
                ↓
         ┌──────────────┐
         │ Route Match? │
         └──────────────┘
         /  /api  /ai  /trips  /blob  /db  /  (static)
        /      │       │       │      │   │   │
       /       │       │       │      │   │   └─→ Static Files (index.html, CSS, JS)
      /        │       │       │      │   │
     /         │       │       │      │   └─────→ nginx Built-in (health, error pages)
    /          │       │       │      │
   /           │       │       │      └───────────→ FastAPI Router (db_test.py)
  /            │       │       │                    - SELECT 1 check
 /             │       │       └────────────────────→ FastAPI Router (blob.py)
│              │       │                            - Blob connectivity
│              │       │
│              │       └────────────────────────────→ FastAPI Router (ai.py)
│              │                                    - /ai/process
│              │                                    - Upload image → Bedrock → PDF
│              │
│              └──────────────────────────────────→ FastAPI Router (auth, chat, trips)
│                                                  - JWT verification
│                                                  - DB queries
│                                                  - Response serialization
│
└─ FastAPI Exception Handling
   - HTTPException → HTTP error response
   - Validation error → 422 Unprocessable Entity
   - Auth failure → 401 Unauthorized
```

## 3. Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER REGISTRATION                             │
└─────────────────────────────────────────────────────────────────┘

Frontend                Backend                Database
  │                       │                       │
  ├─ POST /api/register   │                       │
  │─ {username, pwd} ────→│                       │
  │                       ├─ Hash pwd (bcrypt)    │
  │                       ├─ Check unique email   │
  │                       ├─ Create User ────────→│
  │                       │ INSERT INTO users     │
  │                       │←────────────────────│
  │←─ 201 Created ────────│                       │
  │  {message}            │                       │

┌─────────────────────────────────────────────────────────────────┐
│                      USER LOGIN                                  │
└─────────────────────────────────────────────────────────────────┘

Frontend                Backend                Database
  │                       │                       │
  ├─ POST /api/login      │                       │
  │─ {username, pwd} ────→│                       │
  │                       ├─ Query user ────────→│
  │                       │ SELECT * FROM users  │
  │                       │←────────────────────│
  │                       ├─ bcrypt.verify(pwd, hash)
  │                       ├─ JWT encode {user_id, role}
  │←─ 200 OK ─────────────│
  │  {access_token}       │
  │                       │
  ├─ Save JWT to localStorage
  │
  ├─ Include in requests
  │─ Authorization: Bearer JWT ───→│ ✓ Verified
  │                                 │
  │                       ├─ jwt.decode(token)
  │                       ├─ Check expiry
  │                       ├─ Query user

┌─────────────────────────────────────────────────────────────────┐
│                        LOGOUT                                    │
└─────────────────────────────────────────────────────────────────┘

Frontend
  │
  ├─ Clear localStorage (remove JWT)
  │
  ├─ Redirect to login page
  │
  └─ Backend: No session to invalidate (stateless)
```

## 4. AI Trip Planning Flow

```
USER INTERACTION
  │
  ├─ [1] Upload Image + Type Prompt
  │       │
  │       └─→ Frontend: Display preview, enable send
  │
  └─→ [2] Click Send

FRONTEND
  │
  ├─ [3] Create FormData(image, prompt)
  │
  ├─ [4] POST /ai/process + JWT
  │       │
  │       └─→ Show "Analyzing..." spinner
  │

BACKEND: /ai/process Router
  │
  ├─ [5] Validate JWT → get user_id
  │
  ├─ [6] Upload image to blob
  │       ├─ Generate UUID filename
  │       ├─ POST to Azure Blob
  │       └─ Get image_url (unsigned)
  │
  ├─ [7] Call Bedrock Nova Lite
  │       ├─ Send image bytes + prompt
  │       ├─ System prompt: return JSON
  │       ├─ Parse response
  │       └─ Extract: city, itinerary[], budget, tips[]
  │
  ├─ [8] Generate PDF from itinerary
  │       ├─ Create PDF binary (minimal format)
  │       ├─ Upload to blob/reports/{uuid}.pdf
  │       └─ Generate SAS token (2-hour expiry)
  │       └─ Return signed URL with ?sv=...&sig=...
  │
  ├─ [9] Get or create demo user (for storage)
  │
  ├─ [10] Insert Trip record
  │        └─ INSERT INTO trips (user_id, city, image_url, itinerary_json, budget)
  │
  ├─ [11] Return JSON response
  │        {
  │          status, model_id, latency_ms,
  │          image_url, pdf_url,
  │          parsed: {city, itinerary, budget, tips},
  │          trip: {full trip object}
  │        }
  │

FRONTEND
  │
  ├─ [12] Parse response
  │
  ├─ [13] Format itinerary as readable text
  │
  ├─ [14] Add assistant message to chat UI
  │
  ├─ [15] Display PDF download link
  │        └─ <a href="{pdf_url}">Download PDF</a>
  │
  ├─ [16] POST /api/chat/message (save to history)
  │
  └─ [17] Remove spinner, enable send again

RESULT: User sees formatted itinerary + can download PDF + have persistent history
```

## 5. Database Schema Relationships

```
┌─────────────────┐
│     USERS       │
├─────────────────┤
│ id (PK)         │◄────┐
│ email (UNIQUE)  │     │
│ password_hash   │     │
│ username        │     │
│ role (user/adm) │     │
└─────────────────┘     │
        │               │
        │ 1:N          │
        ├──────────────┼─────────────────────┐
        │              │                     │
        ▼              ▼                     ▼
   ┌──────────┐  ┌──────────────┐    ┌──────────────────┐
   │  TRIPS   │  │CHAT_MESSAGES │    │ (Admin Access)   │
   ├──────────┤  ├──────────────┤    │ Can view all     │
   │id (PK)   │  │id (PK)       │    │ users & trips    │
   │user_id*  │  │user_id*      │    │ Can manage roles │
   │city      │  │role          │    │ Can delete users │
   │image_url │  │message       │    │                  │
   │itinerary │  │created_at    │    └──────────────────┘
   │budget    │  └──────────────┘
   └──────────┘

Cascade Delete: User → Trips & Chat messages automatically deleted
```

## 6. Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   FRONTEND (Browser)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ gateway_auth.js                                         │    │
│  │ • Login/Register handlers                              │    │
│  │ • JWT token lifecycle (save/clear)                     │    │
│  │ • Session validation on page load                      │    │
│  │ • Auth UI state (show/hide profile)                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ script.js (Chat & Main App)                            │    │
│  │ • Chat message send                                    │    │
│  │ • Image upload & preview                              │    │
│  │ • Call /ai/process                                    │    │
│  │ • Display formatted responses                         │    │
│  │ • PDF download link generation                        │    │
│  │ • Message persistence                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │ HTTP (w/ JWT header)
         │
┌────────▼──────────────────────────────────────────────────────┐
│           NGINX (Reverse Proxy)                                │
│ • Route /api, /ai, /trips → http://backend:8000              │
│ • Serve static files (index.html, CSS, JS)                   │
│ • Cache static assets (30 days)                              │
│ • Pass auth headers                                          │
└────────┬──────────────────────────────────────────────────────┘
         │ Docker Network
         │
┌────────▼──────────────────────────────────────────────────────┐
│           FASTAPI BACKEND                                      │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ config.py: Load env vars                                │  │
│ │ auth.py: JWT, bcrypt                                    │  │
│ │ database.py: SQLAlchemy engine                          │  │
│ │ models.py: ORM (User, Trip, ChatMessage)               │  │
│ │ services.py: Bedrock, Blob, PDF                        │  │
│ │ routers/: 6 routers (auth, chat, trips, ai, blob, db) │  │
│ └──────────────────────────────────────────────────────────┘  │
└────────┬───────────────┬────────────────┬──────────────────────┘
         │               │                │
    ┌────▼───────────────▼─────────────────▼────┐
    │                                             │
    ▼                   ▼                    ▼
┌──────────┐    ┌──────────────┐  ┌─────────────────┐
│Azure SQL │    │ Azure Blob   │  │ AWS Bedrock     │
│Database  │    │ Storage      │  │ (nova-lite)     │
│          │    │              │  │                 │
│TCP:1433  │    │ HTTPS API    │  │ HTTPS API       │
└──────────┘    └──────────────┘  └─────────────────┘
```

## 7. Security Flow

```
┌─────────────────────────────────────────────────────────┐
│           REQUEST WITH JWT AUTHENTICATION                │
└─────────────────────────────────────────────────────────┘

Frontend
  │
  ├─ Get JWT from localStorage
  │
  ├─ Add to request header:
  │  Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  │
  └─→ Send request

Backend (app/auth.py)
  │
  ├─ Extract JWT from Authorization header
  │
  ├─ Decode JWT with SECRET_KEY
  │
  ├─ Verify signature (HMAC-SHA256)
  │
  ├─ Check expiry (exp claim)
  │
  ├─ Extract user_id & role
  │
  ├─ (Optional) Verify admin role for admin endpoints
  │
  └─→ Allow or deny request

┌─────────────────────────────────────────────────────────┐
│              BLOB SAS TOKEN GENERATION                   │
└─────────────────────────────────────────────────────────┘

Backend (upload_trip_report_pdf_to_blob)
  │
  ├─ Generate SAS token
  │  ├─ Account name: gatewayimagescloudapp
  │  ├─ Container: travel-images
  │  ├─ Blob: reports/{uuid}.pdf
  │  ├─ Account key: (from connection string)
  │  ├─ Permission: read only
  │  ├─ Expiry: now + 2 hours
  │  └─ Sign with HMAC-SHA256
  │
  ├─ Construct URL:
  │  https://account.blob.core.windows.net/container/blob?sv=2021-06&...&sig=BASE64_SIG
  │
  └─→ Return URL to frontend

Browser (PDF Download)
  │
  ├─ Open PDF URL (includes SAS token)
  │
  ├─ Azure Blob validates:
  │  ├─ Account key matches signature
  │  ├─ Token not expired
  │  ├─ Permission is read
  │
  └─→ Allow download

┌─────────────────────────────────────────────────────────┐
│              PASSWORD HASHING (bcrypt)                   │
└─────────────────────────────────────────────────────────┘

Registration
  User enters: "MyPassword123!"
             ↓
     bcrypt.hashpw() with random salt
             ↓
     Stored in DB: $2b$12$abc123...xyz789 (60 chars)
             ↓
     Original password never stored

Login
  User enters: "MyPassword123!"
             ↓
     bcrypt.checkpw(pwd, hash_from_db)
             ↓
     If matches → issue JWT
     If no match → 401 Unauthorized
```

---

*All diagrams show logical flow and component relationships. Actual network topology in Azure Container Apps may vary.*
