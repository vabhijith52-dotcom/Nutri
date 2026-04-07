# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from models.schemas import SignupRequest, LoginRequest, ProfileUpdate
from core.dependencies import get_current_user
from services import supabase_service as db
from supabase import create_client
from core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
_anon = create_client(settings.supabase_url, settings.supabase_anon_key)


@router.post("/signup")
def signup(body: SignupRequest):
    try:
        result = _anon.auth.sign_up({
            "email":    body.email,
            "password": body.password,
            "options":  {"data": {"full_name": body.full_name}},
        })
        return {
            "message":      "Account created successfully.",
            "user_id":      result.user.id if result.user else None,
            "access_token": result.session.access_token if result.session else None,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/login")
def login(body: LoginRequest):
    try:
        result = _anon.auth.sign_in_with_password({
            "email": body.email, "password": body.password
        })
        profile = db.get_profile(result.user.id)
        return {
            "access_token":  result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "user_id":       result.user.id,
            "profile":       profile,
        }
    except Exception:
        raise HTTPException(401, "Invalid email or password.")


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    profile = db.get_profile(user.id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    return profile


@router.put("/profile")
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    updates = data.model_dump(exclude_none=True)
    result  = db.upsert_profile(user.id, updates)
    return {"message": "Profile updated.", "profile": result}