# GateWay Project - Documentation Quick Start Guide

> For your colleague who needs to understand the project structure and create documentation

---

## 📚 Documentation Files Created

This project now has comprehensive documentation split into logical sections:

1. **[DOCUMENTATION.md](./DOCUMENTATION.md)** ← START HERE
   - Complete technical overview
   - Task analysis and problem definition
   - Technology justification
   - API endpoints reference
   - Setup and deployment
   - Troubleshooting guide

2. **[ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md)**
   - System architecture diagram
   - API request flow
   - Authentication flow
   - AI planning flow
   - Database relationships
   - Component interactions
   - Security architecture

3. **[TEAM_CONTRIBUTIONS.md](./TEAM_CONTRIBUTIONS.md)**
   - Who built what
   - Responsibility matrix
   - Documentation checklist
   - Testing procedures
   - Timeline for docs

---

## 🎯 What is GateWay?

**In One Sentence**: A web app where users upload travel photos and get AI-generated personalized trip itineraries with budgets in seconds.

**Key Features**:
- 📸 Image analysis via AWS Bedrock AI
- 💬 Chat history with AI assistant
- 🗺️ Automated trip planning (city, itinerary, budget, tips)
- 📄 PDF report generation
- 👥 Multi-user accounts with admin roles
- ☁️ Cloud-native (Azure + AWS)

---

## 🏗️ System Architecture (High Level)

```
┌─ Frontend ─────┐      ┌─ Backend API ─────┐      ┌─ Cloud Services ─┐
│                │      │                    │      │                   │
│ Vanilla JS     │──────│ FastAPI (Python)   │──────│ Azure SQL         │
│ HTML/CSS       │      │                    │      │ Azure Blob        │
│ (nginx)        │      │ • Auth endpoints   │      │ AWS Bedrock (AI)  │
│                │      │ • Chat endpoints   │      │                   │
│                │      │ • AI processing    │      │                   │
│                │      │ • Trip management  │      │                   │
└────────────────┘      └────────────────────┘      └───────────────────┘
```

---

## 🔐 Authentication & Security

### How Users Log In
1. User enters username + password in frontend
2. Backend hashes password with **bcrypt** (not stored plain)
3. Backend issues **JWT token** (valid 1 hour)
4. Frontend stores token in localStorage
5. All API calls include: `Authorization: Bearer <token>`

### Key Security Features
✅ JWT tokens (stateless, scalable)  
✅ bcrypt password hashing (industry standard)  
✅ Role-based access (user vs admin)  
✅ SAS tokens for blob downloads (time-limited)  
✅ Environment variables for secrets (never hardcoded)  

---

## 🧠 AI Trip Planning Flow

```
User: "5-day Barcelona trip, $2000"
           ↓
Frontend uploads image + prompt
           ↓
Backend → AWS Bedrock Nova Lite AI model
           ↓
AI returns JSON:
{
  "city": "Barcelona",
  "itinerary": ["Day 1: Sagrada Familia", ...],
  "budget_estimate": "1950",
  "tips": ["Book tickets online", ...]
}
           ↓
Backend generates PDF report
           ↓
Backend saves trip to database
           ↓
Frontend displays results + PDF download link
```

---

## 🗄️ Database Schema

```
USERS
├─ id (primary key)
├─ email (unique)
├─ password_hash (bcrypt)
├─ username
└─ role (user / admin)

TRIPS (belongs to user)
├─ id
├─ user_id (foreign key)
├─ detected_city
├─ image_url (Azure Blob)
├─ itinerary (JSON array)
└─ budget_estimate

CHAT_MESSAGES (belongs to user)
├─ id
├─ user_id (foreign key)
├─ role (user / assistant)
├─ message
└─ created_at
```

---

## 📡 Main API Endpoints

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/api/register` | Create account | ❌ |
| POST | `/api/login` | Get JWT token | ❌ |
| POST | `/ai/process` | Upload image + analyze | ✅ |
| POST | `/api/chat/message` | Save chat message | ✅ |
| GET | `/api/chat/history` | Load chat messages | ✅ |
| GET | `/trips` | List user's trips | ✅ |
| POST | `/trips` | Create trip manually | ✅ |
| GET | `/db/health` | Check database | ❌ |
| GET | `/blob/health` | Check blob storage | ❌ |

*✅ = Requires JWT token in Authorization header*

---

## 📁 Project Structure

```
main/GateWay/
├── backend_fastapi/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py (FastAPI setup)
│       ├── config.py (environment vars)
│       ├── database.py (SQL connection)
│       ├── models.py (ORM: User, Trip, ChatMessage)
│       ├── auth.py (JWT, bcrypt)
│       ├── services.py (Bedrock AI, PDF, Blob)
│       ├── routers/
│       │   ├── auth.py (/api/*)
│       │   ├── chat.py (/api/chat/*)
│       │   ├── trips.py (/trips/*)
│       │   ├── ai.py (/ai/process)
│       │   └── blob.py (/blob/*)
│       └── api/
│           └── db_test.py (/db/*)
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf (reverse proxy)
│   ├── index.html
│   ├── script.js (chat logic)
│   ├── gateway_auth.js (login/JWT)
│   └── styles/
│       └── style.css
│
├── docker-compose.yml (local development)
├── .env (secrets, not in git)
└── README.md
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker Desktop
- `.env` file with Azure/AWS credentials

### Run Locally
```bash
cd d:\projects\cloud_2\main\GateWay

# Start all services
docker-compose up --build

# Access
# Frontend: http://localhost:8080
# Backend API: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Deploy to Azure
```powershell
# Build image
docker build -f backend_fastapi/Dockerfile -t gatewayregistry.azurecr.io/gateway-backend:v4 ./backend_fastapi

# Push to ACR
az acr login --name gatewayregistry
docker push gatewayregistry.azurecr.io/gateway-backend:v4

# Update Container App
az containerapp update --name gateway-backend --resource-group gatewayrg --image gatewayregistry.azurecr.io/gateway-backend:v4
```

---

## 🛠️ Key Technologies & Why

| Technology | Purpose | Why? |
|-----------|---------|------|
| **FastAPI** | Backend framework | Fast, async, auto-documentation |
| **SQLAlchemy** | Database ORM | Database-agnostic, type-safe |
| **Azure SQL** | Database | Enterprise-grade, ACID, global |
| **Azure Blob** | File storage | Scalable, cheap, SAS token support |
| **AWS Bedrock** | AI model | No GPU needed, pay-per-use, cross-cloud |
| **JWT** | Authentication | Stateless, scalable, standard |
| **bcrypt** | Password hashing | Slow by design (prevents brute force) |
| **Vanilla JS** | Frontend | No dependencies, fast load, simple |
| **nginx** | Reverse proxy | Lightweight, efficient, caching |
| **Docker** | Containerization | Dev ≈ prod, reproducible |

---

## 🔍 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| PDF download returns 404 | Blob URL unsigned or expired | Ensure SAS token is appended to URL |
| AI returns 502 | Bedrock API failure | Check AWS_BEDROCK_MODEL_ID, check inference profile |
| Database won't connect | Invalid connection string | Verify AZURE_SQL_CONNECTION_STRING format |
| Frontend shows 502 | Backend container down | Run `docker-compose logs web` |
| JWT expired | Token >1 hour old | User must login again |

---

## 📊 Data Flow Examples

### User Registration
```
1. Frontend: POST /api/register {username, password}
2. Backend: Hash password with bcrypt
3. Backend: INSERT INTO users (email, password_hash, role='user')
4. Database: Return user_id
5. Backend: Return 201 Created
6. Frontend: Show "Success! Go to login"
```

### AI Trip Planning
```
1. Frontend: Upload image + prompt
2. Frontend: POST /ai/process (with JWT)
3. Backend: Authenticate JWT
4. Backend: Upload image to blob (get URL)
5. Backend: Call AWS Bedrock Nova Lite API
6. Backend: Parse AI response JSON
7. Backend: Generate PDF from itinerary
8. Backend: Upload PDF to blob (get SAS URL)
9. Backend: INSERT INTO trips (user_id, city, itinerary, budget)
10. Backend: Return {image_url, pdf_url, trip_data, latency_ms}
11. Frontend: Display formatted itinerary + PDF link
```

### Chat Message Flow
```
1. Frontend: User types message, clicks send
2. Frontend: Add message to chat UI (optimistic)
3. Frontend: POST /api/chat/message {role: "user", message}
4. Backend: INSERT INTO chat_messages
5. Backend: Return {message: "Saved"}
6. Frontend: Call /ai/process (if input was for AI)
7. Backend: Call Bedrock, return response
8. Frontend: Add assistant response to chat
9. Frontend: POST /api/chat/message {role: "assistant", message}
```

---

## 🧪 Testing Checklist

Before releasing, verify:
- [ ] Registration → login flow works
- [ ] JWT token generated and stored
- [ ] AI endpoint accepts image + prompt
- [ ] PDF downloads successfully (not 404)
- [ ] Chat history persists and loads
- [ ] Admin can view all users
- [ ] Health checks pass (`/db/health`, `/blob/health`)
- [ ] Logout clears token from localStorage
- [ ] Token expiry forces re-login

---

## 📚 For Your Documentation

### Essential Sections to Cover

1. **Task Analysis**
   - What problem does GateWay solve?
   - Who are the users?
   - What are primary use cases?

2. **Technology Justification**
   - Why FastAPI? (not Django, Flask)
   - Why Azure? (not AWS-only)
   - Why Bedrock Nova Lite? (not Claude, GPT-4)
   - Why Vanilla JS? (not React)

3. **Architecture**
   - System components (frontend, backend, cloud)
   - Data flow (user input → AI → storage → display)
   - Security model (JWT, SAS tokens)

4. **Setup & Usage**
   - Local development (Docker Compose)
   - Production deployment (Azure Container Apps)
   - Configuration (.env variables)
   - How to run tests

5. **API Reference**
   - All endpoints with examples
   - Request/response formats
   - Error codes
   - Authentication requirements

6. **Troubleshooting**
   - Common errors and fixes
   - Health checks
   - Logs location
   - Support contacts

---

## 💡 Quick Answers to Common Questions

**Q: Where is the AI model running?**  
A: AWS Bedrock (Nova Lite) via HTTPS API calls. No GPU on our servers.

**Q: How are images stored?**  
A: Azure Blob Storage. Each image gets a UUID filename. Users download PDFs via SAS-signed URLs.

**Q: What happens if a user deletes their account?**  
A: Cascade delete removes all their trips and chat messages (database foreign key).

**Q: Can users see other users' trips?**  
A: No, only their own. Admins can view all trips for moderation.

**Q: How long do JWT tokens last?**  
A: 1 hour (configurable via JWT_EXPIRE_HOURS env var).

**Q: Is the database encrypted?**  
A: Yes, Azure SQL encrypts data in transit (TLS) and at rest.

**Q: Why PDF URLs need SAS tokens?**  
A: Blob containers are private by default. SAS tokens grant temporary read-only access.

---

## 📞 Next Steps for Your Colleague

1. **Read** [DOCUMENTATION.md](./DOCUMENTATION.md) first (comprehensive reference)
2. **Study** [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md) (visual understanding)
3. **Review** [TEAM_CONTRIBUTIONS.md](./TEAM_CONTRIBUTIONS.md) (who did what)
4. **Run Locally**: `docker-compose up` and test endpoints
5. **Check** `/docs` endpoint for API auto-documentation
6. **Ask Questions** - consult the team members listed in TEAM_CONTRIBUTIONS

---

## 🔗 Useful Links

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Guide**: https://docs.sqlalchemy.org/
- **Azure SQL**: https://learn.microsoft.com/en-us/azure/azure-sql/
- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **JWT Best Practices**: https://tools.ietf.org/html/rfc7519
- **Docker Docs**: https://docs.docker.com/

---

## 📄 Document Status

- ✅ Core functionality documented
- ✅ Architecture diagrams created
- ✅ API endpoints cataloged
- ✅ Deployment steps outlined
- ✅ Team responsibilities assigned
- ⚠️ Pending: Team-specific implementation details
- ⚠️ Pending: Performance benchmarks
- ⚠️ Pending: Disaster recovery procedures

---

**Last Updated**: April 26, 2026  
**Version**: 1.0  
**For**: Academic/Team Documentation  
**Created By**: Comprehensive Project Analysis  

*Share this file with your colleague as the entry point to all GateWay documentation.*
