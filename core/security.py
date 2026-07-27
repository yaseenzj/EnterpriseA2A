import jwt
from typing import List, Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os

security_agent = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is missing. Please set it in your .env file.")
JWT_ALGORITHM = "HS256"

class AuthContext(BaseModel):
    user_id: str
    username: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    scopes: List[str] = []

def verify_and_decode_jwt(credentials: HTTPAuthorizationCredentials = Depends(security_agent)) -> AuthContext:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return AuthContext(
            user_id=payload.get("sub"),
            username=payload.get("username", payload.get("sub")),
            department=payload.get("department"),
            role=payload.get("role"),
            scopes=payload.get("scopes", [])
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT authorization token")

def check_rbac_scopes(required_scopes: List[str]):
    def dependency(auth: AuthContext = Depends(verify_and_decode_jwt)):
        for scope in required_scopes:
            if scope not in auth.scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"RBAC Enforcement Violation: Missing required scope '{scope}'"
                )
        return auth
    return dependency
