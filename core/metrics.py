import os
import psycopg
import logging
from datetime import datetime

logger = logging.getLogger("metrics")
DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

def log_workflow_start(thread_id: str, user_id: str = None):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO workflow_metrics (thread_id, user_id, status) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (thread_id, user_id, "RUNNING")
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
                
                cur.execute("SELECT AVG(EXTRACT(EPOCH FROM (action_time - created_at)) / 60) FROM pending_approvals WHERE action_time IS NOT NULL")
                avg_approval_time = cur.fetchone()[0]
                
                cur.execute(
                    "SELECT thread_id, user_id, status, start_time, end_time, processing_time_ms "
                    "FROM workflow_metrics ORDER BY start_time DESC LIMIT 20"
                )
                recent_rows = cur.fetchall()
                recent_workflows = [{
                    "thread_id": r[0], "user_id": r[1], "status": r[2],
                    "start_time": r[3].isoformat() if r[3] else None,
                    "end_time": r[4].isoformat() if r[4] else None,
                    "duration_seconds": round(r[5] / 1000, 2) if r[5] else None
                } for r in recent_rows]
                
                return {
                    "total_workflows": total_workflows,
                    "successful_workflows": successful_workflows,
                    "failed_workflows": failed_workflows,
                    "pending_workflows": pending_workflows,
                    "avg_approval_time_minutes": round(avg_approval_time, 1) if avg_approval_time else 0,
                    "recent_workflows": recent_workflows
                }
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
        return {}
