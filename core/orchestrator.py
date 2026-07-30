import os
import json
import uuid
import httpx
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import psycopg
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

import warnings
from rich.logging import RichHandler

# Hide LangGraph deserialization warnings for custom types
warnings.filterwarnings("ignore", message=".*Deserializing unregistered type.*")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("orchestrator")

DB_URI = os.getenv("DB_URI", "postgresql://postgres:yaseen@localhost:5432/postgres")
# Setup connection pool for PostgresSaver
connection_pool = ConnectionPool(conninfo=DB_URI, kwargs={"autocommit": True})
checkpointer = PostgresSaver(connection_pool)
checkpointer.setup()

# --- SECTION 1: Pydantic State & DAG Definitions ---

# AuthContext is defined in security.py to avoid circular imports
from .security import AuthContext

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
    chat_history: list = []
    auth_context: Optional[AuthContext] = None
    dag_plan: Optional[OrchestrationDAG] = None
    retry_count: int = 0
    execution_history: List[Dict[str, Any]] = []
    compliance_approvals: Dict[str, str] = {}  # e.g., {"expense_procurement": "mgr_alex"}
    final_response: Optional[Dict[str, Any]] = None
    current_error: Optional[str] = None
    resolved_endpoints: Dict[str, str] = {}

# --- SECTION 2: LangGraph Node Implementations ---

def guardrails_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    logger.info("[Stage 2: Guardrails] Scanning raw request for security violations...")
    req = state.raw_user_request
    if "drop table" in req.lower() or "delete from" in req.lower():
        logger.error("[Stage 2: Guardrails] Security violation: Potential SQL Injection detected!")
        raise ValueError("Security violation: Potential SQL Injection detected!")
    cleaned_req = req.strip()
    logger.info(f"[Stage 2: Guardrails] Guardrails passed. Sanitized request: {cleaned_req}")
    return {"sanitized_request": cleaned_req}

def planner_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    logger.info("[Stage 3: Planner] LLM is decomposing the request into a task DAG...")
    system_prompt = """You are the Lead Workflow Orchestrator and Dynamic Execution Planner for an Enterprise Service Operations Platform. 

### OBJECTIVE
Analyze incoming multi-intent user requests, validate permissions against the provided user context, discover suitable agents from the registered Agent Catalog, and output a structured Directed Acyclic Graph (DAG) execution plan.

### INPUT CONTEXT
1. **User Request**: {request}
2. **Chat History** (Previous messages for context): {chat_history}
3. **User Context**: {context}
4. **Agent Catalog**: {catalog}

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

5. **Parameters & Schema**:
   - You MUST populate the `parameters` dictionary for each task using exactly the keys defined in the agent's `input_schema`.

6. **Conversational & Ambiguous Prompts (ANTI-HALLUCINATION)**:
   - If the user's request is a greeting ("hi"), a simple confirmation ("yes", "ok"), or a conversational query, you MUST route it strictly to the `Chat_Agent` (`general_chat` capability).
   - DO NOT hallucinate, assume, or invent tasks (like booking a room or buying supplies) unless the user explicitly requested them.
"""

    dynamic_catalog = []
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT agent_name, capabilities, input_schema, output_schema, health_status FROM agent_registry")
                for name, caps, in_schema, out_schema, health in cur.fetchall():
                    if isinstance(caps, str):
                        caps = json.loads(caps)
                    if isinstance(in_schema, str):
                        in_schema = json.loads(in_schema)
                    if isinstance(out_schema, str):
                        out_schema = json.loads(out_schema)
                    
                    dynamic_catalog.append({
                        "agent_id": f"{name} (Status: {health})",
                        "capabilities": caps,
                        "input_schema": in_schema,
                        "output_schema": out_schema
                    })
    except Exception as e:
        logger.error(f"[Stage 3: Planner] Error querying agent_registry for catalog: {e}")

    auth_dict = state.auth_context.dict() if state.auth_context else {}
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt)])
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(OrchestrationDAG)
    
    chain = prompt | structured_llm
    
    dag_plan = chain.invoke({
        "request": state.sanitized_request,
        "chat_history": json.dumps(state.chat_history),
        "context": json.dumps(auth_dict),
        "catalog": json.dumps(dynamic_catalog)
    })
    
    logger.info(f"[Stage 3: Planner] DAG created with {len(dag_plan.tasks)} tasks.")
    return {"dag_plan": dag_plan}

def discovery_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    logger.info("[Stage 4: Discovery] Querying PostgreSQL registry for agent endpoints...")
    # Queries pgregistry dynamically at runtime
    resolved_endpoints = {}
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                # Get healthy endpoints
                cur.execute("SELECT capabilities, endpoint FROM agent_registry WHERE health_status = 'HEALTHY'")
                for caps, endpoint in cur.fetchall():
                    if isinstance(caps, str):
                        caps = json.loads(caps)
                    for cap in caps:
                        resolved_endpoints[cap] = endpoint
                        
                # Also collect offline capabilities to provide better errors
                cur.execute("SELECT agent_name, capabilities FROM agent_registry WHERE health_status = 'OFFLINE'")
                for name, caps in cur.fetchall():
                    if isinstance(caps, str):
                        caps = json.loads(caps)
                    for cap in caps:
                        if cap not in resolved_endpoints:
                            resolved_endpoints[cap] = f"OFFLINE:{name}"
    except Exception as e:
        logger.error(f"[Stage 4: Discovery] Error querying agent_registry: {e}")
        
    logger.info(f"[Stage 4: Discovery] Found endpoints for {list(resolved_endpoints.keys())}")
    return {"resolved_endpoints": resolved_endpoints}

def dispatcher_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    logger.info("[Stage 5: Dispatcher] Dispatching JSON-RPC tasks to microservices...")
    dag = state.dag_plan
    if not dag:
        logger.warning("[Stage 5: Dispatcher] No DAG plan found.")
        return {}
    
    history = list(state.execution_history)
    error_occurred = None
    
    for task in dag.tasks:
        logger.info(f"[Stage 5: Dispatcher] Processing task: {task.task_id} ({task.action}) | Priority: {task.priority} (Urgency: {task.urgency_score}) | Depends on: {task.depends_on}")
        if any(h.get("task_id") == task.task_id and h.get("status") == "SUCCESS" for h in history):
            logger.info(f"[Stage 5: Dispatcher] Task {task.task_id} already completed, skipping.")
            continue
            
        # 1. Approval Gate Check
        if task.requires_approval:
            approval_token = state.compliance_approvals.get(task.action)
            if not approval_token:
                error_occurred = f"COMPLIANCE_LIMIT_EXCEEDED: Task {task.task_id} ({task.action}) requires manager approval."
                logger.warning(f"[Stage 5: Dispatcher] Task {task.task_id} requires approval. Pausing workflow.")
                task.status = "FAILED"
                break
            logger.info(f"[Stage 5: Dispatcher] Approval found for task {task.task_id}.")
                
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
            logger.error(f"[Stage 5: Dispatcher] {error_occurred}")
            task.status = "FAILED"
            break
            
        if endpoint.startswith("OFFLINE:"):
            agent_name = endpoint.split(":")[1]
            error_occurred = f"DISCOVERY_ERROR: Agent '{agent_name}' which provides capability '{task.action}' is currently OFFLINE."
            logger.error(f"[Stage 5: Dispatcher] {error_occurred}")
            task.status = "FAILED"
            break
            
        try:
            with httpx.Client() as client:
                response = client.post(endpoint, json=rpc_payload, timeout=30.0)
                res_json = response.json()
                
                if res_json.get("error"):
                    err = res_json["error"]
                    if err.get("code") == -32001:
                        error_occurred = f"COMPLIANCE_LIMIT_EXCEEDED: {err.get('message')}"
                        logger.warning(f"[Stage 5: Dispatcher] Compliance limit exceeded for task {task.task_id}.")
                        task.status = "FAILED"
                        break
                    else:
                        error_occurred = f"Agent Error: {err.get('message')}"
                        logger.error(f"[Stage 5: Dispatcher] Agent error for task {task.task_id}: {err.get('message')}")
                        task.status = "FAILED"
                        break
                else:
                    logger.info(f"[Stage 5: Dispatcher] Task {task.task_id} completed successfully.")
                    task.status = "COMPLETED"
                    task.result = res_json.get("result")
                    history.append({"task_id": task.task_id, "status": "SUCCESS", "result": task.result})
        except httpx.ConnectError:
            error_occurred = f"AGENT_OFFLINE: Could not connect to the agent for '{task.action}'."
            logger.error(f"[Stage 5: Dispatcher] {error_occurred}")
            task.status = "FAILED"
            break
        except httpx.ReadTimeout:
            error_occurred = f"AGENT_TIMEOUT: The agent for '{task.action}' timed out (took > 30s). This usually happens when an LLM hits a rate limit and retries."
            logger.error(f"[Stage 5: Dispatcher] {error_occurred}")
            task.status = "FAILED"
            break
        except Exception as e:
            error_occurred = f"DISPATCH_ERROR: Unknown error dispatching task '{task.task_id}': {e}"
            logger.error(f"[Stage 5: Dispatcher] {error_occurred}")
            task.status = "FAILED"
            break
            
    if error_occurred:
        logger.error(f"[Stage 5: Dispatcher] Dispatcher encountered an error: {error_occurred}")
    else:
        logger.info("[Stage 5: Dispatcher] Completed all available tasks.")

    return {
        "execution_history": history,
        "current_error": error_occurred,
        "dag_plan": dag
    }

def reflection_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    logger.info("[Stage 6: Reflection] Validating workflow outputs using LLM...")
    if state.current_error and state.current_error != "RETRY":
        logger.warning("[Stage 6: Reflection] Hard error found in state, skipping reflection.")
        return {}
        
    compiled_results = {}
    dag_tasks = {t.task_id: t for t in state.dag_plan.tasks} if state.dag_plan else {}
    
    for h in state.execution_history:
        tid = h["task_id"]
        action = dag_tasks.get(tid).action if tid in dag_tasks else "Unknown Action"
        compiled_results[tid] = {
            "action": action,
            "result": h["result"]
        }
        
    if state.retry_count >= 2:
        logger.warning("[Stage 6: Reflection] Max retries reached.")
        final_payload = {
            "status": "COMPLETED_WITH_ERRORS",
            "message": "Max retries reached. Some tasks failed.",
            "results": compiled_results
        }
        return {"final_response": final_payload, "current_error": None}
        
    # Use LLM to reflect
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        prompt = f"""You are a Workflow Reflection Agent. Review these execution results:
{json.dumps(compiled_results, indent=2)}

Original Request: {state.sanitized_request}

Did any task fail, return a network error, or missing information? 
If YES, reply strictly with the word 'RETRY' and a short reason. 
If NO and everything was perfectly successful, reply strictly with 'SUCCESS'."""

        reflection = llm.invoke([("user", prompt)]).content.strip()
        if reflection.startswith("RETRY"):
            logger.warning(f"[Stage 6: Reflection] LLM determined failure: {reflection}")
            return {
                "current_error": "RETRY",
                "retry_count": state.retry_count + 1,
                "dag_plan": None,
                "execution_history": [],
                "sanitized_request": f"{state.sanitized_request} (Note: Previous attempt failed. {reflection})"
            }
    except Exception as e:
        logger.error(f"[Stage 6: Reflection] LLM reflection failed: {e}")

    # Bypass LLM summary for single tasks that already provide a human-readable response
    if len(compiled_results) == 1:
        only_task = list(compiled_results.values())[0]
        res = only_task.get("result", {})
        if isinstance(res, dict):
            # Check for common human-readable fields provided by agents
            reply_text = res.get("answer") or res.get("message")
            if reply_text:
                logger.info(f"[Stage 6: Reflection] Bypassing LLM summary for single task {only_task.get('action')}.")
                return {
                    "final_response": {
                        "status": "APPROVED_AND_COMPLETED",
                        "message": "Task executed successfully.",
                        "results": compiled_results,
                        "conversational_reply": reply_text
                    }
                }

    conversational_reply = "Workflow completed successfully."
    # Check if we have any answers we can fallback to if LLM fails
    fallback_texts = []
    for task_out in compiled_results.values():
        if isinstance(task_out.get("result"), dict):
            text = task_out["result"].get("answer") or task_out["result"].get("message")
            if text:
                fallback_texts.append(text)
    if fallback_texts:
        conversational_reply = "\n\n".join(fallback_texts)

    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        reply_prompt = f"Summarize these workflow results in a friendly, conversational manner for the user. Do not use markdown code blocks or JSON. Be concise. IMPORTANT: If the results contain any URLs, links, or meeting links, you MUST explicitly include the raw URL in your response (e.g. 'here is the link: https://...'). Original request: {state.sanitized_request}\nResults: {json.dumps(compiled_results)}"
        response_text = llm.invoke([("user", reply_prompt)]).content.strip()
        if response_text:
            conversational_reply = response_text
    except Exception as e:
        logger.error(f"[Stage 6: Reflection] Conversational LLM failed: {e}")

    final_payload = {
        "status": "APPROVED_AND_COMPLETED",
        "message": "Workflow successfully executed across all business agents.",
        "results": compiled_results,
        "conversational_reply": conversational_reply
    }
    logger.info("[Stage 6: Reflection] Workflow fully successful.")
    return {"final_response": final_payload, "current_error": None}

# --- SECTION 3: Conditional Routing & Compilation ---

def determine_next_step(state: EnterpriseOrchestrationState) -> str:
    if state.current_error and "COMPLIANCE_LIMIT_EXCEEDED" in state.current_error:
        return "pause_for_approval"
    return "end_workflow"

def approval_node(state: EnterpriseOrchestrationState) -> Dict[str, Any]:
    logger.info("[Stage 5.5: Approval] Resuming workflow after manager approval.")
    return {}

builder = StateGraph(EnterpriseOrchestrationState)
builder.add_node("guardrails", guardrails_node)
builder.add_node("planner", planner_node)
builder.add_node("discovery", discovery_node)
builder.add_node("dispatcher", dispatcher_node)
builder.add_node("approval", approval_node)
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
        "pause_for_approval": "approval",
        "end_workflow": "reflection"
    }
)
builder.add_edge("approval", "dispatcher")
def reflection_router(state: EnterpriseOrchestrationState) -> str:
    if state.current_error == "RETRY":
        return "retry"
    return "end"

builder.add_conditional_edges(
    "reflection",
    reflection_router,
    {
        "retry": "planner",
        "end": END
    }
)
workflow = builder.compile(checkpointer=checkpointer, interrupt_before=["approval"])
