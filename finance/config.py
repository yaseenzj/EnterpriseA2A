CATALOG = {
    "premium_lunches": 600.0,
    "basic_lunches": 300.0,
    "office_supplies_pack": 1500.0,
    "taxi_ride": 800.0,
    "software_license": 15000.0,
}

AGENT_CARD = {
    "agent_name": "Finance_Agent",
    "description": "Handles corporate expense procurement and budget authorization checks.",
    "endpoint": "http://127.0.0.1:8000/api/v1/execute",
    "version": "1.0.0",
    "capabilities": ["expense_procurement"],
    "input_schema": {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": list(CATALOG.keys())},
            "quantity": {"type": "integer", "minimum": 1},
            "justification": {"type": "string", "description": "The contextual reason or justification for this expense, provided by the user."},
            "approved_by": {"type": "string", "description": "Required if total amount > 5000 INR or if the item violates policy."}
        },
        "required": ["item", "quantity", "justification"]
    }
}
