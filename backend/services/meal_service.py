# backend/services/meal_service.py
"""
Orchestrates meal analysis:
1. Score with engine
2. Explain with Gemini
3. Save to Supabase
4. Update streak
"""
from services.scoring_engine import score_meal
from services.gemini_service  import explain_meal
from services                 import supabase_service as db
from services.intake_service  import update_streak, get_today_str


async def analyze_and_save_meal(
    food_items:  list,
    user:        object,
    profile:     dict,
    description: str   = "",
    image_url:   str   = None,
) -> dict:
    """
    Full pipeline: score → explain → save meal → save analysis → update streak.

    Returns the complete response matching frontend expectations.
    """
    # 1. Score with engine
    scoring_result = score_meal(food_items, profile)

    # 2. Save meal to DB
    meal_row = db.save_meal(user.id, {
        "description":        description,
        "food_items":         food_items,
        "nutrition_data":     scoring_result["nutrition_data"],
        "per_item_nutrition": scoring_result["per_item_nutrition"],
        "image_url":          image_url,
    })
    meal_id = meal_row.get("id")

    # 3. Get AI explanation
    ai_result = await explain_meal(scoring_result, profile)

    # 4. Save analysis to DB
    analysis_row = db.save_analysis(user.id, meal_id, {
        "risk_score":      scoring_result["risk_score"],
        "flags":           scoring_result["flags"],
        "body_simulation": ai_result["body_simulation"],
        "ai_explanation":  ai_result["ai_explanation"],
        "food_swaps":      ai_result["food_swaps"],
    })

    # 5. Update daily intake
    today = get_today_str()
    n = scoring_result["nutrition_data"]
    intake = db.get_or_create_daily_intake(user.id, today)
    db.update_daily_intake(user.id, today, {
        "calories_consumed": round(float(intake.get("calories_consumed") or 0) + float(n.get("calories", 0)), 1),
        "carbs_consumed":    round(float(intake.get("carbs_consumed") or 0)    + float(n.get("carbs", 0)),    1),
        "protein_consumed":  round(float(intake.get("protein_consumed") or 0)  + float(n.get("protein", 0)),  1),
        "fat_consumed":      round(float(intake.get("fat_consumed") or 0)      + float(n.get("fat", 0)),      1),
        "fiber_consumed":    round(float(intake.get("fiber_consumed") or 0)    + float(n.get("fiber", 0)),    1),
        "sodium_consumed":   round(float(intake.get("sodium_consumed") or 0)   + float(n.get("sodium", 0)),   1),
        "sugar_consumed":    round(float(intake.get("sugar_consumed") or 0)    + float(n.get("sugar", 0)),    1),
    })

    # 6. Update streak
    streak_update = update_streak(user.id, profile)
    db.upsert_profile(user.id, streak_update)

    # Return in format frontend expects
    return {
        "meal": {
            "id":                  meal_id,
            "description":         description,
            "food_items":          food_items,
            "nutrition_data":      scoring_result["nutrition_data"],
            "per_item_nutrition":  scoring_result["per_item_nutrition"],
            "image_url":           image_url,
        },
        "analysis": {
            "id":             analysis_row.get("id"),
            "meal_id":        meal_id,
            "risk_score":     scoring_result["risk_score"],
            "flags":          scoring_result["flags"],
            "body_simulation":ai_result["body_simulation"],
            "ai_explanation": ai_result["ai_explanation"],
            "food_swaps":     ai_result["food_swaps"],
        },
    }