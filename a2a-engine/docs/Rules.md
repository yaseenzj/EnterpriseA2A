# Rules Document

## 1. Technical Constraints & Libraries
- **Allowed Frameworks**: FastAPI for all ingress and agent APIs. LangGraph for stateful orchestration.
- **Avoid**: Do not introduce monolithic tightly-coupled logic. Agents must remain completely isolated.
- **Database**: PostgreSQL is strictly mandated. No SQLite or local JSON databases. Utilize `psycopg` (not psycopg2).

## 2. Coding Standards
- **Modularity**: Every new agent must follow the golden template: `main.py`, `config.py`, `schemas.py`, `services.py`.
- **Validation**: All API inputs and outputs must be strictly validated using Pydantic `BaseModel`.
- **Error Handling**: Agents must return standard JSON-RPC 2.0 error formats (e.g., `code: -32601` for method not found). Do not return standard HTTP 500 errors unless critical failure occurs.

## 3. Security Guidelines
- **Zero Trust**: Agents should not inherently trust the orchestrator. Though currently bypassed, future implementations must pass the JWT token to agents for localized verification.
- **SQL Injection**: Always use parameterized queries `%s` when interacting with PostgreSQL. Never use string formatting for SQL.

## 4. AI Behavior Guidelines
- AI coding assistants should **always** check the `core/schemas.py` and `agents/{target}/schemas.py` before modifying logic.
- Ensure that modifications to the LangGraph nodes do not break the checkpointing system (e.g., all state variables must be serializable).
