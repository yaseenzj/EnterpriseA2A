import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facilities-agent")

app = FastAPI(title="Facilities Agent Microservice", version="1.0.0")

# Standard A2A Metadata Card
AGENT_CARD = {
    "agent_name": "facilities_agent",
    "description": "Manages IT and Facilities requests including room booking.",
    "endpoint": "http://localhost:8001/api/v1/execute",
    "version": "1.0.0",
    "capabilities": ["room_booking"],
    "input_schema": {
        "type": "object",
        "properties": {
            "time": {"type": "string", "description": "Time or date for the booking"}
        },
        "required": ["time"]
    }
}

class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field("2.0", pattern="^2.0$")
    method: str
    params: Dict[str, Any]
    id: str

class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[JsonRpcError] = None
    id: str

@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return AGENT_CARD

@app.post("/api/v1/execute", response_model=JsonRpcResponse)
def execute_task(request: JsonRpcRequest):
    logger.info(f"Received task: {request.method} with params: {request.params}")
    
    if request.method not in AGENT_CARD["capabilities"]:
        return JsonRpcResponse(
            id=request.id,
            error=JsonRpcError(code=-32601, message=f"Method '{request.method}' not supported")
        )
        
    try:
        if request.method == "room_booking":
            time_val = request.params.get("time", "unknown")
            booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
            
            result = {
                "status": "SUCCESS",
                "booking_id": booking_id,
                "room": "Conference Room A",
                "calendar_invite_url": f"https://calendar.internal/{booking_id}"
            }
            
            return JsonRpcResponse(id=request.id, result=result)
            
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        return JsonRpcResponse(
            id=request.id,
            error=JsonRpcError(code=-32000, message="Internal Agent Error", data=str(e))
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
