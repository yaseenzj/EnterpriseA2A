-- PostgreSQL Schema Setup for Unified Enterprise Database Cluster
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

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

-- 2. DBCheckpoint: State persistence for workflow pauses (Human-in-the-Loop)
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id VARCHAR(255) NOT NULL,
    parent_id VARCHAR(255),
    checkpoint BYTEA NOT NULL,
    metadata BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- 3. DBRAG: Long-Term Enterprise Memory Vector Store
CREATE TABLE IF NOT EXISTS enterprise_knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    embedding VECTOR(1536), -- Designed for standard 1536-dim embedding models
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS knowledge_vector_hnsw_idx 
ON enterprise_knowledge_base USING hnsw (embedding vector_cosine_ops);
