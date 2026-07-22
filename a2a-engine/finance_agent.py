import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import psycopg
import json
import os

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance-agent")

app = FastAPI(title="Finance Agent Microservice", version="1.0.0")

# Internal Corporate Product Catalog with Pricing in INR
CATALOG = {
    "premium_lunches": 600.0,
    "basic_lunches": 300.0,
    "office_supplies_pack": 1500.0,
}

# Standard A2A Metadata Card
AGENT_CARD = {
    "agent_name": "finance_agent",
    "description": "Handles corporate expense procurement and budget authorization checks.",
    "endpoint": "http://localhost:8000/api/v1/execute",
    "version": "1.0.0",
    "capabilities": ["expense_procurement"],
    "input_schema": {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": list(CATALOG.keys())},
            "quantity": {"type": "integer", "minimum": 1},
            "approved_by": {"type": "string", "description": "Required if total amount > 5000 INR"}
        },
        "required": ["item", "quantity"]
    }
}

# Request and Response models for standard JSON-RPC 2.0
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

@app.on_event("startup")
def register_agent():
    DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_registry (agent_name, description, endpoint, version, capabilities, input_schema, output_schema)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (agent_name) DO UPDATE SET
                        endpoint = EXCLUDED.endpoint,
                        capabilities = EXCLUDED.capabilities,
                        input_schema = EXCLUDED.input_schema;
                """, (
                    AGENT_CARD["agent_name"],
                    AGENT_CARD["description"],
                    AGENT_CARD["endpoint"],
                    AGENT_CARD["version"],
                    json.dumps(AGENT_CARD["capabilities"]),
                    json.dumps(AGENT_CARD["input_schema"]),
                    json.dumps({"type": "object"})
                ))
            conn.commit()
        logger.info("Successfully registered Finance Agent in PostgreSQL agent_registry.")
    except Exception as e:
        logger.error(f"Failed to register in database: {e}")

@app.post("/api/v1/execute", response_model=JsonRpcResponse)
def execute_procurement(request: JsonRpcRequest):
    if request.method != "expense_procurement":
        logger.error(f"Unrecognized capability method invoked: {request.method}")
        return JsonRpcResponse(
            error=JsonRpcError(code=-32601, message=f"Method not found: {request.method}"),
            id=request.id
        )
    
    params = request.params
    item = params.get("item")
    quantity = params.get("quantity")
    approved_by = params.get("approved_by")
    
    if not item or not isinstance(quantity, int) or quantity <= 0:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32602, message="Invalid method parameters: 'item' and 'quantity' are required"),
            id=request.id
        )
    
    # Resolve Price
    price_per_unit = CATALOG.get(item)
    if not price_per_unit:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32002, message=f"Item '{item}' is not registered in the catalog"),
            id=request.id
        )
    
    total_cost = price_per_unit * quantity
    
    # Financial Compliance Check (5000 INR Limit)
    if total_cost > 5000.0 and not approved_by:
        logger.error(f"Compliance Violation: Expense of {total_cost} INR requires manager approval.")
        return JsonRpcResponse(
            error=JsonRpcError(
                code=-32001, 
                message=f"Financial Compliance Limit Exceeded. Total cost is {total_cost} INR. Requires 'approved_by' manager approval token.",
                data={"total_cost": total_cost, "requires_approval": True}
            ),
            id=request.id
        )
    
    # Transaction processed successfully
    txn_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    invoice_id = f"INV-2026-{uuid.uuid4().hex[:6].upper()}"
    
    if approved_by:
        logger.info(f"Compliance check passed: Expense of {total_cost} INR approved by '{approved_by}'")
    logger.info(f"Processed transaction {txn_id} for {total_cost} INR")
    
    return JsonRpcResponse(
        result={
            "status": "SETTLED",
            "transaction_id": txn_id,
            "invoice_id": invoice_id,
            "total_cost": total_cost,
            "currency": "INR",
            "message": f"Successfully purchased {quantity} x {item}."
        },
        id=request.id
    )
