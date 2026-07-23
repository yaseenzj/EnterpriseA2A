import psycopg
import os

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

schema = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. DBRegistry: Capability Directory & Schema Registries
CREATE TABLE IF NOT EXISTS agent_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    endpoint VARCHAR(255) NOT NULL,
    version VARCHAR(20) DEFAULT '1.0.0',
    capabilities JSONB NOT NULL,
    input_schema JSONB,
    output_schema JSONB,
    health_status VARCHAR(50) DEFAULT 'HEALTHY',
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. DBRAG: Long-Term Enterprise Memory Vector Store (using tsvector for Full-Text Search)
CREATE TABLE IF NOT EXISTS enterprise_knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || content)) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create an index for faster text search
CREATE INDEX IF NOT EXISTS knowledge_search_idx ON enterprise_knowledge_base USING GIN (search_vector);
"""

seed_data = [
    (
        "Travel & Expense Policy",
        "Employees are permitted to expense premium lunches up to 600 INR per person. Any expense above 5000 INR total requires explicit manager approval. Flights must be booked in economy class unless the duration is over 8 hours.",
        "Finance"
    ),
    (
        "IT Support Equipment Request",
        "All employees are eligible for a standard laptop refresh every 3 years. Monitors and accessories can be requested via the IT portal. Approvals are required for specialized equipment.",
        "IT"
    )
]

def init_db():
    try:
        with psycopg.connect(DB_URI, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(schema)
                
                # Insert seed data
                for title, content, category in seed_data:
                    cur.execute("""
                        INSERT INTO enterprise_knowledge_base (title, content, category)
                        SELECT %s, %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM enterprise_knowledge_base WHERE title = %s
                        )
                    """, (title, content, category, title))
                    
                print("Database schema initialized and seeded successfully.")
    except Exception as e:
        print(f"Error initializing DB: {e}")

if __name__ == "__main__":
    init_db()
