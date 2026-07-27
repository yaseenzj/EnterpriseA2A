AGENT_CARD = {
    "agent_name": "Knowledge_Agent",
    "description": "Retrieves enterprise knowledge and policies",
    "endpoint": "http://127.0.0.1:8002/api/v1/execute",
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
