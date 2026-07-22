import os
import json
import logging
import psycopg
from fastapi import FastAPI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge-agent")

app = FastAPI(title="Knowledge Agent")

AGENT_CARD = {
    "agent_name": "Knowledge Agent",
    "description": "Retrieves enterprise knowledge and policies",
    "endpoint": "http://localhost:8005/api/v1/execute",
    "version": "1.0.0",
    "capabilities": ["retrieve_knowledge"],
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The user's question or search query"}
        },
        "required": ["query"]
    }
}

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
        logger.info("Successfully registered Knowledge Agent in PostgreSQL agent_registry.")
    except Exception as e:
        logger.error(f"Failed to register in database: {e}")

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
        
    query = request.params.get("query")
    if not query:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32602, message="Invalid parameters: 'query' is required"),
            id=request.id
        )
        
    DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                # PostgreSQL Full-Text Search
                cur.execute("""
                    SELECT title, content, ts_rank(search_vector, plainto_tsquery('english', %s)) as rank
                    FROM enterprise_knowledge_base
                    WHERE search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT 3;
                """, (query, query))
                
                results = cur.fetchall()
                
        if not results:
            answer = "I could not find any enterprise policies regarding your query."
        else:
            # Simple RAG simulation
            snippets = [f"[{r[0]}]: {r[1]}" for r in results]
            context = "\n\n".join(snippets)
            answer = f"Based on enterprise knowledge, here is what I found:\n\n{context}"
            
        return JsonRpcResponse(
            result={"status": "SUCCESS", "answer": answer},
            id=request.id
        )
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return JsonRpcResponse(
            error=JsonRpcError(code=-32000, message=f"Database error: {str(e)}"),
            id=request.id
        )
