# Enterprise A2A Service Operations Platform

A multi-agent AI platform that dynamically orchestrates enterprise service requests across Finance, IT, and Knowledge domains. Built with **LangGraph**, **FastAPI**, **A2A-inspired architecture**, **RAG**, **RBAC**, and **Human-in-the-Loop** approvals.

---

## Architecture Overview

```
User Request
    │
    ▼
[Stage 1] API Gateway (FastAPI + JWT RBAC)
    │
    ▼
[Stage 2] Guardrails Node   ← SQL injection / prompt injection scan
    │
    ▼
[Stage 3] LLM Planner Node  ← Groq LLM builds a dynamic Task DAG
    │                           Reads live Agent Catalog from PostgreSQL
    ▼
[Stage 4] Discovery Node    ← Resolves agent endpoints from registry
    │
    ▼
[Stage 5] Dispatcher Node   ← Fires JSON-RPC requests to microservices
    │         ├── Finance Agent (port 8000) — expense processing
    │         ├── IT Agent     (port 8001) — room booking, software
    │         └── Knowledge Agent (port 8002) — RAG policy retrieval
    │
    │  [If compliance limit exceeded → PAUSE → Human Approval via webhook]
    │
    ▼
[Stage 6] Reflection Node   ← LLM validates results, retries if failed
    │
    ▼
Final Response (conversational LLM summary + structured results)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API / Gateway | FastAPI |
| Workflow Engine | LangGraph (StateGraph + PostgresSaver checkpointer) |
| LLM | Groq (llama-3.3-70b-versatile) |
| LLM Framework | LangChain |
| Agent Communication | A2A-inspired JSON-RPC over HTTP |
| Knowledge Retrieval | RAG with PostgreSQL full-text search (tsvector) |
| Workflow State / Memory | PostgresSaver (LangGraph checkpoint in PostgreSQL) |
| Authentication | JWT (PyJWT) |
| Authorization | RBAC (scope-based claims in JWT) |
| Password Hashing | bcrypt |
| Database | PostgreSQL |
| Validation | Pydantic v2 |

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (running locally)
- A `.env` file in the project root

---

## Environment Setup

Create a `.env` file in the project root:

```env
DB_URI=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres
JWT_SECRET=your-super-secret-key-at-least-32-chars-long
GROQ_API_KEY=your-groq-api-key
```

---

## Installation

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Initialise the database (creates all tables + seeds knowledge base)
python db/init_db.py
```

---

## Running the Platform

Open **4 separate terminals** in the project root and run:

```bash
# Terminal 1 — Core Orchestrator (main API)
uvicorn core.main:app --port 9006 --reload

# Terminal 2 — Finance Agent
uvicorn finance.main:app --port 8000

# Terminal 3 — IT Agent
uvicorn it.main:app --port 8001

# Terminal 4 — Knowledge Agent
uvicorn knowledge.main:app --port 8002
```

---

## Testing via Swagger UI

Open **http://localhost:9006/docs** in your browser.

### Step-by-step:

**1. Create an account**
- `POST /api/v1/auth/signup` — the **first** account created automatically becomes **Admin**

**2. Get a token**
- `POST /api/v1/auth/login` — copy the `access_token` from the response

**3. Authenticate in Swagger**
- Click **Authorize 🔒** (top right of the page)
- Paste the token value (just the token, no `Bearer` prefix)
- Click **Authorize** → **Close**

**4. Submit a service request**
- `POST /api/v1/orchestrate`
- Try these example requests:
  - `"Book a conference room for tomorrow 3-4pm"`
  - `"What is the expense reimbursement limit?"`
  - `"Purchase 2 VS Code licenses"` *(may trigger approval)*
  - `"Book a business class flight to Dubai"` *(triggers approval)*

**5. Test Human-in-the-Loop approval**
- Submit a high-cost request → note the `thread_id` in the `PENDING_APPROVAL` response
- Log in as a Manager or Admin account
- `POST /api/v1/webhook/approve` with the `thread_id`

---

## API Reference

All endpoints are available at **http://localhost:9006/docs** with full interactive documentation.

### Authentication (`/api/v1/auth/...`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/signup` | None | Create a new user account |
| `POST` | `/api/v1/auth/login` | None | Log in, receive JWT |
| `GET` | `/api/v1/auth/users` | Admin | List all users |
| `PATCH` | `/api/v1/auth/users/{username}/role` | Admin | Change a user's role (e.g. `alice`) |
| `PATCH` | `/api/v1/auth/users/{username}/department` | Admin | Transfer user to a department |

### Orchestration (`/api/v1/...`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/orchestrate` | Employee+ | Submit a service request |
| `POST` | `/api/v1/webhook/approve` | Manager+ | Approve a paused workflow |

### Approvals (`/api/v1/approvals/...`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/approvals/pending` | Manager+ | List pending approvals (filtered by dept for Managers) |
| `GET` | `/api/v1/approvals/my-actions` | Manager+ | Approvals actioned by this manager |
| `GET` | `/api/v1/approvals/all` | Admin | All approval records system-wide |
| `GET` | `/api/v1/workflows/my-history` | Any | Workflows submitted by this user |

### Monitoring (`/api/v1/...`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/workflows/metrics` | Admin | System metrics dashboard |
| `GET` | `/api/v1/notifications` | Any | User notifications (pass `user_id` query param) |
| `GET` | `/health` | None | Health check |

---

## Role-Based Access Control

| Role | Scopes | Capabilities |
|---|---|---|
| `Employee` | `execute:room_booking`, `execute:expense_procurement` | Submit requests, view own history |
| `Manager` | Employee scopes + `approve:workflows` | + Approve pending workflows (own dept) |
| `Admin` | All scopes + `admin:all` | + System metrics, all approvals, user management |

> **Note:** The first user to sign up automatically receives the `Admin` role. All subsequent signups default to `Employee`. Use the Admin → User Management panel to promote users.

---

## Agent Registry (Plug-and-Play)

Each business agent registers itself in the PostgreSQL `agent_registry` table on startup with:
- `agent_name`, `description`, `endpoint`, `version`
- `capabilities` (JSON array of action names)
- `input_schema` / `output_schema` (JSON)
- `health_status` (`HEALTHY` / `OFFLINE`)

The orchestrator **dynamically discovers** agents at runtime from this registry. Adding a new agent requires **zero changes** to the orchestrator — just start the new agent service.

---

## Key Design Concepts

### Dynamic DAG Planning
The LLM planner reads the live Agent Catalog and generates a Directed Acyclic Graph of tasks for each request. It determines: task order, parallel opportunities, approval requirements, and required permissions — all without hardcoded routing.

### Workflow Memory (Stateful Execution)
LangGraph's `PostgresSaver` checkpoints full workflow state to PostgreSQL after every node. This enables:
- Human-in-the-Loop pausing and resuming across HTTP requests
- Dependency injection (passing outputs of one agent as inputs to another)
- Retry loops (Reflection node routes failed workflows back to the Planner)

### Reflection Loop
After all agents respond, a dedicated Reflection node uses the LLM to validate the results. If any task failed or returned incomplete data, it routes back to the Planner for up to 2 retry attempts.

---

## Project Structure

```
Agent/
├── core/                   # Orchestrator service (port 9006)
│   ├── main.py             # FastAPI app, API endpoints
│   ├── orchestrator.py     # LangGraph workflow (6-stage DAG)
│   ├── security.py         # JWT verification + RBAC
│   ├── auth_routes.py      # Signup / Login / User management
│   ├── approval_routes.py  # Approval workflow endpoints
│   ├── metrics.py          # Workflow metrics logging
│   ├── notifications.py    # Notification system
│   └── schemas.py          # Pydantic request/response models
├── finance/                # Finance Agent (port 8000)
├── it/                     # IT Agent (port 8001)
├── knowledge/              # Knowledge/RAG Agent (port 8002)
├── db/
│   ├── init_db.py          # Database schema + seed data
│   └── schema.sql          # SQL schema reference
├── docs/
│   ├── assignment.md       # Project brief
│   └── Architecture.md     # Architecture documentation
├── frontend/               # React UI (port 5173, optional)
├── scripts/                # Test and utility scripts
├── requirements.txt
└── README.md
```
