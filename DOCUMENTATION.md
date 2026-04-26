# GateWay - Travel AI Trip Planner - Complete Documentation

## Executive Summary

**GateWay** is a full-stack web application that leverages AI to help users plan personalized travel itineraries. Users upload images or provide text prompts, the AI analyzes them, generates customized trip plans with budget estimates, and stores everything securely. The application combines modern cloud technologies for scalability, security, and global reach.

---

## 1. Task Analysis & Problem Definition

### What the Application Does

The core functionality addresses the problem: *How can travelers quickly get personalized trip itineraries without spending hours researching?*

**Primary Use Cases:**
- User uploads a photo of a destination → AI analyzes it → Returns customized itinerary with budget
- User types a travel prompt (e.g., "5-day trip to Barcelona, $2000 budget") → AI generates detailed plan
- Users can browse their chat history with the AI assistant
- Users can view and manage past trips they've planned
- Admin users can manage other users and oversee all trips in the system

### Problem Statement
- **Challenge**: Travel planning is time-consuming; users need instant, personalized recommendations
- **Solution**: AI-powered planning with secure multi-user accounts and persistent storage
- **Outcome**: Reduced planning time from hours to minutes, personalized recommendations, data persistence

---

## 2. Technology Stack Justification

### Why These Technologies?

| Component | Technology | Why Chosen |
|-----------|-----------|-----------|
| **Backend Framework** | FastAPI (Python) | Fast async HTTP, automatic API docs, type safety, easy to scale |
| **Database** | Azure SQL Server | Enterprise-grade, ACID compliance, global availability, integrated with Azure |
| **ORM** | SQLAlchemy | Database-agnostic, type-safe queries, relationship management |
| **Authentication** | JWT (JSON Web Tokens) | Stateless, scalable, standard in REST APIs, secure for multi-instance deployments |
| **Password Hashing** | bcrypt | Industry standard, resistant to brute force, automatically handles salt |
| **AI Model** | AWS Bedrock (Nova Lite) | Cross-cloud AI, no GPU needed, pay-per-use, supports image+text input |
| **File Storage** | Azure Blob Storage | Scalable object storage, SAS token support for secure downloads, cost-effective |
| **Frontend** | Vanilla JavaScript + HTML/CSS | No dependencies, fast load times, simple deployment via nginx |
| **Reverse Proxy** | nginx | Lightweight, efficient request routing, static file caching |
| **Containerization** | Docker & Docker Compose | Reproducible environments, local dev ≈ production |
| **Cloud Deployment** | Azure Container Apps | Serverless containers, automatic scaling, integrated with Azure services |
| **Container Registry** | Azure Container Registry (ACR) | Private image hosting, integrated authentication, geo-replicated |

### Why NOT Other Choices?
- **Not Django**: Overkill for this use case; FastAPI is lighter and faster
- **Not MongoDB**: Relational data structure (users → trips → chat) suits SQL better
- **Not Auth0**: Azure AD or JWT is simpler for internal team use
- **Not S3**: Azure Blob is already integrated with other Azure services
- **Not React/Vue**: Vanilla JS reduces build complexity; nginx serves static files efficiently

---

## 3. System Architecture & Service Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ nginx (Reverse Proxy & Static File Server)               │   │
│  │ - Serves HTML/CSS/JS                                     │   │
│  │ - Routes /api, /ai, /trips, /blob to backend             │   │
│  │ - Caches static assets (30 days)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                    HTTP/HTTPS │ (Docker Network)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND (Container)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ API Routers:                                             │   │
│  │ • /api/auth → JWT login/register/profile mgmt           │   │
│  │ • /api/chat → Chat history & message persistence         │   │
│  │ • /ai/process → Image/prompt analysis                    │   │
│  │ • /trips → Trip CRUD operations                          │   │
│  │ • /blob/health → Storage connectivity check              │   │
│  │ • /db/health → Database connectivity check               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
         │                           │                    │
         │                           │                    │
    ┌────▼──────┐          ┌─────────▼────┐    ┌────────▼────────┐
    │  AZURE    │          │ AZURE BLOB   │    │  AWS BEDROCK    │
    │   SQL     │          │  STORAGE     │    │   (Nova Lite)   │
    │ DATABASE  │          │              │    │                 │
    │           │          │ • trip PDFs  │    │ • Image analysis│
    │ • users   │          │ • images     │    │ • Text prompts  │
    │ • trips   │          │ • reports    │    │ • JSON output   │
    │ • chat    │          │              │    │                 │
    └───────────┘          └──────────────┘    └─────────────────┘
```

### Data Flow Diagram

```
USER WORKFLOW:

1. REGISTRATION/LOGIN
   Frontend → /api/register (JWT) → Database stores User + hashes password
   Frontend → /api/login (Credentials) → JWT token returned

2. AI TRIP PLANNING (Main Feature)
   Frontend → Upload Image + Prompt
                    ↓
            /ai/process endpoint
                    ↓
   ┌────────────────┬────────────────┬────────────────┐
   ↓                ↓                ↓                ↓
Upload to        Send to Bedrock  Parse JSON      Generate PDF
Azure Blob       Nova Lite        (city, budget)  & Upload
(get URL)        (AI analysis)                    (get SAS URL)
   │                │                │                │
   └────────────────┴────────────────┴────────────────┘
                    ↓
            Save Trip to Database
                    ↓
        Return: Trip data + PDF URL + Image URL

3. CHAT & PERSISTENCE
   Frontend → /api/chat/message (POST) → Save to DB
   Frontend → /api/chat/history (GET) → Load past messages

4. TRIP MANAGEMENT
   Frontend → /trips (GET) → List user's trips
   Frontend → /trips/{id} (GET) → View single trip
   Frontend → /trips (POST) → Manually create trip
   Frontend → /trips/{id} (DELETE) → Remove trip
```

---

## 4. Database Schema

### Table: users
```sql
CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY,
    email NVARCHAR(255) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    username NVARCHAR(255),
    role NVARCHAR(32) NOT NULL DEFAULT 'user'  -- 'user' or 'admin'
);
```
**Purpose**: User authentication, authorization, and profile storage

### Table: trips
```sql
CREATE TABLE trips (
    id INT PRIMARY KEY IDENTITY,
    user_id INT FOREIGN KEY REFERENCES users(id),
    detected_city NVARCHAR(255) NOT NULL,
    image_url NVARCHAR(1024) NOT NULL,
    itinerary TEXT NOT NULL,                -- JSON array of strings
    budget_estimate NUMERIC(12,2) NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);
```
**Purpose**: Store generated travel plans, user-specific trip history

### Table: chat_messages
```sql
CREATE TABLE chat_messages (
    id INT PRIMARY KEY IDENTITY,
    user_id INT FOREIGN KEY REFERENCES users(id),
    role NVARCHAR(32) NOT NULL,            -- 'user' or 'assistant'
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);
```
**Purpose**: Persistent chat history for users to review past AI conversations

---

## 5. API Endpoints Reference

### Authentication (`/api`)
| Method | Endpoint | Auth | Purpose | Request | Response |
|--------|----------|------|---------|---------|----------|
| POST | `/api/register` | None | Create account | `{username, password}` | `{message}` |
| POST | `/api/login` | None | Get JWT token | `{username, password}` | `{access_token, user_id, username, role}` |
| GET | `/api/me` | JWT | Get profile | — | `{id, username, role}` |
| PUT | `/api/me` | JWT | Update profile | `{username?, password?}` | `{message}` |
| DELETE | `/api/me` | JWT | Delete account | — | `{message}` |
| GET | `/api/users` | Admin | List all users | — | `[{id, username, role}]` |
| GET | `/api/users/{id}` | JWT* | Get user details | — | `{id, username, role}` |
| PUT | `/api/users/{id}/role` | Admin | Change user role | `{role}` | `{message}` |
| DELETE | `/api/users/{id}` | Admin | Remove user | — | `{message}` |

*Self or admin

### Chat (`/api/chat`)
| Method | Endpoint | Auth | Purpose | Request | Response |
|--------|----------|------|---------|---------|----------|
| GET | `/api/chat/history` | JWT | Load chat | — | `[{id, role, message, created_at}]` |
| POST | `/api/chat/message` | JWT | Save message | `{role, message}` | `{message}` |
| DELETE | `/api/chat/history` | JWT | Clear chat | — | `{message}` |
| GET | `/api/chat/history/{user_id}` | Admin | Admin view user chat | — | `[{id, role, message, created_at}]` |

### AI Processing (`/ai`)
| Method | Endpoint | Auth | Purpose | Request | Response |
|--------|----------|------|---------|---------|----------|
| POST | `/ai/process` | JWT | Analyze + plan | `image?, prompt/text?` | `{status, model_id, latency_ms, image_url, pdf_url, parsed, trip}` |

### Trips (`/trips`)
| Method | Endpoint | Auth | Purpose | Request | Response |
|--------|----------|------|---------|---------|----------|
| GET | `/trips` | JWT | List my trips | — | `[{id, user_id, detected_city, image_url, itinerary, budget_estimate}]` |
| POST | `/trips` | JWT | Create trip | `{detected_city, image_url, itinerary, budget_estimate}` | Trip object |
| GET | `/trips/{id}` | JWT* | Get trip details | — | Trip object |
| DELETE | `/trips/{id}` | JWT* | Delete trip | — | `{message}` |
| GET | `/trips/user/{id}` | Admin | Admin: list user trips | — | `[Trip]` |

### Storage (`/blob`)
| Method | Endpoint | Auth | Purpose | Request | Response |
|--------|----------|------|---------|---------|----------|
| GET | `/blob/health` | None | Check connectivity | — | `{status}` |
| POST | `/blob/upload-test` | None | Test image upload | FormData(file) | `{image_url, content_type, size_bytes}` |

### Diagnostics (`/db`)
| Method | Endpoint | Auth | Purpose | Request | Response |
|--------|----------|------|---------|---------|----------|
| GET | `/db/health` | None | Check SQL connection | — | `{status, db, result}` |
| POST | `/db/test-create-user` | None | Test user insert | `{email, password_hash?}` | `{id, email}` |
| GET | `/db/test-users` | None | List test users | — | `[{id, email}]` |

### Root
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | None | Welcome message |
| GET | `/health` | None | App health check |

---

## 6. Key Code Components

### A. Authentication (`app/auth.py`)
**Responsibility**: JWT token creation, password hashing, user validation

**Key Functions**:
- `create_access_token(data)` → Generate JWT token with 1-hour expiry
- `get_current_user()` → FastAPI dependency to extract/validate JWT from `Authorization` header
- `require_admin()` → Dependency to enforce admin-only endpoints

**Security Measures**:
- Tokens expire in 1 hour (configurable via `JWT_EXPIRE_HOURS`)
- Passwords hashed with bcrypt before storage
- JWT secret stored in `.env`, never hardcoded

### B. Database (`app/database.py`)
**Responsibility**: SQLAlchemy engine setup, connection management

**Key Features**:
- Connects to Azure SQL via connection string from `.env`
- ODBC driver for SQL Server compatibility
- Connection retry logic (transient error handling)
- SQLAlchemy Base for ORM models

### C. AI Services (`app/services.py`)
**Responsibility**: Bedrock inference, PDF generation, blob uploads

**Key Functions**:
- `call_nova_lite(prompt, image?)` → Calls AWS Bedrock Nova Lite model
  - Sends JSON system prompt requesting: city, itinerary array, budget_estimate, tips
  - Returns parsed JSON output
- `upload_image_to_blob(file)` → Upload user image to Azure Blob
  - Generates UUID-based filename
  - Returns signed URL for browser access
- `upload_trip_report_pdf_to_blob(...)` → Generate PDF from AI output
  - Builds minimal PDF with text content
  - Uploads with SAS token for 2-hour browser access
  - Returns signed URL (not unsigned, to fix ResourceNotFound errors)
- `_get_or_create_demo_user(db)` → Ensures demo account exists for testing

**Why PDF SAS Signing?**
- Blob containers are private by default
- Browser requests without credentials get 404/ResourceNotFound
- SAS token (Shared Access Signature) grants time-limited read permission
- Signed URL: `https://account.blob.core.windows.net/container/blob.pdf?sv=2021&sig=...`

### D. Routers

#### Auth Router (`app/routers/auth.py`)
- Endpoint: `/api/*`
- Registration: Validate email uniqueness, hash password, create User
- Login: Query user by email, verify bcrypt hash, generate JWT
- Profile: Get/update/delete current user
- Admin: List users, change roles, delete users

#### Chat Router (`app/routers/chat.py`)
- Endpoint: `/api/chat/*`
- History: Query ChatMessage records for current user (last 100 messages)
- Save Message: Insert user or assistant message into chat_messages table
- Clear History: Delete all messages for current user
- Admin History: Retrieve chat for any user (admin only)

#### Trips Router (`app/routers/trips.py`)
- Endpoint: `/trips/*`
- List: Get all trips for authenticated user
- Get: Retrieve single trip (self or admin only)
- Create: Manually insert trip record
- Delete: Remove trip (owner or admin)
- Admin List: Get trips for any user

#### AI Router (`app/routers/ai.py`)
- Endpoint: `/ai/process`
- Flow:
  1. Accept FormData(image?, prompt/text?)
  2. Upload image → get URL
  3. Call Nova Lite AI → get JSON
  4. Generate + upload PDF → get SAS URL
  5. Save trip to database
  6. Return all data (trip record + URLs + latencies)

#### Blob Router (`app/routers/blob.py`)
- Endpoint: `/blob/*`
- Health: Test connection to blob storage
- Upload Test: Accept file, upload to blob, return URL

#### DB Test Router (`app/api/db_test.py`)
- Endpoint: `/db/*`
- Health: Execute `SELECT 1` to verify SQL connectivity
- Create User: Insert test user (no password required)
- List Test Users: Query all test users

---

## 7. Frontend Architecture

### HTML Structure (`index.html`)
- **Header**: Logo, navigation, user profile / login button
- **Main Pages** (tab-like navigation):
  - Home: Hero, features, call-to-action
  - AI Trip Planner: Chat interface + image upload
  - About: Company info (placeholder)
- **Auth Modal**: Login/register form overlay

### JavaScript (`script.js` - Main App)
**Key Functions**:
- `activatePage(id)` → Show/hide page sections
- `getAuthHeaders()` → Add JWT to fetch headers
- `handleSend()` → Submit user message → call AI → display response
- `callAiBackend(text, image)` → POST to /ai/process with FormData
- `persistMessage(role, message)` → Save chat to database
- `loadChatHistory()` → Fetch past messages on login

**User Interactions**:
1. User types/pastes image + sends
2. Message added to chat UI (optimistic)
3. Persist to database (non-critical)
4. Call AI backend (shows typing indicator)
5. Parse response JSON
6. Format as readable text with itinerary & tips
7. Add assistant message to chat
8. Display PDF download link if available

### JavaScript (`gateway_auth.js` - Authentication)
**Key Functions**:
- `checkSession()` → Parse JWT from localStorage on page load
- `handleRegisterUser()` → POST /api/register
- `initLoginApp()` → Event listener for login form
- `initLogoutApp()` → Event listener for logout button
- `getToken()`, `saveToken()`, `clearToken()` → JWT management
- `isTokenExpired(token)` → Check exp claim

**JWT Flow**:
```
Register → Store in DB → Login → Return JWT → Save to localStorage
                                              → Include in all requests
Logout → Clear localStorage → Hide profile button
```

### nginx Configuration (`nginx.conf`)
```nginx
# Proxy /api, /ai, /trips, /blob to backend
location /api {
    proxy_pass http://gateway-backend:8000;
    proxy_set_header Authorization $http_authorization;
}

location /ai {
    client_max_body_size 20M;  # Allow large image uploads
    proxy_pass http://gateway-backend:8000;
}

# Cache static assets for 30 days
location ~* \.(jpg|css|js|woff2|svg)$ {
    expires 30d;
}

# SPA fallback: all unknown routes → index.html
location / {
    try_files $uri $uri/ /index.html;
}
```

---

## 8. Setup & Deployment Guide

### Local Development (Docker Compose)

**Prerequisites**:
- Docker Desktop installed
- `.env` file with Azure/AWS credentials

**Steps**:
```bash
cd d:\projects\cloud_2\main\GateWay

# Build and run
docker-compose up --build

# Access:
# Frontend: http://localhost:8080
# Backend API: http://localhost:8000
# API docs: http://localhost:8000/docs
```

**Environment Variables** (in `.env`):
```
AZURE_SQL_CONNECTION_STRING=Server=tcp:...
AZURE_BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_BLOB_CONTAINER_NAME=travel-images
JWT_EXPIRE_HOURS=1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-3
AWS_BEDROCK_MODEL_ID=eu.amazon.nova-2-lite-v1:0
```

### Azure Container Apps Deployment

**Build & Push Image**:
```powershell
# Build
docker build -f backend_fastapi/Dockerfile -t gatewayregistry.azurecr.io/gateway-backend:v4 ./backend_fastapi

# Login to ACR
az acr login --name gatewayregistry

# Push
docker push gatewayregistry.azurecr.io/gateway-backend:v4

# Deploy
az containerapp update `
  --name gateway-backend `
  --resource-group gatewayrg `
  --image gatewayregistry.azurecr.io/gateway-backend:v4
```

**Frontend Deployment** (nginx container):
```powershell
docker build -f frontend/Dockerfile -t gatewayregistry.azurecr.io/gateway-frontend:v4 ./frontend
docker push gatewayregistry.azurecr.io/gateway-frontend:v4

az containerapp update `
  --name gateway-frontend `
  --resource-group gatewayrg `
  --image gatewayregistry.azurecr.io/gateway-frontend:v4
```

---

## 9. Input/Output Specifications

### Typical User Journey

**Input 1: Registration**
```json
POST /api/register
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```
**Output 1**:
```json
{
  "message": "Registration successful! You can now log in."
}
```

**Input 2: Login**
```json
POST /api/login
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```
**Output 2**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": 1,
  "username": "john_doe",
  "role": "user"
}
```

**Input 3: AI Trip Planning**
```
POST /ai/process
Content-Type: multipart/form-data

image: [JPEG file, 2MB]
prompt: "5-day trip to Barcelona with $2000 budget, beach activities"
```
**Output 3**:
```json
{
  "status": "success",
  "model_id": "eu.amazon.nova-2-lite-v1:0",
  "region": "eu-west-3",
  "latency_ms": 2341.56,
  "image_url": "https://gatewayimagescloudapp.blob.core.windows.net/travel-images/uploads/abc123.jpg",
  "pdf_url": "https://gatewayimagescloudapp.blob.core.windows.net/travel-images/reports/def456.pdf?sv=2021&sig=...",
  "parsed": {
    "city": "Barcelona",
    "itinerary": [
      "Day 1: Arrive, visit Sagrada Familia",
      "Day 2: Park Güell, Gothic Quarter",
      "Day 3: Beach day at Barceloneta",
      "Day 4: Montjuïc museums",
      "Day 5: Shopping at Paseo de Gracia, depart"
    ],
    "budget_estimate": "1950",
    "tips": [
      "Visit in September-October for better weather",
      "Use T-Casual travel card for cheap metro",
      "Book Sagrada Familia tickets online"
    ]
  },
  "trip": {
    "id": 42,
    "user_id": 1,
    "detected_city": "Barcelona",
    "image_url": "https://...",
    "itinerary": ["Day 1: ...", ...],
    "budget_estimate": "1950"
  }
}
```

**Input 4: Chat Message**
```json
POST /api/chat/message
{
  "role": "user",
  "message": "Tell me more about Park Güell opening hours"
}
```
**Output 4**:
```json
{
  "message": "Saved"
}
```

**Input 5: Retrieve Chat History**
```
GET /api/chat/history
Header: Authorization: Bearer [JWT_TOKEN]
```
**Output 5**:
```json
[
  {
    "id": 1,
    "role": "user",
    "message": "5-day trip to Barcelona with $2000 budget, beach activities",
    "created_at": "2026-04-26T10:55:30Z"
  },
  {
    "id": 2,
    "role": "assistant",
    "message": "Day 1: Arrive, visit Sagrada Familia...",
    "created_at": "2026-04-26T10:55:32Z"
  }
]
```

---

## 10. Team Member Contributions

### Backend Development
- **User Authentication**: JWT token generation, bcrypt hashing, user registration/login endpoints
- **Database Design**: User, Trip, ChatMessage tables with proper relationships
- **API Routers**: 6 routers covering auth, chat, trips, AI, blob, and diagnostics
- **Azure Integration**: Connection strings, retry logic, error handling
- **AWS Bedrock Integration**: Model inference, JSON parsing, system prompts
- **PDF Generation**: Minimal PDF creation from itinerary data
- **SAS Token Signing**: Secure blob download URLs for private containers

### Frontend Development
- **User Interface**: HTML responsive layout, CSS styling
- **Authentication UI**: Login/register modal, JWT token management
- **Chat Interface**: Message display, image preview, send functionality
- **API Integration**: Fetch calls to all backend endpoints
- **Session Management**: Token validation, auto-logout on expiry
- **Error Handling**: User-friendly error messages, fallbacks

### DevOps/Cloud Infrastructure
- **Docker Setup**: Backend & frontend containerization
- **Docker Compose**: Local multi-container orchestration
- **Azure SQL**: Database provisioning, connection configuration
- **Azure Blob Storage**: Container setup, SAS policy configuration
- **Azure Container Apps**: Container deployment, scaling, monitoring
- **Azure Container Registry**: Private image hosting, authentication
- **nginx Configuration**: Reverse proxy setup, static file caching

### Testing & Documentation
- **Health Checks**: `/db/health`, `/blob/health` endpoints
- **Test Endpoints**: `/db/test-*` for database validation
- **API Documentation**: Auto-generated via FastAPI /docs endpoint
- **Error Logs**: Detailed error messages in container logs

---

## 11. Security Considerations

### Authentication & Authorization
✅ JWT tokens with 1-hour expiry  
✅ Bcrypt password hashing (never plain text)  
✅ Role-based access control (user vs admin)  
✅ Authorization: Bearer token in `Authorization: Bearer <token>` header  

### Data Protection
✅ Azure SQL encryption in transit (TLS)  
✅ Azure Blob SAS tokens (time-limited, read-only for downloads)  
✅ Environment variables in `.env` (never hardcoded secrets)  
✅ Password hashes stored, not passwords  

### Infrastructure
✅ CORS policy (configurable, currently `*` for dev)  
✅ HTTPS enforced in production (nginx redirect)  
✅ Private container registry (not public pulls)  

### Recommendations for Production
⚠️ Rotate Azure SQL password regularly  
⚠️ Rotate AWS Bedrock API keys  
⚠️ Implement CORS whitelist (not `*`)  
⚠️ Enable Azure SQL firewall rules  
⚠️ Use Azure Key Vault for secret management  
⚠️ Monitor container logs for anomalies  
⚠️ Implement rate limiting on public endpoints  

---

## 12. Troubleshooting

### Issue: PDF download returns "ResourceNotFound"
**Cause**: Blob container is private; unsigned URL fails  
**Solution**: Ensure `upload_trip_report_pdf_to_blob()` returns SAS-signed URL with `?sv=...&sig=...`

### Issue: AI inference fails with "ModelNotReadyException"
**Cause**: Bedrock inference profile not configured  
**Solution**: Set `AWS_BEDROCK_INFERENCE_PROFILE_ID` in `.env`

### Issue: Database connection fails
**Cause**: Connection string syntax or firewall rules  
**Solution**: Verify `AZURE_SQL_CONNECTION_STRING`, check SQL Server firewall allows client IP

### Issue: Frontend can't reach backend
**Cause**: nginx proxy configuration or backend not running  
**Solution**: Check `nginx.conf` proxy_pass, verify backend container is healthy

### Issue: Image upload fails
**Cause**: Blob storage connection string invalid  
**Solution**: Verify `AZURE_BLOB_CONNECTION_STRING` and `AZURE_BLOB_CONTAINER_NAME`

---

## 13. Files Structure

```
main/GateWay/
├── .env                           ← Configuration (secrets)
├── docker-compose.yml             ← Local container orchestration
├── README.md                       ← Project overview
│
├── backend_fastapi/
│   ├── Dockerfile                 ← Container image build
│   ├── requirements.txt            ← Python dependencies
│   ├── app/
│   │   ├── main.py                ← FastAPI app setup, routers
│   │   ├── config.py              ← Settings from environment
│   │   ├── database.py            ← SQLAlchemy engine
│   │   ├── models.py              ← User, Trip, ChatMessage ORM
│   │   ├── schemas.py             ← Pydantic request/response models
│   │   ├── auth.py                ← JWT & password utilities
│   │   ├── services.py            ← Bedrock, blob, PDF logic
│   │   ├── routers/
│   │   │   ├── auth.py            ← /api endpoints
│   │   │   ├── chat.py            ← /api/chat endpoints
│   │   │   ├── trips.py           ← /trips endpoints
│   │   │   ├── ai.py              ← /ai/process endpoint
│   │   │   └── blob.py            ← /blob endpoints
│   │   └── api/
│   │       └── db_test.py         ← /db endpoints
│
├── frontend/
│   ├── Dockerfile                 ← nginx container
│   ├── nginx.conf                 ← Reverse proxy config
│   ├── index.html                 ← Main HTML
│   ├── script.js                  ← Chat & app logic
│   ├── gateway_auth.js            ← Auth logic
│   └── styles/
│       └── style.css              ← Styling
│
└── db-init/                       ← SQL initialization scripts (optional)
```

---

## 14. Performance & Scalability

### Bottlenecks & Solutions

| Bottleneck | Impact | Solution |
|-----------|--------|----------|
| Single FastAPI instance | Throughput ceiling | Azure Container Apps autoscaling (CPU/memory based) |
| Bedrock API latency | User wait time (2-3s) | Acceptable; no real-time requirement |
| Image file size | Bandwidth/storage | Limit to 20MB client_max_body_size in nginx |
| Database connection pool | Concurrent user ceiling | SQLAlchemy pooling (default good for <50 concurrent) |
| Blob storage | Scale-up | Azure automatically handles; no limit concern |

### Scalability Features Already Implemented
✅ Stateless JWT auth (no session store needed)  
✅ Blob storage (scales to exabytes)  
✅ Azure SQL (managed service, auto-scaling read replicas available)  
✅ Container Apps (auto-scales based on metrics)  

---

## 15. Future Enhancements

1. **Advanced AI Features**
   - Multi-turn conversations with context retention
   - Collaborative trip planning (multiple users)
   - Cost optimization suggestions

2. **User Experience**
   - Real-time trip map visualization
   - Integration with booking APIs (flights, hotels)
   - Mobile app (React Native or Flutter)

3. **Analytics & Monitoring**
   - User engagement dashboard
   - Popular destinations reporting
   - AI model performance metrics

4. **Payment & Monetization**
   - Premium features (extended chat, faster processing)
   - Stripe/PayPal integration
   - API rate limiting by tier

---

## Conclusion

**GateWay** is a well-architected, cloud-native travel AI application that demonstrates:
- ✅ Modern API design (FastAPI + JWT)
- ✅ Multi-cloud integration (Azure + AWS)
- ✅ Scalable architecture (containerized, stateless)
- ✅ Security best practices (bcrypt, SAS tokens, JWT)
- ✅ User-friendly interface (JavaScript SPA)

The modular design allows each team member to work independently on frontend, backend, or DevOps without conflicts, and the comprehensive error handling and logging enable easy debugging and maintenance.

---

**Document Version**: 1.0  
**Last Updated**: April 26, 2026  
**Audience**: Academic documentation, team reference, future developers
