# Enterprise Orchestration Flow

Here is the high-level architectural flow of your platform, explaining how a user's request travels through the system from start to finish. You can use this diagram to explain the core logic to your mentor.

```mermaid
graph TD
    %% Styling
    classDef stage fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#fff
    classDef db fill:#2c5282,stroke:#4299e1,stroke-width:2px,color:#fff
    classDef agent fill:#276749,stroke:#48bb78,stroke-width:2px,color:#fff
    classDef endpoint fill:#742a2a,stroke:#fc8181,stroke-width:2px,color:#fff
    
    User([👤 User Request]) --> Gateway[Stage 1: API Gateway & JWT Auth]:::stage
    
    Gateway --> RBAC{RBAC Check}
    RBAC -- Unauthorized --> Reject([403 Forbidden]):::endpoint
    RBAC -- Authorized --> Guardrails[Stage 2: Guardrails Node]:::stage
    
    Guardrails --> Malicious{Malicious?}
    Malicious -- Yes --> Block([500 Security Violation]):::endpoint
    Malicious -- No --> Planner[Stage 3: LLM Planner Node]:::stage
    
    Planner --> DAG[Generate Task DAG]
    DAG --> Discovery[Stage 4: Agent Discovery Node]:::stage
    
    Discovery <--> DB[(PostgreSQL Agent Registry)]:::db
    Discovery --> Dispatcher[Stage 5: Dispatcher Node]:::stage
    
    Dispatcher --> HistoryCheck{Data Dependencies?}
    HistoryCheck -- Needs Data --> FetchHistory[(Fetch Short-Term Memory)]:::db
    FetchHistory --> Execute
    HistoryCheck -- Independent --> Execute[Dispatch JSON-RPC]
    
    Execute --> A1[Finance Agent]:::agent
    Execute --> A2[Facilities Agent]:::agent
    Execute --> A3[Knowledge Agent]:::agent
    
    A1 --> Approval{Limit Exceeded?}
    Approval -- Yes --> SaveState[(PostgresSaver Checkpointer)]:::db
    SaveState --> Wait([Pending Webhook Approval]):::endpoint
    Approval -- No --> Results
    
    A2 --> Results
    A3 <--> RAG[(PostgreSQL tsvector Knowledge Base)]:::db
    A3 --> Results
    
    Results --> Reflection[Stage 6: Reflection Node]:::stage
    Reflection --> Final([Return 200 OK JSON]):::endpoint
```

### Stage Summary:
1. **API Gateway:** Intercepts the request and checks the JWT token for valid scopes.
2. **Guardrails:** Scans the raw text for SQL injections or forbidden prompts.
3. **Planner:** Uses the Groq LLM to decompose the request into an ordered Directed Acyclic Graph (DAG) of tasks.
4. **Discovery:** Queries PostgreSQL to find out exactly where the required agents are currently hosted.
5. **Dispatcher:** Injects short-term memory (outputs from previous tasks) into current tasks and fires HTTP requests to the distributed agents. Handles compliance halts (Pending Approval).
6. **Reflection:** Aggregates all the successful agent outputs into a unified response for the user.
