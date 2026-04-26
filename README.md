# GateWay ✈️

**GateWay** is an AI-powered travel planning web application. Users can upload a travel photo or describe a destination in text, and the app generates a personalized trip itinerary and budget estimate using AWS Bedrock. Results are saved to Azure SQL, and a PDF trip report is generated and stored in Azure Blob Storage.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Running with Docker](#running-with-docker)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Frontend](#frontend)

---

## Features

- **AI Trip Planner** – Upload a travel image or enter a text prompt to receive a full itinerary, budget estimate, and travel tips powered by AWS Bedrock (Amazon Nova Lite).
- **PDF Report Generation** – Automatically generates and stores a downloadable PDF trip report in Azure Blob Storage.
- **JWT Authentication** – Secure registration and login with role-based access (`user` / `admin`).
- **Chat History** – Persistent per-user chat history stored in Azure SQL.
- **Trip Management** – Save, view, and delete AI-generated or manually created trips.
- **Admin Panel** – Admin users can list all users, view any user's trips/chat history, change roles, and delete accounts.
- **Single-Page Application** – Vanilla JS frontend served via Nginx.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, Gunicorn |
| Database | Azure SQL (via SQLAlchemy + pyodbc / MSSQL) |
| AI | AWS Bedrock – Amazon Nova Lite (`eu.amazon.nova-2-lite-v1:0`) |
| File Storage | Azure Blob Storage |
| Auth | JWT (HS256) via `python-jose`, passwords hashed with `bcrypt` |
| Frontend | HTML5, CSS3, Vanilla JS, served by Nginx |
| Containerisation | Docker, Docker Compose |

---

## Project Structure

```
GateWay/
├── backend_fastapi/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point, middleware, startup
│   │   ├── config.py         # Settings loaded from environment variables
│   │   ├── database.py       # SQLAlchemy engine and session
│   │   ├── models.py         # ORM models: User, Trip, ChatMessage
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── auth.py           # JWT creation and dependency helpers
│   │   ├── services.py       # Bedrock inference, Blob upload, PDF generation
│   │   └── routers/
│   │       ├── auth.py       # /api/register, /api/login, /api/me, /api/users
│   │       ├── trips.py      # /trips CRUD
│   │       ├── ai.py         # /ai/process – image/text → AI → trip + PDF
│   │       ├── chat.py       # /api/chat/history, /api/chat/message
│   │       └── blob.py       # /blob/health, /blob/upload-test
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html            # Main SPA shell
│   ├── script.js             # Page routing, chat UI, image upload
│   ├── gateway_auth.js       # Auth modal, token management, profile UI
│   ├── nginx.conf            # Nginx config (proxy /api and /ai to backend)
│   └── styles/
│       └── pictures/         # Static images used in the UI
├── db-init/
│   └── gateway_init_clean.sql  # Optional SQL init script
├── docker-compose.yml
├── Dockerfile                # Root Dockerfile (builds backend image)
└── .gitignore
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- An **Azure SQL** database (connection string)
- An **Azure Blob Storage** account (connection string + container name)
- An **AWS** account with **Bedrock** access enabled in `eu-west-3` (or your chosen region)

---

## Environment Variables

Create a `.env` file in the project root (it is git-ignored). All variables below are required unless a default is shown.

```env
# ── Azure SQL ──────────────────────────────────────────────────────────────
AZURE_SQL_CONNECTION_STRING=mssql+pyodbc://user:password@host/db?driver=ODBC+Driver+18+for+SQL+Server

# ── Azure Blob Storage ─────────────────────────────────────────────────────
AZURE_BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_BLOB_CONTAINER_NAME=travel-images   # default: travel-images

# ── AWS Bedrock ────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-3                      # default: eu-west-3
AWS_BEDROCK_MODEL_ID=eu.amazon.nova-2-lite-v1:0

# ── JWT ────────────────────────────────────────────────────────────────────
SECRET_KEY=your-secret-key-here
JWT_EXPIRE_HOURS=1                        # default: 1
```

---

## Running with Docker

```bash
# 1. Clone the repository
git clone <repo-url>
cd GateWay

# 2. Create your .env file (see above)
cp .env.example .env   # or create it manually

# 3. Build and start all services
docker compose up --build

# Backend available at:  http://localhost:8000
# Frontend available at: http://localhost:8080
# Interactive API docs:  http://localhost:8000/docs
```

To stop:
```bash
docker compose down
```

---

## API Reference

All protected endpoints require the header:
```
Authorization: Bearer <jwt_token>
```

### Auth — `/api`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/register` | Public | Register a new user |
| `POST` | `/api/login` | Public | Login and receive a JWT |
| `GET` | `/api/me` | User | Get current user profile |
| `PUT` | `/api/me` | User | Update username or password |
| `DELETE` | `/api/me` | User | Delete own account |
| `GET` | `/api/users` | Admin | List all users |
| `GET` | `/api/users/{id}` | User/Admin | Get a user by ID |
| `PUT` | `/api/users/{id}/role` | Admin | Change a user's role |
| `DELETE` | `/api/users/{id}` | Admin | Delete a user |

### AI — `/ai`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/ai/process` | User | Submit image and/or text prompt; returns itinerary, budget, PDF URL, and saved trip |

Request: `multipart/form-data` with optional `image` (file) and `prompt`/`text` (string) fields.

### Trips — `/trips`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/trips` | User | List own trips |
| `GET` | `/trips/{id}` | User/Admin | Get a trip by ID |
| `POST` | `/trips` | User | Manually create a trip |
| `DELETE` | `/trips/{id}` | User/Admin | Delete a trip |
| `GET` | `/trips/user/{user_id}` | Admin | List trips for a specific user |

### Chat — `/api/chat`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/chat/history` | User | Get own chat history (last 100 messages) |
| `POST` | `/api/chat/message` | User | Save a chat message (`user` or `assistant` role) |
| `DELETE` | `/api/chat/history` | User | Clear own chat history |
| `GET` | `/api/chat/history/{user_id}` | Admin | Get a user's full chat history |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `GET` | `/blob/health` | Azure Blob connectivity check |
| `GET` | `/db/health` | Azure SQL connectivity check |

---

## Database Schema

The schema is auto-created on startup by SQLAlchemy. The `db-init/gateway_init_clean.sql` file provides a reference SQL script.

**users**
| Column | Type | Notes |
|---|---|---|
| `id` | int (PK) | Auto-increment |
| `email` | varchar(255) | Used as the login username, unique |
| `username` | varchar(255) | Display name |
| `password_hash` | varchar(255) | bcrypt hash |
| `role` | varchar(32) | `user` or `admin` |

**trips**
| Column | Type | Notes |
|---|---|---|
| `id` | int (PK) | Auto-increment |
| `user_id` | int (FK → users) | |
| `detected_city` | varchar(255) | City identified by AI |
| `image_url` | varchar(1024) | Azure Blob URL of the uploaded image |
| `itinerary` | text | JSON-serialised itinerary array |
| `budget_estimate` | numeric(12,2) | Estimated trip cost |

**chat_messages**
| Column | Type | Notes |
|---|---|---|
| `id` | int (PK) | Auto-increment |
| `user_id` | int (FK → users) | |
| `role` | varchar(32) | `user` or `assistant` |
| `message` | text | Message content |
| `created_at` | datetime | Server-generated timestamp |

---

## Authentication

- Passwords are hashed with **bcrypt** before storage.
- On login, a signed **HS256 JWT** is issued containing `user_id`, `username`, and `role`.
- Token expiry defaults to **1 hour** and is configurable via `JWT_EXPIRE_HOURS`.
- The frontend stores the token in `localStorage` under the key `gateway_jwt` and attaches it as a `Bearer` token on every API request.
- Admin-only endpoints use a `require_admin` dependency that rejects non-admin JWTs with `403 Forbidden`.

---

## Frontend

The frontend is a single-page application served by **Nginx** on port `8080`. Nginx also acts as a reverse proxy, forwarding `/api` and `/ai` requests to the FastAPI backend at port `8000`.

Key pages:
- **Home** – Landing page with hero section and feature highlights.
- **AI Trip Planner** – Chat-style interface for uploading photos or entering text prompts. Requires authentication.
- **About Us** – Project information.

Authentication flow:
- Unauthenticated users are shown a modal when they try to access the AI planner.
- After login, the UI updates to show the username, profile dropdown, and logout option.
- Admin users see additional management options in the profile menu.
