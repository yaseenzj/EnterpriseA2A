import jwt
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from .security import check_rbac_scopes, JWT_SECRET, JWT_ALGORITHM
from .schemas import OrchestrationRequest, ApprovalPayload
from .orchestrator import workflow, EnterpriseOrchestrationState, AuthContext
from .metrics import log_workflow_start, log_workflow_end, get_metrics_dashboard
from .notifications import send_notification, get_user_notifications

app = FastAPI(title="FastAPI Security & Ingress Gateway", version="1.0.0")

@app.get("/api/v1/auth/token")
def generate_test_token(user_id: str = "usr_9921", role: str = "Employee", department: str = "Sales_Team"):
    payload = {
        "sub": user_id,
        "role": role,
        "department": department,
        "scopes": ["execute:room_booking", "execute:expense_procurement"],
        "exp": 9999999999
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/v1/orchestrate")
async def orchestrate_request(
    request: OrchestrationRequest,
    auth: AuthContext = Depends(check_rbac_scopes(["execute:room_booking", "execute:expense_procurement"]))
):
    import logging
    logger = logging.getLogger("orchestrator")
    logger.info(f"[Stage 1: API Gateway] Intercepted request. JWT authenticated for user: {auth.user_id}")
    
    thread_id = request.thread_id if request.thread_id else f"thread_{auth.user_id}"
    initial_state = EnterpriseOrchestrationState(raw_user_request=request.request_text, auth_context=auth)
    
    # Metrics
    log_workflow_start(thread_id)
    
    # Run the graph workflow with the postgres checkpointer config
    config = {"configurable": {"thread_id": thread_id}}
    output_state = workflow.invoke(initial_state, config=config)
    
    # Handle dict vs BaseModel returned from langgraph invoke
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()
    
    if state_dict.get("current_error"):
        if "COMPLIANCE_LIMIT_EXCEEDED" in state_dict["current_error"]:
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
            return {
                "thread_id": thread_id,
                "status": "FAILED",
                "error": state_dict["current_error"]
            }
        
    send_notification(auth.user_id, f"Workflow {thread_id} completed successfully.", "SUCCESS")
    log_workflow_end(thread_id, "COMPLETED")
    return {
        "thread_id": thread_id,
        "status": "COMPLETED",
        "response": state_dict.get("final_response")
    }

@app.post("/api/v1/webhook/approve")
def approve_pending_workflow(payload: ApprovalPayload):
    config = {"configurable": {"thread_id": payload.thread_id}}
    # Fetch the state directly from LangGraph's postgres checkpointer
    state = workflow.get_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Active thread session not found in Postgres")
        
    state_data = state.values
    
    if isinstance(state_data, dict):
        if "compliance_approvals" not in state_data:
            state_data["compliance_approvals"] = {}
        state_data["compliance_approvals"]["expense_procurement"] = payload.approved_by
        state_data["current_error"] = None
    else:
        state_data.compliance_approvals["expense_procurement"] = payload.approved_by
        state_data.current_error = None
    
    # Resume execution by passing None to invoke
    workflow.update_state(config, state_data)
    output_state = workflow.invoke(None, config=config)
    
    # Handle dict vs BaseModel
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()
    
    send_notification(payload.approved_by, f"You approved workflow {payload.thread_id}.", "INFO")
    
    # Notify the original employee that their workflow is completed!
    original_user = None
    auth_ctx = state_data.get("auth_context") if isinstance(state_data, dict) else getattr(state_data, "auth_context", None)
    
    if auth_ctx:
        original_user = auth_ctx.get("user_id") if isinstance(auth_ctx, dict) else getattr(auth_ctx, "user_id", None)
        
    status = "COMPLETED"
    if state_dict.get("current_error"):
        status = "FAILED"
        if original_user:
            send_notification(original_user, f"Workflow {payload.thread_id} failed after approval: {state_dict['current_error']}", "ERROR")
    else:
        if original_user:
            send_notification(original_user, f"Workflow {payload.thread_id} was approved and completed successfully.", "SUCCESS")
        
    log_workflow_end(payload.thread_id, status)
    
    return {
        "thread_id": payload.thread_id,
        "status": status,
        "response": state_dict.get("final_response"),
        "error": state_dict.get("current_error")
    }

@app.get("/api/v1/workflows/metrics")
def get_metrics():
    return get_metrics_dashboard()

@app.get("/api/v1/notifications")
def get_notifications(user_id: str = "usr_9921"):
    return get_user_notifications(user_id)
