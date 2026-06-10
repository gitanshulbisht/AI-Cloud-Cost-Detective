# 🔍 AI Cloud Cost Detective

> **An AI-powered full-stack web application that scans Azure Resource Groups, detects cost optimization opportunities, and delivers actionable fix commands — all powered by a Large Language Model.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat&logo=postgresql)](https://www.postgresql.org)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA%20NIM-Llama%203.3%2070B-76B900?style=flat&logo=nvidia)](https://build.nvidia.com)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Request Flow Diagrams](#request-flow-diagrams)
  - [Authentication Flow](#1-authentication-flow)
  - [Analysis Flow (HTTP + WebSocket)](#2-analysis-flow-http--websocket)
  - [History & Report Flow](#3-history--report-flow)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Local Development Setup](#local-development-setup)
- [Mock vs Live Azure Mode](#mock-vs-live-azure-mode)
- [Known Issues & Fixes](#known-issues--fixes)

---

## Overview

AI Cloud Cost Detective automates the tedious process of cloud cost auditing. A user selects an Azure Resource Group, triggers an analysis, and the system:

1. Scans all resources in that group via the **Azure CLI** (or mock data for local development).
2. Sends the resource inventory to **NVIDIA NIM** (Meta Llama 3.3 70B Instruct) for AI-powered cost analysis.
3. Streams real-time progress updates back to the browser via **WebSockets**.
4. Persists the structured JSON report to **PostgreSQL** and presents it in a rich UI.

---

## Features

| Feature | Description |
|---|---|
| 🔐 **JWT Authentication** | Stateless Bearer token auth with bcrypt password hashing |
| ☁️ **Azure Resource Scanning** | Calls `az resource list` and `az group list` via subprocess, with mock fallback |
| 🤖 **AI Cost Analysis** | LLM identifies over-provisioned, unused, and misconfigured resources |
| 📡 **Real-time WebSocket Progress** | Step-by-step streaming of analysis stages to the browser |
| 📊 **Analysis History** | All past runs stored in PostgreSQL, browsable and clickable |
| 🛠️ **Actionable Fix Commands** | Each issue ships with a ready-to-run Azure CLI remediation command |
| 🐳 **Dockerised Database** | PostgreSQL 15 runs as a Docker container (`aicloudcost-pg`) |

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | **FastAPI** (async, Python 3.12+) |
| ASGI Server | **Uvicorn** |
| Database Driver | **asyncpg** (async PostgreSQL driver) |
| ORM / Schema | Raw SQL with auto-migration via `asyncpg` on startup |
| Authentication | **PyJWT** + **bcrypt** |
| AI Client | **OpenAI SDK** pointed at NVIDIA NIM endpoint |
| AI Model | `meta/llama-3.3-70b-instruct` via `integrate.api.nvidia.com` |
| Azure Integration | **Azure CLI** (`az`) via Python `subprocess` |
| Real-time | **WebSockets** (FastAPI native) |
| Config | **python-dotenv** |

### Frontend
| Layer | Technology |
|---|---|
| Framework | **React 19** with **TypeScript 6** |
| Build Tool | **Vite 8** |
| Routing | **React Router DOM v7** |
| HTTP Client | **Axios** |
| Styling | **Tailwind CSS v4** (via `@tailwindcss/vite` plugin) |
| Icons | **Lucide React** |
| Date Formatting | **date-fns** |

### Infrastructure
| Component | Technology |
|---|---|
| Database | **PostgreSQL 15** (Docker: `aicloudcost-pg`) |
| Container Runtime | **Docker** |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT BROWSER                                  │
│                                                                          │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────────┐  │
│  │  Login / │  │ Dashboard │  │  History  │  │       Report         │  │
│  │  Signup  │  │  (Trigger │  │ (Past     │  │ (Issues + Fix Cmds)  │  │
│  │  Pages   │  │  Analysis)│  │  Analyses)│  │                      │  │
│  └────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────────────────────┘  │
│       │  React Router│              │                                    │
│       │  + Axios     │ WebSocket    │  Axios                             │
└───────┼──────────────┼─────────────┼────────────────────────────────────┘
        │              │             │
        │ HTTP/REST     │ ws://       │ HTTP/REST
        ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND  (port 8000)                          │
│                                                                          │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐ │
│  │  Auth Router    │   │  Analysis Router  │   │   History Router     │ │
│  │                 │   │                  │   │                      │ │
│  │ POST /signup    │   │ POST /analyze    │   │ GET /history         │ │
│  │ POST /login     │   │ GET  /resource-  │   │                      │ │
│  │                 │   │      groups      │   │                      │ │
│  │  [bcrypt +      │   │ WS  /ws/progress │   │                      │ │
│  │   PyJWT]        │   │     /{id}        │   │                      │ │
│  └────────┬────────┘   └────────┬─────────┘   └──────────┬───────────┘ │
│           │                     │                         │             │
│           │            ┌────────┴──────────┐              │             │
│           │            │  asyncio.Task      │              │             │
│           │            │  (background job) │              │             │
│           │            │                   │              │             │
│           │            │  1. azure_scanner │              │             │
│           │            │  2. ai_analyzer   │              │             │
│           │            │  3. db persist    │              │             │
│           │            │  4. ws broadcast  │              │             │
│           │            └────────┬──────────┘              │             │
│           │                     │                         │             │
└───────────┼─────────────────────┼─────────────────────────┼─────────────┘
            │                     │                         │
            ▼                     │                         │
┌───────────────────┐             │                         │
│   PostgreSQL 15   │◄────────────┘─────────────────────────┘
│  (Docker)         │
│                   │
│  ┌─────────────┐  │
│  │    users    │  │
│  │ ─────────── │  │
│  │ id (PK)     │  │
│  │ email       │  │
│  │ password_   │  │
│  │  hash       │  │
│  │ created_at  │  │
│  └─────────────┘  │
│                   │
│  ┌─────────────┐  │
│  │  analyses   │  │
│  │ ─────────── │  │
│  │ id (PK)     │  │
│  │ user_id(FK) │  │
│  │ resource_   │  │
│  │  group      │  │
│  │ resources_  │  │
│  │  scanned    │  │
│  │ issues_found│  │
│  │ estimated_  │  │
│  │  savings    │  │
│  │ analysis_   │  │
│  │  result(JSONB)│ │
│  │ status      │  │
│  │ created_at  │  │
│  └─────────────┘  │
└───────────────────┘
            ▲
            │
┌───────────┴───────────────────────────────────────────┐
│              EXTERNAL SERVICES                         │
│                                                        │
│  ┌──────────────────────┐  ┌────────────────────────┐ │
│  │   Azure CLI (az)     │  │  NVIDIA NIM API         │ │
│  │                      │  │  integrate.api.nvidia   │ │
│  │  az group list       │  │  .com/v1                │ │
│  │  az resource list    │  │                         │ │
│  │  --resource-group X  │  │  Model:                 │ │
│  │                      │  │  meta/llama-3.3-        │ │
│  │  [Mock mode          │  │  70b-instruct           │ │
│  │   available]         │  │                         │ │
│  └──────────────────────┘  └────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

---

## Request Flow Diagrams

### 1. Authentication Flow

```
┌──────────┐          ┌──────────────┐         ┌─────────────┐
│ Browser  │          │  FastAPI     │         │  PostgreSQL  │
│          │          │  Backend     │         │             │
└────┬─────┘          └──────┬───────┘         └──────┬──────┘
     │                       │                        │
     │  POST /api/auth/signup │                        │
     │  { email, password }  │                        │
     │──────────────────────►│                        │
     │                       │                        │
     │                       │ SELECT id FROM users   │
     │                       │ WHERE email = $1       │
     │                       │───────────────────────►│
     │                       │                        │
     │                       │◄── [] (no existing)────│
     │                       │                        │
     │                       │ bcrypt.hashpw(password)│
     │                       │ ──────────────────────  │
     │                       │                        │
     │                       │ INSERT INTO users      │
     │                       │ RETURNING id           │
     │                       │───────────────────────►│
     │                       │                        │
     │                       │◄── { id: 1 } ──────────│
     │                       │                        │
     │                       │ jwt.encode({ sub: "1", │
     │                       │   exp: +24h })         │
     │                       │ ──────────────────────  │
     │                       │                        │
     │◄── { access_token,    │                        │
     │      token_type }─────│                        │
     │                       │                        │
     │  localStorage.setItem │                        │
     │  ('token', ...)       │                        │
     │ ─────────────────────  │                        │
     │                       │                        │
     │  [navigate to '/']    │                        │
     │                       │                        │
     │  (Subsequent requests)│                        │
     │  Authorization:       │                        │
     │  Bearer <JWT>         │                        │
     │──────────────────────►│                        │
     │                       │ jwt.decode(token)      │
     │                       │ → user_id: "1"         │
     │                       │ ──────────────────────  │
     │                       │                        │
```

---

### 2. Analysis Flow (HTTP + WebSocket)

This is the core flow — it combines a REST POST to kick off the job and a WebSocket connection for live progress streaming.

```
┌──────────┐     ┌──────────────┐    ┌─────────────┐   ┌──────────────┐  ┌──────────────┐
│ Browser  │     │  FastAPI     │    │  PostgreSQL  │   │  Azure CLI   │  │  NVIDIA NIM  │
│(Dashboard│     │  Backend     │    │             │   │  (az)        │  │  (LLM API)   │
└────┬─────┘     └──────┬───────┘    └──────┬──────┘   └──────┬───────┘  └──────┬───────┘
     │                  │                   │                  │                 │
     │ GET /api/resource-groups             │                  │                 │
     │  Authorization: Bearer <JWT>         │                  │                 │
     │─────────────────►│                  │                  │                 │
     │                  │ az group list -o json               │                 │
     │                  │ (or MOCK_RESOURCE_GROUPS)           │                 │
     │                  │─────────────────────────────────────►│                 │
     │                  │◄── [{ name: "dev-rg" }, ...]────────│                 │
     │◄── ["dev-rg", "prod-rg"]            │                  │                 │
     │                  │                  │                  │                 │
     │ [User selects RG]│                  │                  │                 │
     │                  │                  │                  │                 │
     │ POST /api/analyze│                  │                  │                 │
     │ { resource_group: "dev-rg" }        │                  │                 │
     │─────────────────►│                  │                  │                 │
     │                  │ analysis_id = uuid4()               │                 │
     │                  │ asyncio.create_task(process_analysis())               │
     │◄── { analysis_id, status: "started" }                  │                 │
     │                  │                  │                  │                 │
     │ WS CONNECT       │                  │                  │                 │
     │ ws://localhost:8000/ws/progress/{analysis_id}           │                 │
     │═════════════════►│                  │                  │                 │
     │  [WS Handshake]  │                  │                  │                 │
     │◄═════════════════│                  │                  │                 │
     │                  │                  │                  │                 │
     │     ── asyncio.Task begins ──       │                  │                 │
     │                  │                  │                  │                 │
     │                  │ sleep(1)  [allow WS to connect]     │                 │
     │                  │                  │                  │                 │
     │◄═ "Fetching resource groups..." ═══│                  │                 │
     │                  │                  │                  │                 │
     │                  │ sleep(1)         │                  │                 │
     │                  │                  │                  │                 │
     │◄═ "Scanning resources in dev-rg..."│                  │                 │
     │                  │                  │                  │                 │
     │                  │ az resource list --resource-group dev-rg -o json      │
     │                  │─────────────────────────────────────►│                │
     │                  │◄── [{ type, name, location, sku, tags }, ...] ────────│
     │                  │                  │                  │                 │
     │◄═ "Analyzing costs with AI..."      │                  │                 │
     │                  │                  │                  │                 │
     │                  │ openai.chat.completions.create(      │                 │
     │                  │   model="meta/llama-3.3-70b-instruct",               │
     │                  │   messages=[{ role:"user", content: prompt }]         │
     │                  │ )                │                  │                 │
     │                  │──────────────────────────────────────────────────────►│
     │                  │                  │                  │                 │
     │                  │◄── { summary, estimated_savings, issues_count, issues }│
     │                  │    [JSON-parsed from LLM response]                   │
     │                  │                  │                  │                 │
     │◄═ "Storing results..."              │                  │                 │
     │                  │                  │                  │                 │
     │                  │ INSERT INTO analyses (user_id, resource_group, ...)   │
     │                  │─────────────────►│                  │                 │
     │                  │◄── OK            │                  │                 │
     │                  │                  │                  │                 │
     │◄═ "Analysis complete" ══════════════│                  │                 │
     │                  │                  │                  │                 │
     │ [ws.close()]     │                  │                  │                 │
     │ [navigate('/history') after 1.5s]   │                  │                 │
     │                  │                  │                  │                 │
```

---

### 3. History & Report Flow

```
┌──────────┐          ┌──────────────┐         ┌─────────────┐
│ Browser  │          │  FastAPI     │         │  PostgreSQL  │
│(History) │          │  Backend     │         │             │
└────┬─────┘          └──────┬───────┘         └──────┬──────┘
     │                       │                        │
     │  GET /api/history      │                        │
     │  Authorization: Bearer <JWT>                    │
     │──────────────────────►│                        │
     │                       │                        │
     │                       │ SELECT id,             │
     │                       │  resource_group,       │
     │                       │  resources_scanned,    │
     │                       │  issues_found,         │
     │                       │  estimated_savings,    │
     │                       │  created_at,           │
     │                       │  analysis_result       │
     │                       │ FROM analyses          │
     │                       │ WHERE user_id = $1     │
     │                       │ ORDER BY created_at DESC│
     │                       │───────────────────────►│
     │                       │◄── [rows]──────────────│
     │                       │                        │
     │◄── [{ id, resource_group, resources_scanned,   │
     │       issues_found, estimated_savings,          │
     │       created_at, analysis_result }]────────────│
     │                       │                        │
     │  [User clicks a row]  │                        │
     │ ─────────────────────  │                        │
     │                       │                        │
     │  navigate('/report',  │                        │
     │   { state: { report: item } })                 │
     │  [NO network call — data passed via            │
     │   React Router state]  │                       │
     │                       │                        │
     │  Report page renders: │                        │
     │  - summary            │                        │
     │  - estimated_savings  │                        │
     │  - issues[] with      │                        │
     │    severity badges &  │                        │
     │    fix_command CLI    │                        │
     │                       │                        │
```

---

## Project Structure

```
AI-Cloud-Cost-Detective/
│
├── backend/
│   ├── main.py              # FastAPI app, all routes, WebSocket manager, startup/shutdown hooks
│   ├── ai_analyzer.py       # NVIDIA NIM LLM client, prompt engineering, JSON response parsing
│   ├── azure_scanner.py     # Azure CLI subprocess wrapper + mock data for local dev
│   ├── db.py                # asyncpg connection pool, init_db() creates tables on startup
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # Environment variables (not committed)
│   └── .env.example         # Template for .env
│
└── frontend/
    ├── src/
    │   ├── App.tsx              # Root router, ProtectedRoute guard (reads localStorage JWT)
    │   ├── main.tsx             # React DOM render entry point
    │   ├── pages/
    │   │   ├── Login.tsx        # POST /api/auth/login, stores JWT in localStorage
    │   │   ├── Signup.tsx       # POST /api/auth/signup, stores JWT in localStorage
    │   │   ├── Dashboard.tsx    # Fetches RGs, triggers analysis, opens WebSocket
    │   │   ├── History.tsx      # GET /api/history, lists all past analyses
    │   │   └── Report.tsx       # Renders analysis_result JSONB, severity badges, fix commands
    │   └── components/
    │       ├── Navbar.tsx       # Top nav with Dashboard/History links, Logout button
    │       └── ProgressTracker.tsx  # Real-time WebSocket message list with spinner/checkmark
    ├── index.html
    ├── vite.config.ts       # Vite + React + Tailwind CSS v4 plugin setup
    ├── package.json
    └── tsconfig.app.json
```

---

## Database Schema

### `users`
| Column | Type | Constraints |
|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` |
| `email` | `VARCHAR(255)` | `UNIQUE NOT NULL` |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` (bcrypt) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |

### `analyses`
| Column | Type | Constraints |
|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` |
| `user_id` | `INTEGER` | `REFERENCES users(id)` |
| `resource_group` | `VARCHAR(255)` | `NOT NULL` |
| `resources_scanned` | `INTEGER` | |
| `issues_found` | `INTEGER` | |
| `estimated_savings` | `VARCHAR(255)` | e.g. `"$150/month"` |
| `analysis_result` | `JSONB` | Full LLM structured output |
| `status` | `VARCHAR(50)` | `DEFAULT 'pending'` → `'completed'` |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |

> Tables are auto-created by `init_db()` on every backend startup using `CREATE TABLE IF NOT EXISTS`.

---

## API Reference

### Auth

| Method | Endpoint | Auth | Body | Response |
|---|---|---|---|---|
| `POST` | `/api/auth/signup` | None | `{ email, password }` | `{ access_token, token_type }` |
| `POST` | `/api/auth/login` | None | `{ email, password }` | `{ access_token, token_type }` |

### Resources

| Method | Endpoint | Auth | Response |
|---|---|---|---|
| `GET` | `/api/resource-groups` | Bearer JWT | `["rg-name-1", "rg-name-2"]` |

### Analysis

| Method | Endpoint | Auth | Body | Response |
|---|---|---|---|---|
| `POST` | `/api/analyze` | Bearer JWT | `{ resource_group: string }` | `{ analysis_id: uuid, status: "started" }` |
| `GET` | `/api/history` | Bearer JWT | — | `[AnalysisRecord]` |

### WebSocket

| Protocol | Endpoint | Messages |
|---|---|---|
| `WS` | `/ws/progress/{analysis_id}` | Text frames: progress strings, `"Analysis complete"`, or `"Error: ..."` |

### AI Response Schema (stored in `analysis_result` JSONB)
```json
{
  "summary": "string",
  "estimated_savings": "$150/month",
  "issues_count": 3,
  "issues": [
    {
      "resource_name": "string",
      "issue_type": "over-provisioned | unused | misconfigured",
      "severity": "high | medium | low",
      "explanation": "string",
      "fix_command": "az vm deallocate --name ... --resource-group ..."
    }
  ]
}
```

---

## Environment Variables

Create `backend/.env` from `backend/.env.example`:

```env
# PostgreSQL connection string
DATABASE_URL="postgresql://jules:jules@127.0.0.1:5432/aicloudcost"

# JWT signing secret — change in production!
JWT_SECRET="supersecretjwtkeythatshouldbechanged"

# NVIDIA NIM API Key — get from https://build.nvidia.com
NVIDIA_API_KEY="nvapi-..."

# Set to "true" to use mock Azure data (no real az CLI needed)
USE_MOCK_AZURE_CLI="true"
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | asyncpg-compatible PostgreSQL DSN |
| `JWT_SECRET` | ✅ | Secret for signing/verifying JWTs |
| `NVIDIA_API_KEY` | ✅ | API key from [build.nvidia.com](https://build.nvidia.com) |
| `USE_MOCK_AZURE_CLI` | Optional | `"true"` skips real Azure CLI, uses hardcoded mock resources |

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop
- (Optional) Azure CLI authenticated with `az login`

### 1. Start PostgreSQL via Docker

```bash
docker run -d \
  --name aicloudcost-pg \
  -e POSTGRES_USER=jules \
  -e POSTGRES_PASSWORD=jules \
  -e POSTGRES_DB=aicloudcost \
  -p 5432:5432 \
  postgres:15
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your NVIDIA_API_KEY

# Start the server (tables are created automatically on startup)
uvicorn main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend

npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Mock vs Live Azure Mode

| Mode | `USE_MOCK_AZURE_CLI` | Requirements |
|---|---|---|
| **Mock** (default) | `"true"` | No Azure account needed. Returns hardcoded 3 resources: a `Standard_D8s_v3` VM, `Premium_P4` SQL DB, and an unused Public IP. |
| **Live** | `"false"` | Requires `az login` + sufficient subscription permissions. Calls real `az group list` and `az resource list`. |

The mock resources are intentionally "expensive-looking" to give the LLM meaningful material for generating cost-saving recommendations.

---

## Known Issues & Fixes

### `AI analysis failed: 404 page not found`

**Cause:** The NVIDIA NIM model name was `meta/llama3-70b-instruct` (missing hyphens) — an invalid model ID.

**Fix:** Updated to the correct model ID in `ai_analyzer.py`:
```python
# Before (broken)
model="meta/llama3-70b-instruct"

# After (fixed)
model="meta/llama-3.3-70b-instruct"
```

### WebSocket progress never appears

**Cause:** The frontend connects to the WebSocket *after* the POST response, but the `asyncio.create_task` background job starts immediately.  
**Mitigation:** A `asyncio.sleep(1)` delay is added at the start of `process_analysis()` to give the client time to establish the WebSocket connection before the first progress message is sent.

### JWT stored in `localStorage`

The JWT is stored in `localStorage` for simplicity. For production, consider `httpOnly` cookies to protect against XSS.

---

## License

MIT
