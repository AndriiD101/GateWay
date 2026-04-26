# Travel AI – Combined Backend

A single **FastAPI** service that merges the original Flask auth/chat backend
with the Travel AI FastAPI app. All endpoints are documented below.

---

## Architecture

```
combined/
├── app/
│   ├── main.py          ← FastAPI app, CORS, router registration
│   ├── config.py        ← All env-var settings (Settings dataclass)
│   ├── auth.py          ← JWT create / decode / FastAPI dependencies
│   ├── database.py      ← Azure SQL SQLAlchemy engine + get_db()
│   ├── models.py        ← SQLAlchemy ORM models (User, Trip, ChatMessage)
│   ├── schemas.py       ← Pydantic request/response models
│   ├── services.py      ← Blob upload, Bedrock AI, trip DB logic
│   ├── routers/
│   │   ├── auth.py      ← /api/register  /api/login  /api/me  /api/users
│   │   ├── chat.py      ← /api/chat/*
│   │   ├── trips.py     ← /trips/*
│   │   ├── ai.py        ← /ai/process
│   │   └── blob.py      ← /blob/*
│   └── api/
│       └── db_test.py   ← /db/* (Azure SQL health checks)
├── Dockerfile
├── requirements.txt
└── .env.example
```

### Databases
| Store | Used for |
|---|---|
| **Azure SQL** | `users` table (auth), `chat_messages` table, `trips` table |

> This backend uses Azure SQL only. SQLAlchemy creates required tables
> (`users`, `chat_messages`, `trips`) on startup.

---

## Quick Start

```bash
# 1. Copy env file and fill in secrets
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or with Docker:
```bash
docker build -t travel-ai-combined .
docker run --env-file .env -p 8000:8000 travel-ai-combined
```

Interactive docs available at **http://localhost:8000/docs**

---

## API Reference

### Auth & Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/register` | — | Register a new account |
| `POST` | `/api/login` | — | Login, receive JWT |
| `GET` | `/api/me` | JWT | Get own profile |
| `PUT` | `/api/me` | JWT | Update own username / password |
| `DELETE` | `/api/me` | JWT | Delete own account + chat history |
| `GET` | `/api/users` | JWT (admin) | List all users |
| `GET` | `/api/users/{id}` | JWT (self or admin) | Get single user |
| `PUT` | `/api/users/{id}/role` | JWT (admin) | Change a user's role |
| `DELETE` | `/api/users/{id}` | JWT (admin) | Delete user + their chat history |

**Register** – `POST /api/register`
```json
{ "username": "alice", "password": "s3cr3t" }
```

**Login** – `POST /api/login`
```json
{ "username": "alice", "password": "s3cr3t" }
```
Response:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_id": 1,
  "username": "alice",
  "role": "user"
}
```
Pass the token as `Authorization: Bearer <jwt>` on all protected routes.

---

### Chat History

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/chat/history` | JWT | Own chat history (last 100 msgs) |
| `POST` | `/api/chat/message` | JWT | Save a message |
| `DELETE` | `/api/chat/history` | JWT | Clear own chat history |
| `GET` | `/api/chat/history/{user_id}` | JWT (admin) | View any user's history |

**Save message** – `POST /api/chat/message`
```json
{ "role": "user", "message": "Hello!" }
```

---

### Trips (Azure SQL)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/trips` | JWT | List own trips |
| `GET` | `/trips/{id}` | JWT (self or admin) | Get single trip |
| `POST` | `/trips` | JWT | Create trip manually |
| `DELETE` | `/trips/{id}` | JWT (self or admin) | Delete trip |
| `GET` | `/trips/user/{user_id}` | JWT (admin) | List trips for any user |

**Create trip** – `POST /trips`
```json
{
  "detected_city": "Paris",
  "image_url": "https://...",
  "itinerary": ["Visit Eiffel Tower", "Explore Louvre"],
  "budget_estimate": "1500.00"
}
```

---

### AI – AWS Bedrock Nova Lite

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/ai/process` | JWT | Analyse image/text, save trip, generate PDF |

`multipart/form-data` fields:
- `image` *(file, optional)* — travel photo
- `prompt` or `text` *(string, optional)* — custom prompt

Response includes `parsed` (AI JSON), `trip` (saved trip), `pdf_url`, `image_url`, `latency_ms`.

---

### Blob Storage

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/blob/health` | — | Check Azure Blob connectivity |
| `POST` | `/blob/upload-test` | — | Test image upload |

---

### Health & DB

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | App health check |
| `GET` | `/db/health` | — | Azure SQL connectivity |
| `POST` | `/db/test-create-user` | — | Insert test user (Azure SQL) |
| `GET` | `/db/test-users` | — | List test users (Azure SQL) |

---

