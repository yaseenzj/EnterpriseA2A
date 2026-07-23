# Architecture Document

## 1. System Architecture
The application follows a distributed microservices pattern orchestrated by a central LangGraph state machine.

### Flow
1. **Ingress (Core Gateway)**: User submits a request via the FastAPI gateway (`/api/v1/orchestrate`). The token is decoded and RBAC context is injected.
2. **Planner Node**: An LLM (via LangGraph) decomposes the request into atomic tasks, identifies dependencies, and builds a DAG.
3. **Discovery Node**: Connects to the PostgreSQL `agent_registry` to dynamically find the endpoints of agents capable of fulfilling the tasks.
4. **Dispatcher Node**: Executes the tasks across the microservice network via HTTP JSON-RPC calls. Handles compliance limits and pauses the graph if manager approval is required.
5. **Agent Execution**: Standalone agents (Finance, Facilities, Knowledge) execute the task and return standardized responses.

## 2. Technical Stack
- **Language**: Python 3.10+
- **API Framework**: FastAPI & Uvicorn
- **Orchestration Engine**: LangGraph & LangChain (ChatGroq)
- **Database**: PostgreSQL (for Agent Registry, Vector Search, and LangGraph Checkpointing)
- **Communication Protocol**: JSON-RPC 2.0 over HTTP

## 3. Directory Structure
```text
a2a-engine/
├── agents/             # Decentralized Microservices
│   ├── facilities/     # IT & Booking agent
│   ├── finance/        # Expense & Procurement agent
│   └── knowledge/      # RAG & Policy agent
├── core/               # Central Orchestrator
│   ├── main.py         # Ingress Gateway
│   ├── orchestrator.py # LangGraph DAG
│   ├── schemas.py      # Request/Response models
│   └── security.py     # JWT & RBAC logic
├── db/                 # Database initialization and schemas
├── docs/               # Project documentation
└── scripts/            # Utility scripts (e.g., registry population)
```
