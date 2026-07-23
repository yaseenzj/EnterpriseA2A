# Project Phases

## Phase 1: Foundation & Refactoring (COMPLETED)
- Restructure monolith into isolated microservices (`agents/`, `core/`).
- Standardize agent templates (`main.py`, `config.py`, `schemas.py`, `services.py`).
- Centralize security and API ingress into the `core/` module.

## Phase 2: Orchestration & DB Integration (CURRENT)
- Ensure PostgreSQL agent registry is robust.
- Ensure LangGraph state pausing and resumption for manager approvals works seamlessly via webhooks.
- Test error logging and dynamic agent discovery.

## Phase 3: Agent Expansion
- Add external tool use to the Knowledge Agent (e.g., connecting it to a real vector DB or Confluence).
- Implement real API connections for the Facilities agent (e.g., Microsoft Graph API for calendar invites).
- Implement real payment gateway webhooks for the Finance agent.

## Phase 4: UI/UX Implementation
- Build a user-friendly frontend interface (Next.js or React) to replace the current API-only interaction.
- Implement real-time WebSocket streaming so users can see the DAG execution logs live in the UI.

## Phase 5: Deployment & DevOps
- Containerize all agents using Docker.
- Create a `docker-compose.yml` to spin up PostgreSQL, the orchestrator, and all agents simultaneously.
- Deploy to a cloud provider using Kubernetes for automatic agent scaling.
