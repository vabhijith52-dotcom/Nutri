# backend/routers/bot.py
from fastapi import APIRouter, Depends
from models.schemas import BotMessage
from core.dependencies import get_current_user
from services.gemini_service import bot_respond
from services.intake_service import update_streak, get_today_str
from services.scoring_engine import search_foods, score_food
from services import supabase_service as db

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/message")
async def send_message(body: BotMessage, user=Depends(get_current_user)):
    """
    Main bot endpoint. Gemini receives full daily context and responds.
    If food was logged, updates daily_intake and streak.
    """
    today   = get_today_str()
    profile = db.get_profile(user.id) or {}
    plan    = db.get_active_diet_plan(user.id)
    intake  = db.get_or_create_daily_intake(user.id, today)

    # Build full context for Gemini
    context = {
        "profile":      profile,
        "today_intake": intake,
        "diet_plan":    plan,
        "streak":       profile.get("current_streak", 0),
        "conversation": list(intake.get("bot_conversation") or []),
    }

    # Save user message
    db.save_bot_message(user.id, today, "user", body.message)

    # Call Gemini
    result = await bot_respond(body.message, context)

    # If Gemini detected a food was logged, update intake
    food_logged = result.get("food_logged")
    nutrition   = None
    if food_logged:
        food_id = None
        matches = search_foods(food_logged["name"], limit=1)
        if matches:
            food_id = matches[0]["id"]

        if food_id:
            qty       = float(food_logged.get("quantity", 100))
            food_res  = score_food(food_id, qty, profile)
            nutrition = food_res.get("nutrition", {})
            if nutrition:
                db.add_extra_food_to_intake(user.id, today, {
                    "name":      food_res.get("food_name", food_logged["name"]),
                    "quantity":  qty,
                    "nutrition": nutrition,
                    "risk_score":food_res.get("risk_score"),
                })
                # Update streak since a food was logged
                streak_update = update_streak(user.id, profile)
                db.upsert_profile(user.id, streak_update)
                profile.update(streak_update)

    # Save assistant reply
    db.save_bot_message(user.id, today, "assistant", result["reply"])

    # Fetch updated intake
    updated_intake = db.get_or_create_daily_intake(user.id, today)

    return {
        "reply":         result["reply"],
        "intent":        result.get("intent", "question"),
        "food_logged":   {"name": food_logged["name"], "nutrition": nutrition}
                         if food_logged and nutrition else None,
        "daily_summary": {
            "calories_consumed": updated_intake.get("calories_consumed", 0),
            "carbs_consumed":    updated_intake.get("carbs_consumed", 0),
            "protein_consumed":  updated_intake.get("protein_consumed", 0),
            "sugar_consumed":    updated_intake.get("sugar_consumed", 0),
            "sodium_consumed":   updated_intake.get("sodium_consumed", 0),
        },
        "streak": profile.get("current_streak", 0),
    }


@router.get("/daily-summary")
def daily_summary(user=Depends(get_current_user)):
    today  = get_today_str()
    intake = db.get_or_create_daily_intake(user.id, today)
    plan   = db.get_active_diet_plan(user.id)

    # Get today's targets from plan
    from datetime import date
    today_name = date.today().strftime("%A")
    today_targets = {}
    if plan and plan.get("daily_targets"):
        today_targets = plan["daily_targets"].get(today_name, {})

    return {
        "date":          today,
        "intake":        intake,
        "targets":       today_targets,
        "plan_today":    plan.get("plan_data", {}).get(today_name, {}) if plan else {},
    }


@router.get("/conversation")
def get_conversation(user=Depends(get_current_user)):
    today = get_today_str()
    msgs  = db.get_bot_conversation(user.id, today)
    return {"messages": msgs, "date": today}