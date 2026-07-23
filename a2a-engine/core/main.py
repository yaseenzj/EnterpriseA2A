import jwt
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from .security import check_rbac_scopes, JWT_SECRET, JWT_ALGORITHM
from .schemas import OrchestrationRequest, ApprovalPayload
from .orchestrator import workflow, EnterpriseOrchestrationState, AuthContext

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
def orchestrate_request(
    payload: OrchestrationRequest,
    auth: AuthContext = Depends(check_rbac_scopes(["execute:room_booking", "execute:expense_procurement"]))
):
    thread_id = f"thread_{auth.user_id}"
    initial_state = EnterpriseOrchestrationState(raw_user_request=payload.request_text, auth_context=auth)
    
    # Run the graph workflow with the postgres checkpointer config
    config = {"configurable": {"thread_id": thread_id}}
    output_state = workflow.invoke(initial_state, config=config)
    
    # Handle dict vs BaseModel returned from langgraph invoke
    state_dict = output_state if isinstance(output_state, dict) else output_state.dict()
    
    if state_dict.get("current_error"):
        if "COMPLIANCE_LIMIT_EXCEEDED" in state_dict["current_error"]:
            return {
                "thread_id": thread_id,
                "status": "PENDING_APPROVAL",
                "message": state_dict["current_error"],
                "requires_action": "Manager approval required. POST to /api/v1/webhook/approve to authorize."
            }
        else:
            return {
                "thread_id": thread_id,
                "status": "FAILED",
                "error": state_dict["current_error"]
            }
        
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
    
    return {
        "thread_id": payload.thread_id,
        "status": "COMPLETED",
        "response": state_dict.get("final_response")
    }
