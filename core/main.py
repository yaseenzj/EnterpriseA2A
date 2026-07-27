import os
import psycopg
import jwt
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .security import check_rbac_scopes, JWT_SECRET, JWT_ALGORITHM, AuthContext, verify_and_decode_jwt
from .schemas import OrchestrationRequest, ApprovalPayload
from .orchestrator import workflow, EnterpriseOrchestrationState
from .metrics import log_workflow_start, log_workflow_end, get_metrics_dashboard
from .notifications import send_notification, get_user_notifications
from .auth_routes import router as auth_router
from .approval_routes import router as approval_router

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

app = FastAPI(title="Enterprise A2A Orchestrator Gateway", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(approval_router)

def write_pending_approval(thread_id: str, requested_by: str, request_summary: str):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pending_approvals (thread_id, requested_by, request_summary, status) VALUES (%s, %s, %s, 'PENDING') ON CONFLICT DO NOTHING",
                    (thread_id, requested_by, request_summary)
                )
            conn.commit()
    except Exception as e:
        import logging
        logging.getLogger("orchestrator").error(f"Failed to write pending approval: {e}")

def resolve_approval(thread_id: str, actioned_by: str, status: str):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE pending_approvals SET status = %s, actioned_by = %s, action_time = CURRENT_TIMESTAMP WHERE thread_id = %s",
                    (status, actioned_by, thread_id)
                )
            conn.commit()
    except Exception as e:
        import logging
        logging.getLogger("orchestrator").error(f"Failed to resolve approval: {e}")

@app.post("/api/v1/orchestrate")
async def orchestrate_request(
    request: OrchestrationRequest,
    auth: AuthContext = Depends(check_rbac_scopes(["execute:room_booking", "execute:expense_procurement"]))
):
    import logging
    logger = logging.getLogger("orchestrator")
    logger.info(f"[Stage 1: API Gateway] Intercepted request. JWT authenticated for user: {auth.user_id}")

    username = getattr(auth, "username", auth.user_id)
    thread_id = request.thread_id if request.thread_id else f"thread_{auth.user_id}"
    initial_state = EnterpriseOrchestrationState(raw_user_request=request.request_text, auth_context=auth)

    log_workflow_start(thread_id, user_id=username)

    config = {"configurable": {"thread_id": thread_id}}
    output_state = workflow.invoke(initial_state, config=config)
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()

    if state_dict.get("current_error"):
        if "COMPLIANCE_LIMIT_EXCEEDED" in state_dict["current_error"]:
            write_pending_approval(thread_id, username, request.request_text)
            send_notification(auth.user_id, f"Workflow {thread_id} paused for manager approval.", "ALERT")
            log_workflow_end(thread_id, "PENDING_APPROVAL")
            return {
                "thread_id": thread_id,
                "status": "PENDING_APPROVAL",
                "message": state_dict["current_error"],
                "requires_action": "Manager approval required. POST to /api/v1/webhook/approve to authorize."
            }
        else:
            send_notification(auth.user_id, f"Workflow {thread_id} failed: {state_dict['current_error']}", "ERROR")
            log_workflow_end(thread_id, "FAILED")
            return {"thread_id": thread_id, "status": "FAILED", "error": state_dict["current_error"]}

    send_notification(auth.user_id, f"Workflow {thread_id} completed successfully.", "SUCCESS")
    log_workflow_end(thread_id, "COMPLETED")
    return {
        "thread_id": thread_id,
        "status": "COMPLETED",
        "response": state_dict.get("final_response")
    }

@app.post("/api/v1/webhook/approve")
def approve_pending_workflow(payload: ApprovalPayload, auth: AuthContext = Depends(verify_and_decode_jwt)):
    config = {"configurable": {"thread_id": payload.thread_id}}
    state = workflow.get_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Active thread session not found in Postgres")

    state_data = state.values
    approver_name = getattr(auth, "username", payload.approved_by)

    if isinstance(state_data, dict):
        if "compliance_approvals" not in state_data:
            state_data["compliance_approvals"] = {}
        state_data["compliance_approvals"]["expense_procurement"] = approver_name
        state_data["current_error"] = None
    else:
        state_data.compliance_approvals["expense_procurement"] = approver_name
        state_data.current_error = None

    workflow.update_state(config, state_data)
    output_state = workflow.invoke(None, config=config)
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()

    status = "APPROVED" if not state_dict.get("current_error") else "FAILED"
    resolve_approval(payload.thread_id, approver_name, status)

    send_notification(approver_name, f"You approved workflow {payload.thread_id}.", "INFO")

    original_user = None
    auth_ctx = state_data.get("auth_context") if isinstance(state_data, dict) else getattr(state_data, "auth_context", None)
    if auth_ctx:
        original_user = auth_ctx.get("user_id") if isinstance(auth_ctx, dict) else getattr(auth_ctx, "user_id", None)

    final_status = "COMPLETED"
    if state_dict.get("current_error"):
        final_status = "FAILED"
        if original_user:
            send_notification(original_user, f"Workflow {payload.thread_id} failed after approval.", "ERROR")
    else:
        if original_user:
            send_notification(original_user, f"Workflow {payload.thread_id} was approved and completed successfully.", "SUCCESS")

    log_workflow_end(payload.thread_id, final_status)
    return {
        "thread_id": payload.thread_id,
        "status": final_status,
        "response": state_dict.get("final_response"),
        "error": state_dict.get("current_error")
    }

@app.get("/api/v1/workflows/metrics")
def get_metrics(auth: AuthContext = Depends(verify_and_decode_jwt)):
    if auth.role not in ("Admin",):
        raise HTTPException(status_code=403, detail="Admin access required")
    return get_metrics_dashboard()

@app.get("/api/v1/notifications")
def get_notifications(user_id: str, auth: AuthContext = Depends(verify_and_decode_jwt)):
    return get_user_notifications(user_id)
