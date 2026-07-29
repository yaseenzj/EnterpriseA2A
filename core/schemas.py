from pydantic import BaseModel

class OrchestrationRequest(BaseModel):
    request_text: str
    thread_id: str | None = None

class ApprovalPayload(BaseModel):
    thread_id: str
    approved_by: str
    action: str = "APPROVE"
