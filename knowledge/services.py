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
                    SELECT title, content, ts_rank(search_vector, to_tsquery('english', replace(plainto_tsquery('english', %s)::text, '&', '|'))) as rank
                    FROM enterprise_knowledge_base
                    WHERE search_vector @@ to_tsquery('english', replace(plainto_tsquery('english', %s)::text, '&', '|'))
                    ORDER BY rank DESC
                    LIMIT 10;
                """, (query, query))
                
                results = cur.fetchall()
                
        if not results:
            answer = "I could not find any enterprise policies regarding your query."
        else:
            snippets = [f"[{r[0]}]: {r[1]}" for r in results]
            context = "\n\n".join(snippets)
            
            try:
                from langchain_groq import ChatGroq
                from langchain_core.messages import HumanMessage, SystemMessage
                
                llm = ChatGroq(model="llama-3.3-70b-versatile")
                
                messages = [
                    SystemMessage(content="You are a helpful enterprise knowledge assistant. Answer the user's question concisely based ONLY on the provided context. If the exact answer isn't available but there is a closely related policy (like reimbursement rules for what they are asking about), summarize that related policy instead. Only if there is absolutely nothing relevant in the context, say 'I cannot find the answer in the provided policies.'"),
                    HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
                ]
                
                response = llm.invoke(messages)
                answer = response.content
            except Exception as e:
                logger.error(f"LLM Synthesis failed: {e}")
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
