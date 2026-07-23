from pydantic import BaseModel

class OrchestrationRequest(BaseModel):
    request_text: str

class ApprovalPayload(BaseModel):
    thread_id: str
    approved_by: str
