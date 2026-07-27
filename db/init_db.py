import psycopg
import os
from dotenv import load_dotenv
load_dotenv()

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

-- 4. DBMetrics: Workflow Execution Tracking
CREATE TABLE IF NOT EXISTS workflow_metrics (
    thread_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    processing_time_ms INTEGER
);

-- 5. DBAlerts: System Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. DBAuth: Users with real credentials and roles
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'Employee',
    department VARCHAR(100) NOT NULL DEFAULT 'General',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. DBApprovals: Track every pending/actioned workflow approval
CREATE TABLE IF NOT EXISTS pending_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id VARCHAR(255) NOT NULL,
    request_summary TEXT,
    requested_by VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    actioned_by VARCHAR(255),
    action_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
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
    ),
    (
        "Conference Room Booking Policy",
        "Conference rooms must be booked at least 1 hour in advance. The maximum booking duration is 4 consecutive hours to ensure fair usage across departments. Room capacities range from 4 to 20 people. External guests must be registered at the lobby.",
        "IT"
    ),
    (
        "Corporate Catering & Food Policy",
        "Basic lunches (sandwiches, salads) do not require approval and are budgeted at 300 INR per person. Premium lunches (hot meals, multi-course) are allowed only for external client meetings or executive team meetings, budgeted up to 600 INR per person. Alcohol is strictly prohibited during core business hours.",
        "Finance"
    ),
    (
        "Remote Work & Work-From-Home Policy",
        "Employees are allowed to work remotely up to 3 days per week. A one-time stipend of 25,000 INR is provided to setup a home office, which can be used for desks, chairs, and monitors. Internet bills can be reimbursed up to 1,500 INR monthly.",
        "HR"
    ),
    (
        "Software Procurement Policy",
        "Any software license costing less than 10,000 INR annually can be expensed directly without prior approval. Enterprise software, SaaS subscriptions, or developer tools costing more than 10,000 INR require approval from both the IT Director and the Department Head.",
        "IT"
    ),
    (
        "Guest Wi-Fi and Security Policy",
        "External visitors and clients must connect exclusively to the 'Corp-Guest' network. The guest network password changes every Monday and can be requested from the front desk. Employees must never share the internal 'Corp-Secure' network credentials with guests.",
        "Security"
    ),
    (
        "Ride-Sharing & Taxi Reimbursement",
        "Employees traveling for client meetings or returning from the office after 9:00 PM are eligible for fully reimbursed Uber or Ola rides. Receipts must be attached to the expense report. Daily commutes during normal hours are not reimbursable.",
        "Finance"
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
