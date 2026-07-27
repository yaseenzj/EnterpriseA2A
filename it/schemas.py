from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

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
