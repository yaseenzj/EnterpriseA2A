import psycopg
import json
import os

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

AGENTS = [
    {
        "agent_name": "finance_agent",
        "description": "Handles corporate expense procurement and budget authorization checks.",
        "endpoint": "http://localhost:8000/api/v1/execute",
        "version": "1.0.0",
        "capabilities": ["expense_procurement"],
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1},
                "approved_by": {"type": "string"}
            },
            "required": ["item", "quantity"]
        }
    },
    {
        "agent_name": "knowledge_agent",
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
    },
    {
        "agent_name": "facilities_agent",
        "description": "Manages IT and Facilities requests including room booking.",
        "endpoint": "http://localhost:8001/api/v1/execute",
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
]

def register_agents():
    try:
        with psycopg.connect(DB_URI, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Clear existing registry for clean slate
                cur.execute("DELETE FROM agent_registry;")
                
                for agent in AGENTS:
                    cur.execute("""
                        INSERT INTO agent_registry 
                        (agent_name, description, endpoint, version, capabilities, input_schema)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        agent["agent_name"],
                        agent["description"],
                        agent["endpoint"],
                        agent["version"],
                        json.dumps(agent["capabilities"]),
                        json.dumps(agent["input_schema"])
                    ))
                print(f"Successfully registered {len(AGENTS)} agents into PostgreSQL.")
    except Exception as e:
        print(f"Error registering agents: {e}")

if __name__ == "__main__":
    register_agents()
