import os
import psycopg
import logging
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError

logger = logging.getLogger("knowledge-agent")

def handle_retrieve_knowledge(request: JsonRpcRequest) -> JsonRpcResponse:
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
