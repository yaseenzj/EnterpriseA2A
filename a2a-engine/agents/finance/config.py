CATALOG = {
    "premium_lunches": 600.0,
    "basic_lunches": 300.0,
    "office_supplies_pack": 1500.0,
}

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
