import os
import psycopg
import jwt
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
load_dotenv()

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"
bearer = HTTPBearer()
router = APIRouter(prefix="/api/v1", tags=["approvals"])

def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_manager_or_admin(token: dict = Depends(decode_token)):
    if token.get("role") not in ("Manager", "Admin"):
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    return token

def require_admin(token: dict = Depends(decode_token)):
    if token.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token

def get_db():
    return psycopg.connect(DB_URI)

def fmt_approval(r):
    return {
        "id": str(r[0]),
        "thread_id": r[1],
        "request_summary": r[2],
        "requested_by": r[3],
        "status": r[4],
        "actioned_by": r[5],
        "action_time": r[6].isoformat() if r[6] else None,
        "created_at": r[7].isoformat() if r[7] else None,
    }

# ─── Approval endpoints ────────────────────────────────────────────────────────

@router.get("/approvals/pending")
def get_pending_approvals(token: dict = Depends(require_manager_or_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, thread_id, request_summary, requested_by, status, actioned_by, action_time, created_at "
                "FROM pending_approvals WHERE status = 'PENDING' ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
    return [fmt_approval(r) for r in rows]

@router.get("/approvals/my-actions")
def get_my_actions(token: dict = Depends(require_manager_or_admin)):
    me = token.get("username")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, thread_id, request_summary, requested_by, status, actioned_by, action_time, created_at "
                "FROM pending_approvals WHERE actioned_by = %s ORDER BY action_time DESC",
                (me,)
            )
            rows = cur.fetchall()
    return [fmt_approval(r) for r in rows]

@router.get("/approvals/all")
def get_all_approvals(token: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, thread_id, request_summary, requested_by, status, actioned_by, action_time, created_at "
                "FROM pending_approvals ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
    return [fmt_approval(r) for r in rows]

# ─── Workflow history for the current user ─────────────────────────────────────

@router.get("/workflows/my-history")
def get_my_history(token: dict = Depends(decode_token)):
    me = token.get("username")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id, user_id, status, start_time, end_time, processing_time_ms "
                "FROM workflow_metrics WHERE user_id = %s ORDER BY start_time DESC LIMIT 50",
                (me,)
            )
            rows = cur.fetchall()
    return [{
        "thread_id": r[0],
        "user_id": r[1],
        "status": r[2],
        "start_time": r[3].isoformat() if r[3] else None,
        "end_time": r[4].isoformat() if r[4] else None,
        "processing_time_ms": r[5],
    } for r in rows]
