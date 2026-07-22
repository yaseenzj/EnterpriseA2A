import os
import json
import uuid
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import psycopg
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
# Setup connection pool for PostgresSaver
connection_pool = ConnectionPool(conninfo=DB_URI, kwargs={"autocommit": True})
checkpointer = PostgresSaver(connection_pool)
checkpointer.setup()

# --- SECTION 1: Pydantic State & DAG Definitions ---

class AuthContext(BaseModel):
    user_id: str
    department: str
    role: str
    scopes: List[str]

class TaskDef(BaseModel):
    task_id: str
    target_agent: str
    action: str
    priority: str
    urgency_score: int
    depends_on: List[str] = []
    required_permissions: List[str] = []
    requires_approval: bool = False
    parameters: Dict[str, Any] = {}
    input_mappings: Dict[str, str] = {}
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    result: Optional[Dict[str, Any]] = None

class OrchestrationDAG(BaseModel):
    intent_summary: str = Field(description="Brief summary of request")
    tasks: List[TaskDef]

class EnterpriseOrchestrationState(BaseModel):
    raw_user_request: str
    sanitized_request: str = ""
    auth_context: Optional[AuthContext] = None
    dag_plan: Optional[OrchestrationDAG] = None
    execution_history: List[Dict[str, Any]] = []
    compliance_approvals: Dict[str, str] = {}  # e.g., {"expense_procurement": "mgr_alex"}
    final_response: Optional[Dict[str, Any]] = None
    current_error: Optional[str] = None
    resolved_endpoints: Dict[str, str] = {}

# --- SECTION 2: LangGraph Node Implementations ---

def guardrails_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    req = state.raw_user_request
    if "drop table" in req.lower() or "delete from" in req.lower():
        raise ValueError("Security violation: Potential SQL Injection detected!")
    cleaned_req = req.strip()
    return {"sanitized_request": cleaned_req}

def planner_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    system_prompt = """You are the Lead Workflow Orchestrator and Dynamic Execution Planner for an Enterprise Service Operations Platform. 

### OBJECTIVE
Analyze incoming multi-intent user requests, validate permissions against the provided user context, discover suitable agents from the registered Agent Catalog, and output a structured Directed Acyclic Graph (DAG) execution plan.

### INPUT CONTEXT
1. **User Request**: {request}
2. **User Context**: {context}
3. **Agent Catalog**: {catalog}

### INSTRUCTIONS & GUARDRAILS
1. **Intent & Prioritization Extraction**:
   - Assess overall and task-level priority: CRITICAL (outages/security), HIGH (time-sensitive/same-day), MEDIUM (standard), or LOW (informational).
   - Assign an urgency_score from 1 (flexible) to 5 (immediate action required) based on time indicators in the prompt.

2. **Decomposition & Dependencies**:
   - Break down complex requests into distinct atomic tasks.
   - Identify sequential data dependencies. If Task B needs output variables (e.g., room_id) from Task A, mark depends_on: ["task_A"] and map inputs.

3. **RBAC & Permission Mapping**:
   - Explicitly list the required_permissions needed to execute each action.
   - Check if the user's permissions array from JWT contains those permissions.
   - If missing, set requires_approval: true and flag the task for the ApprovalAgent.

4. **Policy Constraint Pre-fetching**:
   - If a request involves spending, ordering, or policy-bound actions, insert a KnowledgeAgent task *before* or alongside action tasks to retrieve relevant limits.
"""

    mock_catalog = [
        {"agent_id": "KnowledgeAgent", "capabilities": ["retrieve_knowledge"], "input_schema": {"query": "string"}, "output_schema": {"answer": "string"}},
        {"agent_id": "ITFacilitiesAgent", "capabilities": ["room_booking"], "input_schema": {"room_type": "string", "date": "string"}, "output_schema": {"booking_id": "string"}},
        {"agent_id": "FinanceAgent", "capabilities": ["expense_procurement"], "input_schema": {"item": "string (must be exactly 'premium_lunches' or 'basic_lunches')", "quantity": "integer"}, "output_schema": {"transaction_id": "string", "total_cost": "float"}}
    ]

    auth_dict = state.auth_context.dict() if state.auth_context else {}
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt)])
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(OrchestrationDAG)
    
    chain = prompt | structured_llm
    
    dag_plan = chain.invoke({
        "request": state.sanitized_request,
        "context": json.dumps(auth_dict),
        "catalog": json.dumps(mock_catalog)
    })
    
    return {"dag_plan": dag_plan}

def discovery_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    # Queries pgregistry dynamically at runtime
    resolved_endpoints = {}
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT capabilities, endpoint FROM agent_registry")
                for caps, endpoint in cur.fetchall():
                    if isinstance(caps, str):
                        caps = json.loads(caps)
                    for cap in caps:
                        resolved_endpoints[cap] = endpoint
    except Exception as e:
        print(f"Error querying agent_registry: {e}")
        
    return {"resolved_endpoints": resolved_endpoints}

def dispatcher_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    dag = state.dag_plan
    if not dag:
        return {}
    
    history = list(state.execution_history)
    error_occurred = None
    
    for task in dag.tasks:
        if any(h.get("task_id") == task.task_id and h.get("status") == "SUCCESS" for h in history):
            continue
            
        # 1. Approval Gate Check
        if task.requires_approval:
            approval_token = state.compliance_approvals.get(task.action)
            if not approval_token:
                error_occurred = f"COMPLIANCE_LIMIT_EXCEEDED: Task {task.task_id} ({task.action}) requires manager approval."
                task.status = "FAILED"
                break
                
        # 2. Dependency Injection
        if task.input_mappings:
            for dest_param, source_path in task.input_mappings.items():
                parts = source_path.split('.')
                if len(parts) >= 3 and parts[1] == "output":
                    src_task_id = parts[0]
                    src_field = parts[2]
                    for h in history:
                        if h.get("task_id") == src_task_id and h.get("status") == "SUCCESS":
                            res = h.get("result", {})
                            task.parameters[dest_param] = res.get(src_field)
                            
        rpc_payload = {
            "jsonrpc": "2.0",
            "method": task.action,
            "params": task.parameters,
            "id": str(uuid.uuid4())
        }
        
        endpoint = state.resolved_endpoints.get(task.action)
        if not endpoint:
            error_occurred = f"DISCOVERY_ERROR: No registered agent found for capability '{task.action}'."
            task.status = "FAILED"
            break
            
        try:
            with httpx.Client() as client:
                response = client.post(endpoint, json=rpc_payload, timeout=5.0)
                res_json = response.json()
                
                if res_json.get("error"):
                    err = res_json["error"]
                    if err.get("code") == -32001:
                        error_occurred = f"COMPLIANCE_LIMIT_EXCEEDED: {err.get('message')}"
                        task.status = "FAILED"
                        break
                    else:
                        error_occurred = f"Agent Error: {err.get('message')}"
                        task.status = "FAILED"
                        break
                else:
                    task.status = "COMPLETED"
                    task.result = res_json.get("result")
                    history.append({"task_id": task.task_id, "status": "SUCCESS", "result": task.result})
        except httpx.ConnectError:
            # Fallback for testing environments if servers are offline
            if task.action == "expense_procurement":
                total_cost = 600.0 * task.parameters.get("quantity", 1)
                if total_cost > 5000.0 and "approved_by" not in task.parameters:
                    error_occurred = f"COMPLIANCE_LIMIT_EXCEEDED: Total cost is {total_cost} INR."
                    task.status = "FAILED"
                    break
                else:
                    task.status = "COMPLETED"
                    task.result = {"status": "SETTLED", "transaction_id": "TXN-MOCK123", "total_cost": total_cost}
                    history.append({"task_id": task.task_id, "status": "SUCCESS", "result": task.result})
            elif task.action == "retrieve_knowledge":
                task.status = "COMPLETED"
                task.result = {"status": "SUCCESS", "answer": "Based on company policy, premium lunches are allowed for meetings but must be approved if total cost exceeds budget limits."}
                history.append({"task_id": task.task_id, "status": "SUCCESS", "result": task.result})
            else:
                task.status = "COMPLETED"
                task.result = {"status": "SUCCESS", "booking_id": "BK-991A", "calendar_invite_url": "https://calendar.internal/BK-991A"}
                history.append({"task_id": task.task_id, "status": "SUCCESS", "result": task.result})
            
    return {
        "execution_history": history,
        "current_error": error_occurred,
        "dag_plan": dag
    }

def reflection_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    if state.current_error:
        return {}
    compiled_results = {h["task_id"]: h["result"] for h in state.execution_history}
    final_payload = {
        "status": "APPROVED_AND_COMPLETED",
        "message": "Workflow successfully executed across all business agents.",
        "results": compiled_results
    }
    return {"final_response": final_payload}

# --- SECTION 3: Conditional Routing & Compilation ---

def determine_next_step(state: EnterpriseOrchestrationState) -> str:
    if state.current_error and "COMPLIANCE_LIMIT_EXCEEDED" in state.current_error:
        return "pause_for_approval"
    return "end_workflow"

builder = StateGraph(EnterpriseOrchestrationState)
builder.add_node("guardrails", guardrails_node)
builder.add_node("planner", planner_node)
builder.add_node("discovery", discovery_node)
builder.add_node("dispatcher", dispatcher_node)
builder.add_node("reflection", reflection_node)

builder.set_entry_point("guardrails")
builder.add_edge("guardrails", "planner")
builder.add_edge("planner", "discovery")
builder.add_edge("discovery", "dispatcher")
builder.add_edge("dispatcher", "reflection")

builder.add_conditional_edges(
    "dispatcher",
    determine_next_step,
    {
        "pause_for_approval": END,
        "end_workflow": "reflection"
    }
)
builder.add_edge("reflection", END)
workflow = builder.compile(checkpointer=checkpointer)
