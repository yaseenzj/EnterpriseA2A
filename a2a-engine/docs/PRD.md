# Project Requirements Document (PRD)

## 1. Project Overview
The **A2A (Agent-to-Agent) Engine** is an enterprise service orchestration platform. It is designed to interpret complex, multi-intent natural language requests from users, break them down into actionable steps, and orchestrate those steps across a network of specialized, decentralized microservice agents. 

## 2. Target Users
- **Enterprise Employees**: Users who need to perform operational tasks (e.g., booking rooms, procuring supplies, querying enterprise knowledge) without navigating multiple disparate systems.
- **System Administrators / IT**: Managers who need to deploy scalable, plug-and-play agent modules and enforce Role-Based Access Control (RBAC).

## 3. Core Features
- **Natural Language Orchestration**: Translates natural user input into a Directed Acyclic Graph (DAG) execution plan using LLMs.
- **Dynamic Agent Discovery**: Automatically discovers available capabilities via a PostgreSQL database registry, removing hardcoded endpoints.
- **RBAC & Compliance Enforcement**: Reads user JWT scopes and intercepts tasks exceeding policy limits (e.g., spending limits) to enforce manager approval flows.
- **Microservice Agent Network**: Isolated agents (Facilities, Finance, Knowledge) that act as standalone API endpoints communicating via JSON-RPC 2.0.
- **Resumable Workflows**: Pauses workflow execution for external webhooks (manager approval) and resumes where it left off using LangGraph checkpointing.
