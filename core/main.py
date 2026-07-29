import os
import psycopg
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import Optional

from .security import check_rbac_scopes, AuthContext, verify_and_decode_jwt
from .schemas import OrchestrationRequest, ApprovalPayload
from .orchestrator import workflow, EnterpriseOrchestrationState
from .metrics import log_workflow_start, log_workflow_end, get_metrics_dashboard
from .notifications import send_notification, get_user_notifications
from .auth_routes import router as auth_router
from .approval_routes import router as approval_router

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

# ─── FastAPI App with full OpenAPI metadata ────────────────────────────────────
app = FastAPI(
    title="Enterprise A2A Orchestrator",
    version="2.0.0",
    description="""
## Enterprise Service Operations Platform

A multi-agent AI platform that dynamically orchestrates enterprise service requests
across Finance, IT, and Knowledge domains using LangGraph, A2A communication, RAG, and RBAC.

### Quick Start (Testing via /docs)
1. **Sign up** → `POST /api/v1/auth/signup`
2. **Log in** → `POST /api/v1/auth/login` → copy the `access_token`
3. Click **Authorize 🔒** (top right) → paste the token → **Authorize**
4. Now you can test all protected endpoints

### Roles
| Role | Permissions |
|---|---|
| `Employee` | Submit requests, view own history |
| `Manager` | All Employee perms + approve workflows (own dept) |
| `Admin` | All perms + user management + system metrics |

### Workflow Stages
`API Gateway → Guardrails → LLM Planner → Agent Discovery → Dispatcher → [Approval?] → Reflection`
    """,
    contact={"name": "Enterprise A2A Platform"},
    openapi_tags=[
        {"name": "auth", "description": "User signup, login, and admin user management"},
        {"name": "orchestration", "description": "Submit and track multi-agent workflow requests"},
        {"name": "approvals", "description": "Manager & Admin approval workflow management"},
        {"name": "monitoring", "description": "Metrics, notifications, and system health"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(approval_router)

# ─── Internal helpers ──────────────────────────────────────────────────────────

def _write_pending_approval(thread_id: str, requested_by: str, request_summary: str, raw_request: str = None, department: str = None):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pending_approvals (thread_id, requested_by, request_summary, raw_request, status, requester_department) "
                    "VALUES (%s, %s, %s, %s, 'PENDING', %s) ON CONFLICT DO NOTHING",
                    (thread_id, requested_by, request_summary, raw_request, department)
                )
            conn.commit()
    except Exception as e:
        import logging; logging.getLogger("orchestrator").error(f"Failed to write pending approval: {e}")

def _resolve_approval(thread_id: str, actioned_by: str, status: str):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE pending_approvals SET status = %s, actioned_by = %s, action_time = CURRENT_TIMESTAMP WHERE thread_id = %s",
                    (status, actioned_by, thread_id)
                )
            conn.commit()
    except Exception as e:
        import logging; logging.getLogger("orchestrator").error(f"Failed to resolve approval: {e}")

# ─── Response models ───────────────────────────────────────────────────────────

class WorkflowResponse(BaseModel):
    thread_id: str
    status: str
    message: Optional[str] = None
    requires_action: Optional[str] = None
    response: Optional[dict] = None
    error: Optional[str] = None

class ApprovalResponse(BaseModel):
    thread_id: str
    status: str
    response: Optional[dict] = None
    error: Optional[str] = None

# ─── Core Orchestration Endpoints ─────────────────────────────────────────────

@app.post(
    "/api/v1/orchestrate",
    tags=["orchestration"],
    summary="Submit a Service Request",
    description="""
Submit a natural-language enterprise service request. The platform will:
- Validate your JWT and RBAC scopes
- Run guardrails (SQL injection scan etc.)
- Use an LLM to build a dynamic execution DAG
- Discover the right agents from the registry
- Dispatch tasks and return results

**Example requests to try:**
- `"Book a conference room for tomorrow 3-4pm"`
- `"I need a software license for VS Code"`
- `"What is the expense reimbursement policy?"`
- `"Book a business class flight to Dubai and purchase 2 software licenses"` *(triggers approval)*
    """,
    response_model=WorkflowResponse,
    responses={
        200: {"description": "Workflow completed, failed, or paused for approval"},
        401: {"description": "Invalid or missing JWT token"},
        403: {"description": "Insufficient RBAC scopes"},
    }
)
async def orchestrate_request(
    request: OrchestrationRequest,
    auth: AuthContext = Depends(check_rbac_scopes(["execute:room_booking", "execute:expense_procurement"]))
):
    import logging
    logger = logging.getLogger("orchestrator")
    logger.info(f"[Stage 1: API Gateway] JWT authenticated for user: {auth.username or auth.user_id}")

    username = auth.username or auth.user_id
    thread_id = request.thread_id if request.thread_id else f"thread_{username}"
    initial_state = EnterpriseOrchestrationState(raw_user_request=request.request_text, auth_context=auth)

    log_workflow_start(thread_id, user_id=username)
    config = {"configurable": {"thread_id": thread_id}}
    output_state = workflow.invoke(initial_state, config=config)
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()

    if state_dict.get("current_error"):
        if "COMPLIANCE_LIMIT_EXCEEDED" in state_dict["current_error"]:
            dag_plan = state_dict.get("dag_plan")
            intent_summary = "Pending Workflow Approval"
            if dag_plan:
                if isinstance(dag_plan, dict):
                    intent_summary = dag_plan.get("intent_summary", intent_summary)
                else:
                    intent_summary = getattr(dag_plan, "intent_summary", intent_summary)
            
            _write_pending_approval(thread_id, username, request_summary=intent_summary, raw_request=request.request_text, department=auth.department)
            send_notification(auth.user_id, f"Workflow {thread_id} paused for manager approval.", "ALERT")
            log_workflow_end(thread_id, "PENDING_APPROVAL")
            return WorkflowResponse(
                thread_id=thread_id,
                status="PENDING_APPROVAL",
                message=state_dict["current_error"],
                requires_action="Manager approval required. POST to /api/v1/webhook/approve with the thread_id."
            )
        else:
            send_notification(auth.user_id, f"Workflow {thread_id} failed: {state_dict['current_error']}", "ERROR")
            log_workflow_end(thread_id, "FAILED")
            return WorkflowResponse(thread_id=thread_id, status="FAILED", error=state_dict["current_error"])

    send_notification(auth.user_id, f"Workflow {thread_id} completed successfully.", "SUCCESS")
    log_workflow_end(thread_id, "COMPLETED")
    return WorkflowResponse(
        thread_id=thread_id,
        status="COMPLETED",
        response=state_dict.get("final_response")
    )


@app.post(
    "/api/v1/webhook/approve",
    tags=["approvals"],
    summary="Approve a Paused Workflow",
    description="""
Resume a workflow that was paused for manager approval due to a compliance limit.

**Requires:** Manager or Admin JWT token.

**Steps:**
1. Submit a request that exceeds limits (e.g. high-value expense) → get `PENDING_APPROVAL` response with `thread_id`
2. Log in as a Manager/Admin and call this endpoint with that `thread_id`
3. The paused LangGraph workflow resumes from the approval node and completes
    """,
    response_model=ApprovalResponse,
    responses={
        200: {"description": "Workflow resumed and completed"},
        403: {"description": "Manager or Admin role required"},
        404: {"description": "Thread ID not found or already completed"},
    }
)
def approve_pending_workflow(
    payload: ApprovalPayload,
    auth: AuthContext = Depends(verify_and_decode_jwt)
):
    if auth.role not in ("Manager", "Admin"):
        raise HTTPException(status_code=403, detail="Manager or Admin role required to approve workflows")

    config = {"configurable": {"thread_id": payload.thread_id}}
    state = workflow.get_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Active thread session not found. It may have already completed or expired.")

    state_data = state.values
    approver_name = auth.username or payload.approved_by

    if isinstance(state_data, dict):
        state_data.setdefault("compliance_approvals", {})["expense_procurement"] = approver_name
        state_data["current_error"] = None
    else:
        state_data.compliance_approvals["expense_procurement"] = approver_name
        state_data.current_error = None

    workflow.update_state(config, state_data)
    output_state = workflow.invoke(None, config=config)
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()

    approval_status = "APPROVED" if not state_dict.get("current_error") else "FAILED"
    _resolve_approval(payload.thread_id, approver_name, approval_status)
    send_notification(auth.user_id, f"You approved workflow {payload.thread_id}.", "INFO")

    # Notify the original employee
    auth_ctx = state_data.get("auth_context") if isinstance(state_data, dict) else getattr(state_data, "auth_context", None)
    if auth_ctx:
        original_user = auth_ctx.get("user_id") if isinstance(auth_ctx, dict) else getattr(auth_ctx, "user_id", None)
        if original_user:
            msg = "completed successfully" if approval_status == "APPROVED" else "failed after approval"
            send_notification(original_user, f"Your workflow {payload.thread_id} was approved and {msg}.", "SUCCESS" if approval_status == "APPROVED" else "ERROR")

    final_status = "COMPLETED" if approval_status == "APPROVED" else "FAILED"
    log_workflow_end(payload.thread_id, final_status)

    return ApprovalResponse(
        thread_id=payload.thread_id,
        status=final_status,
        response=state_dict.get("final_response"),
        error=state_dict.get("current_error")
    )


@app.get(
    "/api/v1/workflows/metrics",
    tags=["monitoring"],
    summary="Get System Metrics Dashboard",
    description="Returns aggregated workflow execution statistics. **Admin only.**",
    responses={
        200: {"description": "Metrics dashboard data"},
        403: {"description": "Admin role required"},
    }
)
def get_metrics(auth: AuthContext = Depends(verify_and_decode_jwt)):
    if auth.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required to access system metrics")
    return get_metrics_dashboard()


@app.get(
    "/api/v1/notifications",
    tags=["monitoring"],
    summary="Get User Notifications",
    description="Fetch the latest notifications for a specific user ID (their UUID from the JWT `sub` field).",
)
def get_notifications(user_id: str, auth: AuthContext = Depends(verify_and_decode_jwt)):
    return {"notifications": get_user_notifications(user_id)}


@app.get("/health", tags=["monitoring"], summary="Health Check", description="Returns 200 if the orchestrator is running.")
def health_check():
    return {"status": "healthy", "service": "Enterprise A2A Orchestrator", "version": "2.0.0"}
