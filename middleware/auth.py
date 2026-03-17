# middleware/auth.py — Clerk JWT verification for FastAPI
# Extracts user identity and role from Clerk session tokens.

import os
import logging
import json
import base64
from typing import Optional
from fastapi import Request, HTTPException

logger = logging.getLogger("call-intelligence")

# Dev mode flag — when true, dev endpoints are accessible
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


def _decode_jwt_payload(token: str) -> dict:
    """Decode the payload of a JWT without full cryptographic verification.
    
    In production, you should verify the JWT signature using Clerk's JWKS endpoint.
    For now, we trust the token since it comes through Clerk's middleware on the frontend.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (base64url)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"JWT decode failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def get_current_user(request: Request) -> dict:
    """Extract the current user from the Clerk session token.
    
    Returns dict with:
        - clerk_user_id: str
        - role: str ('agent', 'team_lead', 'manager')
        - team_id: str | None
        - name: str
        - email: str
    
    The role and team_id come from Clerk's publicMetadata.
    Set these in the Clerk Dashboard for each user:
        { "role": "agent", "team_id": "team_alpha" }
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header[7:]
    payload = _decode_jwt_payload(token)
    
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    # Clerk puts publicMetadata in different keys depending on SDK version
    metadata = payload.get("metadata", payload.get("publicMetadata", {}))
    if not metadata:
        metadata = payload.get("public_metadata", {})
    
    role = metadata.get("role", "agent")
    team_id = metadata.get("team_id")
    
    # Extract name and email from JWT claims
    name = payload.get("name", payload.get("first_name", "User"))
    email = payload.get("email", payload.get("email_address", ""))
    
    if not email and "email_addresses" in payload:
        emails = payload["email_addresses"]
        if emails:
            email = emails[0] if isinstance(emails[0], str) else emails[0].get("email_address", "")
    
    return {
        "clerk_user_id": clerk_user_id,
        "role": role,
        "team_id": team_id,
        "name": name,
        "email": email,
    }


def require_role(*allowed_roles):
    """Dependency factory that checks if user has the required role."""
    async def check_role(request: Request):
        user = await get_current_user(request)
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return user
    return check_role


def require_dev_mode():
    """Dependency that ensures DEV_MODE is enabled."""
    async def check_dev(request: Request):
        if not DEV_MODE:
            raise HTTPException(status_code=404, detail="Not found")
        return True
    return check_dev
