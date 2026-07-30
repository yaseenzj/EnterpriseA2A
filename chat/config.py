AGENT_CARD = {
    "agent_name": "Chat_Agent",
    "description": "Handles general conversational inputs, greetings, and basic questions about the enterprise. Does not perform actions or answer advanced out-of-scope queries.",
    "endpoint": "http://127.0.0.1:8003/api/v1/execute",
    "version": "1.0.0",
    "capabilities": ["general_chat"],
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The user's conversational query or greeting."},
            "chat_history": {"type": "array", "description": "Array of past messages for context, e.g. [{'role': 'user', 'content': '...'}]"}
        },
        "required": ["query"]
    }
}
