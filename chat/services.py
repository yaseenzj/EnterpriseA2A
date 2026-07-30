import logging
import os
import psycopg
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError

logger = logging.getLogger("chat-agent")
DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

def fetch_knowledge_context(query: str) -> str:
    """Fetch basic context from knowledge base if it matches simple terms like 'conference room'."""
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                # Basic ILIKE search
                keywords = [word for word in query.lower().split() if len(word) > 4]
                if not keywords:
                    return ""
                search_term = keywords[0]
                cur.execute("SELECT content FROM enterprise_knowledge_base WHERE content ILIKE %s LIMIT 1", (f"%{search_term}%",))
                row = cur.fetchone()
                if row:
                    return row[0]
    except Exception as e:
        logger.error(f"Failed to fetch KB for chat context: {e}")
    return ""

def handle_general_chat(request: JsonRpcRequest) -> JsonRpcResponse:
    query = request.params.get("query", "")
    
    if not query:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32602, message="Invalid method parameters: 'query' is required"),
            id=request.id
        )

    # Optional: fetch a bit of context if they ask something related to the enterprise
    context = fetch_knowledge_context(query)

    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.5)
        
        sys_prompt = f"""You are a helpful and friendly conversational assistant for an enterprise platform.
Your job is to greet users, engage in basic polite conversation, and answer simple questions about the enterprise if you have the context.

IMPORTANT RULES:
1. DO NOT write code for the user under any circumstances.
2. DO NOT answer advanced technical questions, math problems, or general world knowledge outside of basic conversation.
3. If the user asks you to write code or do a complex non-enterprise task, politely refuse and explain that you are an internal enterprise assistant.
4. Keep your responses concise (1-3 sentences max).
5. CRITICAL ANTI-HALLUCINATION RULE: DO NOT hallucinate or invent ANY schedule events, facts, or data. If you are asked to summarize a schedule or bookings, ONLY list items explicitly requested or confirmed in the chat history. If the chat history mentions booking a room or a taxi, include exactly that. NEVER make up meetings (e.g. "Marketing team", "Review meeting") out of thin air. If the user asks for their schedule and there are no actual bookings in the history, tell them they have nothing scheduled.
6. If the user is trying to book or purchase something they have already booked (e.g., a taxi at 5 PM), politely inform them that it is already booked and ask if they are sure they want to book another one (do not use the word "duplicate").

Context from Enterprise Knowledge Base (if applicable to their question):
{context}
"""
        chat_history = request.params.get("chat_history", [])
        
        messages = [
            SystemMessage(content=sys_prompt)
        ]
        
        # Append up to 30 most recent messages from history
        for msg in chat_history[-30:]:
            # Frontend might send {role: "user", content: "..."} or {role: "system", content: "..."}
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))
                
        # Append the current query
        messages.append(HumanMessage(content=query))
        
        resp = llm.invoke(messages)
        answer = resp.content

        return JsonRpcResponse(
            result={"status": "SUCCESS", "answer": answer},
            id=request.id
        )
        
    except Exception as e:
        logger.error(f"LLM Chat Error: {e}")
        return JsonRpcResponse(
            error=JsonRpcError(code=-32000, message="Internal LLM Error", data=str(e)),
            id=request.id
        )
