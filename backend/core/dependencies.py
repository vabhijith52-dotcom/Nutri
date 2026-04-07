# backend/core/dependencies.py
from fastapi import Header, HTTPException
from typing import Optional
from services.supabase_service import get_user_from_token


def get_current_user(authorization: str = Header(...)):
    """Required auth — raises 401 if token is missing or invalid."""
    token = authorization.removeprefix("Bearer ").strip()
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token. Please log in again.")
    return user


def get_optional_user(authorization: Optional[str] = Header(None)):
    """Optional auth — returns None if no token. Used on /meals/analyze so it
    works without login but saves to DB when authenticated."""
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return get_user_from_token(token)
