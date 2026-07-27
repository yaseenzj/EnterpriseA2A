AGENT_CARD = {
    "agent_name": "IT_Agent",
    "description": "Manages IT and Facilities requests including room booking.",
    "endpoint": "http://127.0.0.1:8001/api/v1/execute",
    "version": "1.0.0",
    "capabilities": ["room_booking"],
    "input_schema": {
        "type": "object",
        "properties": {
            "time": {"type": "string", "description": "Time or date for the booking"}
        },
        "required": ["time"]
    }
}
