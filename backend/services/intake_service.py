# backend/services/intake_service.py
"""
Daily intake tracking and streak logic.
Streak rule: any meal logged to daily_intake = streak day counts.
"""
from datetime import date, timedelta
from services import supabase_service as db


def get_today_str() -> str:
    return date.today().isoformat()


def update_streak(user_id: str, profile: dict) -> dict:
    """
    Called after any meal is logged.
    Returns updated streak fields to save to profile.
    """
    today       = date.today()
    today_str   = today.isoformat()
    yesterday   = (today - timedelta(days=1)).isoformat()

    last_date_str = profile.get("last_streak_date")
    current       = int(profile.get("current_streak") or 0)
    longest       = int(profile.get("longest_streak") or 0)

    if last_date_str == today_str:
        # Already counted today — no change
        return {"current_streak": current, "longest_streak": longest,
                "last_streak_date": today_str}

    if last_date_str == yesterday:
        # Consecutive day — increment
        current += 1
    else:
        # Gap (or first log ever) — reset to 1
        current = 1

    longest = max(longest, current)

    return {
        "current_streak":  current,
        "longest_streak":  longest,
        "last_streak_date": today_str,
    }


def compute_daily_targets(diet_plan_data: dict) -> dict:
    """
    Pre-compute daily nutrient targets from a 7-day plan.
    Sums breakfast + lunch + dinner nutrients for each day.
    """
    DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    targets = {}
    for day in DAYS:
        day_data = diet_plan_data.get(day, {})
        total_cal = sum(
            meal.get("calories", 0)
            for meal in day_data.values()
            if isinstance(meal, dict)
        )
        targets[day] = {"calories": total_cal}
    return targets