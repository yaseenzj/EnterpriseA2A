from pydantic import BaseModel

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict
    id: str

class JsonRpcError(BaseModel):
    code: int
    message: str

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: dict | None = None
    error: JsonRpcError | None = None
    id: str
