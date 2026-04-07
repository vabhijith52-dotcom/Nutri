# backend/routers/progress.py
from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from services import supabase_service as db

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/streak")
def get_streak(user=Depends(get_current_user)):
    profile = db.get_profile(user.id) or {}
    return {
        "current_streak":   profile.get("current_streak", 0),
        "longest_streak":   profile.get("longest_streak", 0),
        "last_streak_date": profile.get("last_streak_date"),
    }


@router.get("/weekly-nutrients")
def weekly_nutrients(user=Depends(get_current_user)):
    """
    Returns 7-day daily calorie targets from active diet plan.
    (As confirmed: graph shows PLAN targets, not actual consumed)
    """
    plan = db.get_active_diet_plan(user.id)
    if not plan or not plan.get("daily_targets"):
        return {"data": [], "has_plan": False}

    daily_targets = plan["daily_targets"]
    DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    data = []
    for day in DAYS:
        targets = daily_targets.get(day, {})
        plan_data = plan.get("plan_data", {}).get(day, {})
        total_cal = targets.get("calories", 0)
        breakfast_cal = plan_data.get("breakfast", {}).get("calories", 0) if isinstance(plan_data.get("breakfast"), dict) else 0
        lunch_cal     = plan_data.get("lunch", {}).get("calories", 0)     if isinstance(plan_data.get("lunch"), dict) else 0
        dinner_cal    = plan_data.get("dinner", {}).get("calories", 0)    if isinstance(plan_data.get("dinner"), dict) else 0

        data.append({
            "day":       day[:3],
            "calories":  total_cal or (breakfast_cal + lunch_cal + dinner_cal),
            "breakfast": breakfast_cal,
            "lunch":     lunch_cal,
            "dinner":    dinner_cal,
        })

    return {"data": data, "has_plan": True}


@router.get("/monthly-summary")
def monthly_summary(user=Depends(get_current_user)):
    this_month, last_month = db.get_monthly_analyses(user.id)

    def avg_risk(rows):
        if not rows:
            return 0
        return round(sum(r["risk_score"] for r in rows if r["risk_score"] is not None)
                     / len(rows), 1)

    this_avg = avg_risk(this_month)
    last_avg = avg_risk(last_month)
    trend = "better" if this_avg < last_avg else "worse" if this_avg > last_avg else "same"

    return {
        "this_month":  {"count": len(this_month), "avg_risk": this_avg},
        "last_month":  {"count": len(last_month), "avg_risk": last_avg},
        "trend":       trend,
        "this_month_count": len(this_month),
        "last_month_count": len(last_month),
    }