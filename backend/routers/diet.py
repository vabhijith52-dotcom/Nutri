# backend/routers/diet.py
from fastapi import APIRouter, Depends, HTTPException
from models.schemas import DietPlanRequest
from core.dependencies import get_current_user
from services.gemini_service import generate_diet_plan
from services.intake_service import compute_daily_targets
from services import supabase_service as db

router = APIRouter(prefix="/diet", tags=["diet"])


@router.post("/generate")
async def generate(body: DietPlanRequest, user=Depends(get_current_user)):
    """Generate a 7-day personalised diet plan using Gemini."""
    profile = db.get_profile(user.id) or {}
    history = db.get_user_meals(user.id, limit=10)

    # Get recent meal descriptions for context
    recent = []
    for m in history:
        analyses = m.get("meal_analyses") or []
        risk = analyses[0]["risk_score"] if analyses else None
        recent.append({"description": m.get("description",""), "composite_score": risk})

    plan_data = await generate_diet_plan(
        profile         = profile,
        meal_history    = recent,
        food_preference = body.food_preference,
        allergies       = body.allergies,
    )

    if not plan_data:
        raise HTTPException(500, "Diet plan generation failed. Check Gemini API key.")

    # Pre-compute daily calorie targets for the weekly graph
    daily_targets = compute_daily_targets(plan_data)

    constraints = {
        "food_preference": body.food_preference,
        "allergies":       body.allergies,
    }

    saved = db.save_diet_plan(user.id, plan_data, daily_targets, constraints)
    return {
        "id":            saved.get("id"),
        "plan_data":     plan_data,
        "daily_targets": daily_targets,
        "constraints":   constraints,
    }


@router.get("/active")
def get_active(user=Depends(get_current_user)):
    plan = db.get_active_diet_plan(user.id)
    return plan or {}


@router.get("/history")
def get_history(user=Depends(get_current_user)):
    return db.get_diet_plan_history(user.id)