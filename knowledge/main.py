import logging
import json
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg
from fastapi import FastAPI
from .config import AGENT_CARD
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError
from .services import handle_retrieve_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge-agent")

app = FastAPI(title="Knowledge Agent")

@app.on_event("startup")
def register_agent():
    DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_registry (agent_name, description, endpoint, version, capabilities, input_schema, output_schema, health_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'HEALTHY')
                    ON CONFLICT (agent_name) DO UPDATE SET
                        endpoint = EXCLUDED.endpoint,
                        capabilities = EXCLUDED.capabilities,
                        input_schema = EXCLUDED.input_schema,
                        health_status = 'HEALTHY';
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
        logger.info("Successfully registered Knowledge Agent in PostgreSQL agent_registry.")
    except Exception as e:
        logger.error(f"Failed to register in database: {e}")

@app.on_event("shutdown")
def deregister_agent():
    DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_registry 
                    SET health_status = 'OFFLINE' 
                    WHERE agent_name = %s;
                """, (AGENT_CARD["agent_name"],))
            conn.commit()
        logger.info("Successfully marked Knowledge Agent as OFFLINE in PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to deregister from database: {e}")

@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return AGENT_CARD

@app.post("/api/v1/execute", response_model=JsonRpcResponse)
def execute_knowledge(request: JsonRpcRequest):
    if request.method != "retrieve_knowledge":
        return JsonRpcResponse(
            error=JsonRpcError(code=-32601, message=f"Method not found: {request.method}"),
            id=request.id
        )
        
    return handle_retrieve_knowledge(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)
