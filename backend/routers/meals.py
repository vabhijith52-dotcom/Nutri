# backend/routers/meals.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from models.schemas import MealAnalyzeRequest
from core.dependencies import get_current_user, get_optional_user
from services.meal_service import analyze_and_save_meal
from services.gemini_service import detect_food_from_image, parse_meal_description
from services import supabase_service as db

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("/analyze")
async def analyze(request: MealAnalyzeRequest, user=Depends(get_optional_user)):
    """
    Analyze a meal. Works without login (no save).
    With login: saves to DB, updates streak, updates daily intake.
    """
    # Build food_items list
    if request.food_items:
        food_items = [{"name": f.name, "quantity": f.quantity} for f in request.food_items]
    else:
        raise HTTPException(400, "Provide food_items list.")

    profile = {}
    if user:
        profile = db.get_profile(user.id) or {}

    if user:
        result = await analyze_and_save_meal(
            food_items  = food_items,
            user        = user,
            profile     = profile,
            description = request.description or "",
            image_url   = request.image_url,
        )
    else:
        # Unauthenticated — score only, no save
        from services.scoring_engine import score_meal
        from services.gemini_service  import explain_meal
        scoring = score_meal(food_items, profile)
        ai      = await explain_meal(scoring, profile)
        result  = {
            "meal": {
                "id": None, "description": request.description or "",
                "food_items": food_items,
                "nutrition_data": scoring["nutrition_data"],
                "per_item_nutrition": scoring["per_item_nutrition"],
                "image_url": request.image_url,
            },
            "analysis": {
                "id": None, "meal_id": None,
                "risk_score": scoring["risk_score"],
                "flags": scoring["flags"],
                "body_simulation": ai["body_simulation"],
                "ai_explanation": ai["ai_explanation"],
                "food_swaps": ai["food_swaps"],
            },
        }

    return result


@router.post("/detect-image")
async def detect_image(file: UploadFile = File(...)):
    """
    Upload meal photo → Gemini identifies food items.
    Returns editable list matching frontend FoodEntry interface.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (JPG, PNG).")
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large. Max 10MB.")

    result = await detect_food_from_image(image_bytes, file.content_type or "image/jpeg")
    return result


@router.get("/history")
def meal_history(user=Depends(get_current_user), limit: int = 20):
    return db.get_user_meals(user.id, limit)


@router.delete("/{meal_id}")
def delete_meal(meal_id: str, user=Depends(get_current_user)):
    db.delete_meal(meal_id, user.id)
    return {"deleted": meal_id}