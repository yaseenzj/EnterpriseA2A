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
