import logging
from fastapi import FastAPI
from .config import AGENT_CARD
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError
from .services import handle_room_booking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facilities-agent")

app = FastAPI(title="Facilities Agent Microservice", version="1.0.0")

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
            return handle_room_booking(request)
            
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        return JsonRpcResponse(
            id=request.id,
            error=JsonRpcError(code=-32000, message="Internal Agent Error", data=str(e))
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
