# backend/services/supabase_service.py
from supabase import create_client, Client
from core.config import settings

# Service key — bypasses RLS for backend operations
_client: Client = create_client(settings.supabase_url, settings.supabase_service_key)
# Anon key — for auth operations (signup/login use user's JWT flow)
_anon: Client = create_client(settings.supabase_url, settings.supabase_anon_key)


def get_client() -> Client:
    return _client


def get_user_from_token(token: str):
    """Validate JWT and return Supabase user object."""
    try:
        return _client.auth.get_user(token).user
    except Exception:
        return None


# ── Profiles ──────────────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict | None:
    try:
        r = _client.table("profiles").select("*").eq("user_id", user_id).single().execute()
        return r.data
    except Exception:
        return None


def upsert_profile(user_id: str, data: dict) -> dict:
    data["user_id"] = user_id
    r = _client.table("profiles").upsert(data, on_conflict="user_id").execute()
    return r.data[0] if r.data else {}


# ── Health Metrics ────────────────────────────────────────────────────────────

def save_metrics(user_id: str, metrics: list) -> list:
    rows = [{"user_id": user_id, "metric_type": m["metric_type"],
             "value": m["value"], "unit": m.get("unit"), "source": m.get("source","manual")}
            for m in metrics]
    r = _client.table("health_metrics").insert(rows).execute()
    return r.data or []


def get_metrics_history(user_id: str, metric_type: str = None, limit: int = 30) -> list:
    q = _client.table("health_metrics").select("*").eq("user_id", user_id)
    if metric_type:
        q = q.eq("metric_type", metric_type)
    r = q.order("recorded_at", desc=True).limit(limit).execute()
    return r.data or []


def get_latest_metrics(user_id: str) -> dict:
    """Return most recent value for each metric type."""
    r = _client.table("health_metrics").select("*").eq("user_id", user_id) \
        .order("recorded_at", desc=True).limit(100).execute()
    latest = {}
    for row in (r.data or []):
        mt = row["metric_type"]
        if mt not in latest:
            latest[mt] = row
    return latest


# ── Meals ─────────────────────────────────────────────────────────────────────

def save_meal(user_id: str, meal_data: dict) -> dict:
    meal_data["user_id"] = user_id
    r = _client.table("meals").insert(meal_data).execute()
    return r.data[0] if r.data else {}


def save_analysis(user_id: str, meal_id: str, analysis_data: dict) -> dict:
    analysis_data["user_id"] = user_id
    analysis_data["meal_id"] = meal_id
    r = _client.table("meal_analyses").insert(analysis_data).execute()
    return r.data[0] if r.data else {}


def get_meal_analysis(analysis_id: str) -> dict | None:
    try:
        r = _client.table("meal_analyses").select("*, meals(*)") \
            .eq("id", analysis_id).single().execute()
        return r.data
    except Exception:
        return None


def get_user_meals(user_id: str, limit: int = 20) -> list:
    r = (_client.table("meals").select("*, meal_analyses(*)")
         .eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute())
    return r.data or []


def delete_meal(meal_id: str, user_id: str) -> bool:
    _client.table("meals").delete().eq("id", meal_id).eq("user_id", user_id).execute()
    return True


# ── Diet Plans ────────────────────────────────────────────────────────────────

def save_diet_plan(user_id: str, plan_data: dict, daily_targets: dict,
                   constraints: dict) -> dict:
    # Deactivate previous plans
    _client.table("diet_plans").update({"is_active": False}).eq("user_id", user_id).execute()
    r = _client.table("diet_plans").insert({
        "user_id": user_id, "plan_data": plan_data,
        "daily_targets": daily_targets, "constraints": constraints,
        "is_active": True,
    }).execute()
    return r.data[0] if r.data else {}


def get_active_diet_plan(user_id: str) -> dict | None:
    try:
        r = (_client.table("diet_plans").select("*")
             .eq("user_id", user_id).eq("is_active", True)
             .order("created_at", desc=True).limit(1).execute())
        return r.data[0] if r.data else None
    except Exception:
        return None


def get_diet_plan_history(user_id: str) -> list:
    r = (_client.table("diet_plans").select("id,created_at,is_active,constraints")
         .eq("user_id", user_id).order("created_at", desc=True).limit(10).execute())
    return r.data or []


# ── Daily Intake ──────────────────────────────────────────────────────────────

def get_or_create_daily_intake(user_id: str, date_str: str) -> dict:
    try:
        r = _client.table("daily_intake").select("*") \
            .eq("user_id", user_id).eq("date", date_str).single().execute()
        return r.data
    except Exception:
        # Create new row
        r = _client.table("daily_intake").insert({
            "user_id": user_id, "date": date_str,
        }).execute()
        return r.data[0] if r.data else {}


def update_daily_intake(user_id: str, date_str: str, updates: dict) -> dict:
    r = (_client.table("daily_intake").update(updates)
         .eq("user_id", user_id).eq("date", date_str).execute())
    return r.data[0] if r.data else {}


def add_extra_food_to_intake(user_id: str, date_str: str, food_entry: dict) -> dict:
    """Append a food item to extra_foods JSONB array and increment nutrient totals."""
    intake = get_or_create_daily_intake(user_id, date_str)
    extra_foods = list(intake.get("extra_foods") or [])
    extra_foods.append(food_entry)

    nutrition = food_entry.get("nutrition", {})
    updates = {
        "extra_foods":       extra_foods,
        "calories_consumed": round(float(intake.get("calories_consumed") or 0) + float(nutrition.get("calories", 0)), 1),
        "carbs_consumed":    round(float(intake.get("carbs_consumed") or 0) + float(nutrition.get("carbs", 0)), 1),
        "protein_consumed":  round(float(intake.get("protein_consumed") or 0) + float(nutrition.get("protein", 0)), 1),
        "fat_consumed":      round(float(intake.get("fat_consumed") or 0) + float(nutrition.get("fat", 0)), 1),
        "fiber_consumed":    round(float(intake.get("fiber_consumed") or 0) + float(nutrition.get("fiber", 0)), 1),
        "sodium_consumed":   round(float(intake.get("sodium_consumed") or 0) + float(nutrition.get("sodium", 0)), 1),
        "sugar_consumed":    round(float(intake.get("sugar_consumed") or 0) + float(nutrition.get("sugar", 0)), 1),
    }
    return update_daily_intake(user_id, date_str, updates)


def save_bot_message(user_id: str, date_str: str, role: str, content: str) -> None:
    """Append a message to the daily conversation log (max 10 messages)."""
    intake = get_or_create_daily_intake(user_id, date_str)
    conversation = list(intake.get("bot_conversation") or [])
    conversation.append({"role": role, "content": content})
    conversation = conversation[-10:]  # keep last 10
    update_daily_intake(user_id, date_str, {"bot_conversation": conversation})


def get_bot_conversation(user_id: str, date_str: str) -> list:
    intake = get_or_create_daily_intake(user_id, date_str)
    return list(intake.get("bot_conversation") or [])


# ── Progress ──────────────────────────────────────────────────────────────────

def get_weekly_intake(user_id: str) -> list:
    """Last 7 days of daily_intake rows."""
    r = (_client.table("daily_intake").select("*")
         .eq("user_id", user_id).order("date", desc=True).limit(7).execute())
    return list(reversed(r.data or []))


def get_monthly_analyses(user_id: str) -> tuple[list, list]:
    """Return this month and last month meal analyses."""
    from datetime import date, timedelta
    today = date.today()
    this_month_start = today.replace(day=1).isoformat()
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()

    r = (_client.table("meal_analyses").select("risk_score,created_at")
         .eq("user_id", user_id)
         .gte("created_at", last_month_start)
         .order("created_at", desc=True).execute())
    rows = r.data or []

    this_month = [row for row in rows if row["created_at"] >= this_month_start]
    last_month = [row for row in rows if row["created_at"] < this_month_start]
    return this_month, last_month