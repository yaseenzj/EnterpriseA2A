import jwt
from typing import List
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .orchestrator import AuthContext

import os

security_agent = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "enterprise_super_secret_key")
JWT_ALGORITHM = "HS256"

def verify_and_decode_jwt(credentials: HTTPAuthorizationCredentials = Depends(security_agent)) -> AuthContext:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return AuthContext(
            user_id=payload.get("sub"),
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
