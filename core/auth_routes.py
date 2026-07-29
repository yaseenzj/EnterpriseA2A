import os
import psycopg
import jwt
import bcrypt
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"

bearer = HTTPBearer()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ROLE_SCOPES = {
    "Employee": ["execute:room_booking", "execute:expense_procurement"],
    "Manager":  ["execute:room_booking", "execute:expense_procurement", "approve:workflows"],
    "Admin":    ["execute:room_booking", "execute:expense_procurement", "approve:workflows", "admin:all"],
}

class SignupRequest(BaseModel):
    username: str
    password: str
    department: str = "General"

class LoginRequest(BaseModel):
    username: str
    password: str

class RoleUpdateRequest(BaseModel):
    role: str

class DepartmentUpdateRequest(BaseModel):
    department: str

def get_db():
    return psycopg.connect(DB_URI)

def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_admin(token: dict = Depends(decode_token)):
    if token.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token

@router.post("/signup")
def signup(req: SignupRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check if this is the very first user → becomes Admin
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            role = "Admin" if count == 0 else "Employee"

            # Check username uniqueness
            cur.execute("SELECT id FROM users WHERE username = %s", (req.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username already taken")

            # Admin is system-wide — no department
            effective_dept = None if role == "Admin" else req.department
            hashed = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute(
                "INSERT INTO users (username, password_hash, role, department) VALUES (%s, %s, %s, %s) RETURNING id, username, role, department",
                (req.username, hashed, role, effective_dept)
            )
            row = cur.fetchone()
            conn.commit()

    user_id, username, role, dept = row
    scopes = ROLE_SCOPES.get(role, [])
    payload = {"sub": str(user_id), "username": username, "role": role, "department": dept, "scopes": scopes, "exp": 9999999999}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": {"id": str(user_id), "username": username, "role": role, "department": dept}}

@router.post("/login")
def login(req: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash, role, department FROM users WHERE username = %s", (req.username,))
            row = cur.fetchone()

    if not row or not bcrypt.checkpw(req.password.encode('utf-8'), row[2].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id, username, _, role, dept = row
    scopes = ROLE_SCOPES.get(role, [])
    payload = {"sub": str(user_id), "username": username, "role": role, "department": dept, "scopes": scopes, "exp": 9999999999}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": {"id": str(user_id), "username": username, "role": role, "department": dept}}

@router.get("/users")
def list_users(token: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, role, department, created_at FROM users ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [{"id": str(r[0]), "username": r[1], "role": r[2], "department": r[3], "created_at": r[4].isoformat()} for r in rows]

@router.patch(
    "/users/{username}/role",
    summary="Change User Role",
    description="**Admin only.** Set a user's role by their username. Example: `/api/v1/auth/users/alice/role`. Promoting to Admin clears their department."
)
def update_user_role(username: str, req: RoleUpdateRequest, token: dict = Depends(require_admin)):
    if req.role not in ("Employee", "Manager", "Admin"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be Employee, Manager, or Admin")
    # Admins are system-wide — clear department when promoting
    new_dept_sql = ", department = NULL" if req.role == "Admin" else ""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET role = %s{new_dept_sql} WHERE username = %s RETURNING username",
                (req.role, username)
            )
            row = cur.fetchone()
            conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return {"message": f"User '{row[0]}' role updated to {req.role}"}

@router.patch(
    "/users/{username}/department",
    summary="Transfer User Department",
    description="**Admin only.** Move a user to a different department by their username. Example: `/api/v1/auth/users/alice/department`"
)
def update_user_department(username: str, req: DepartmentUpdateRequest, token: dict = Depends(require_admin)):
    VALID_DEPTS = ('Sales', 'IT', 'Finance', 'HR', 'Operations', 'Marketing', 'General')
    if req.department not in VALID_DEPTS:
        raise HTTPException(status_code=400, detail=f"Invalid department. Must be one of: {', '.join(VALID_DEPTS)}")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET department = %s WHERE username = %s RETURNING username", (req.department, username))
            row = cur.fetchone()
            conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return {"message": f"User '{row[0]}' transferred to {req.department} department"}
