import os
import psycopg
import logging
from datetime import datetime

logger = logging.getLogger("metrics")
DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

def log_workflow_start(thread_id: str):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO workflow_metrics (thread_id, status) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (thread_id, "RUNNING")
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log workflow start: {e}")

def log_workflow_end(thread_id: str, status: str):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                # Calculate processing time by comparing current time with start_time
                cur.execute(
                    "UPDATE workflow_metrics SET status = %s, end_time = CURRENT_TIMESTAMP, processing_time_ms = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time)) * 1000 WHERE thread_id = %s",
                    (status, thread_id)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log workflow end: {e}")

def get_metrics_dashboard():
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM workflow_metrics")
                total_workflows = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM workflow_metrics WHERE status = 'COMPLETED' OR status = 'APPROVED_AND_COMPLETED'")
                successful_workflows = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM workflow_metrics WHERE status = 'FAILED' OR status = 'COMPLETED_WITH_ERRORS'")
                failed_workflows = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM workflow_metrics WHERE status = 'PENDING_APPROVAL'")
                pending_workflows = cur.fetchone()[0]
                
                cur.execute("SELECT AVG(processing_time_ms) FROM workflow_metrics WHERE processing_time_ms IS NOT NULL")
                avg_processing_time = cur.fetchone()[0]
                
                return {
                    "total_workflows": total_workflows,
                    "successful_workflows": successful_workflows,
                    "failed_workflows": failed_workflows,
                    "pending_workflows": pending_workflows,
                    "average_processing_time_ms": round(avg_processing_time, 2) if avg_processing_time else 0
                }
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
        return {}
