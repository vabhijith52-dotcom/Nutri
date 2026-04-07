# backend/services/gemini_service.py
"""
All Gemini AI calls.
Never makes clinical decisions — only explains, detects, parses, plans.
"""
import json
import base64
import asyncio
import google.generativeai as genai
from core.config import settings

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


async def _call(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _model.generate_content, prompt)
    return resp.text.strip()


async def _call_with_image(prompt: str, image_bytes: bytes, mime: str) -> str:
    data = {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, lambda: _model.generate_content([data, prompt]))
    return resp.text.strip()


# ── 1. Detect foods from image ────────────────────────────────────────────────

async def detect_food_from_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """
    Identify food items in a meal photo with gram estimates.
    Returns editable list matching frontend FoodEntry interface.
    """
    food_ids = list(
        "white_rice,basmati_rice,brown_rice,whole_wheat_roti,maida_roti,idli,dosa,upma,"
        "poha,rolled_oats,moong_dal,rajma,chana,toor_dal,urad_dal,masoor_dal,spinach,"
        "boiled_potato,sweet_potato,cauliflower,brinjal,okra,tomato,carrot,banana,apple,"
        "mango,orange,guava,low_fat_curd,paneer,ghee,chicken_breast,whole_egg,egg_white,"
        "fish_rohu,tofu,samosa,pakoda,dhokla,roasted_chana,peanuts,masala_chai,lassi_sweet,"
        "coconut_water,dal_makhani,palak_paneer,chole,aloo_sabzi,kadhi,rajma_chawal,"
        "sambar,rasam,uttapam,pongal,medu_vada".split(",")
    )

    prompt = f"""You are a food recognition expert specialising in Indian cuisine.
Identify every food item in this meal photo and estimate grams consumed.

Use these exact IDs where the food matches: {', '.join(food_ids[:30])}...
Use plain English name if no exact match.

Return ONLY valid JSON:
{{
  "items": [
    {{"name": "food_id_or_plain_name", "quantity": 150}},
    ...
  ],
  "confidence": "high|medium|low",
  "notes": "brief observation"
}}
No markdown, no preamble."""

    raw = await _call_with_image(prompt, image_bytes, mime)
    try:
        result = json.loads(_clean_json(raw))
        return result
    except Exception:
        return {"items": [], "confidence": "low", "notes": "Could not identify foods."}


# ── 2. Extract health metrics from lab report ─────────────────────────────────

async def extract_lab_metrics(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """
    Parse a lab report image/PDF and extract health metrics.
    Returns structured dict with extracted values + suggested conditions.
    """
    prompt = """You are a clinical lab report parser.
Extract ALL health metrics visible in this lab report.

Return ONLY valid JSON:
{
  "extracted": {
    "hba1c": null,
    "fasting_sugar": null,
    "weight": null,
    "bmi": null,
    "systolic_bp": null,
    "diastolic_bp": null,
    "ldl": null,
    "hdl": null,
    "triglycerides": null,
    "total_cholesterol": null
  },
  "suggested_conditions": [],
  "suggested_severities": {},
  "notes": "any relevant observation"
}

Rules:
- Only include fields actually present in the report (leave others null)
- suggested_conditions: list from ["Diabetes","Hypertension","Obesity","Cholesterol"]
- suggested_severities: e.g. {"Diabetes": "controlled", "Hypertension": "stage1"}
- Use standard Indian lab units (glucose in mg/dL, BP in mmHg)
No markdown, no preamble."""

    raw = await _call_with_image(prompt, image_bytes, mime)
    try:
        return json.loads(_clean_json(raw))
    except Exception:
        return {
            "extracted": {},
            "suggested_conditions": [],
            "suggested_severities": {},
            "notes": "Could not parse lab report. Please enter values manually.",
        }


# ── 3. Parse meal description into food items ─────────────────────────────────

async def parse_meal_description(description: str) -> list:
    """Parse free-text meal description into [{name, quantity}] list."""
    prompt = f"""You are a clinical dietitian assistant for Indian patients.
Parse this meal description into individual food items with gram estimates.

Use these exact IDs where the food matches (PREFERRED):
white_rice, basmati_rice, whole_wheat_roti, idli, dosa, rolled_oats, moong_dal,
rajma, chana, toor_dal, spinach, boiled_potato, banana, apple, low_fat_curd,
paneer, whole_egg, chicken_breast, fish_rohu, samosa, roasted_chana, peanuts,
masala_chai, sambar, uttapam, dal_makhani, palak_paneer, chole, aloo_sabzi

Return ONLY valid JSON — list of objects with "name" and "quantity" (grams):
[{{"name": "whole_wheat_roti", "quantity": 80}}, {{"name": "moong_dal", "quantity": 150}}]

Meal: "{description}"
No preamble, no markdown."""

    raw = await _call(prompt)
    try:
        return json.loads(_clean_json(raw))
    except Exception:
        return []


# ── 4. Generate AI explanation for scored meal ────────────────────────────────

async def explain_meal(scoring_result: dict, user_profile: dict) -> dict:
    """
    Given scoring engine output, generate patient-friendly explanation.
    Returns: {ai_explanation, food_swaps, body_simulation}
    """
    conditions  = user_profile.get("conditions", [])
    severities  = user_profile.get("condition_severities", {})

    # Build condition context
    cond_context = []
    for c in conditions:
        sev = severities.get(c, "")
        cond_context.append(f"- {c}: {sev}" if sev else f"- {c}")

    prompt = f"""You are a clinical nutrition educator explaining a meal analysis to an Indian patient.

Patient conditions:
{chr(10).join(cond_context) if cond_context else "None specified"}

Meal risk score: {scoring_result.get('risk_score', 50)}/100 (lower = safer)
Nutrient totals: {json.dumps(scoring_result.get('nutrition_data', {}), indent=2)}

Top flags detected:
{json.dumps([f['label'] + ': ' + f['message'] for f in (scoring_result.get('flags', {}).get('flags', []))[:5]], indent=2)}

Write a structured report using markdown sections EXACTLY as shown:

## Nutritional Assessment

[2-3 sentences about what this meal provides and how it scored. Be specific about numbers.]

## Why These Foods Are Flagged

[For each high/medium flag, one line: emoji + **Label**: explanation]
[Use 🔴 for high severity, 🟡 for medium, 🟢 for low]
[Include → *Recommendation*: specific action on next line]

## Official Health Guidelines

[1-2 bullet points per condition citing ADA/WHO/AHA with actual numbers]

## Healthier Alternatives

[3-4 specific Indian food swaps with reasoning]

---
*NutriSense supports dietary awareness and lifestyle improvements. It does not provide medical advice or replace your doctor.*

Also return as valid JSON appended after the report (separated by |||):
{{
  "food_swaps": [
    {{"from": "original food", "to": "healthier alternative", "reason": "clinical reason"}},
    ...
  ],
  "body_simulation": {{
    "immediate": "what happens 0-30 mins after eating",
    "short_term": "what happens 1-2 hours after",
    "advice": "specific tip for managing any adverse effects"
  }}
}}"""

    raw = await _call(prompt)

    # Split explanation from JSON
    if "|||" in raw:
        explanation_part, json_part = raw.split("|||", 1)
    else:
        explanation_part = raw
        json_part = "{}"

    food_swaps = []
    body_simulation = {}
    try:
        extra = json.loads(_clean_json(json_part))
        food_swaps      = extra.get("food_swaps", [])
        body_simulation = extra.get("body_simulation", {})
    except Exception:
        pass

    return {
        "ai_explanation":  explanation_part.strip(),
        "food_swaps":      food_swaps,
        "body_simulation": body_simulation,
    }


# ── 5. Generate 7-day diet plan ─────────────────────────────
# ──────────────────

async def generate_diet_plan(profile: dict, meal_history: list,
                              food_preference: str, allergies: list) -> dict:
    """Generate a 7-day personalised Indian meal plan."""
    conditions = profile.get("conditions", [])
    severities = profile.get("condition_severities", {})
    target_cal = int(profile.get("doctor_calorie_target") or 1800)
    age        = profile.get("age", 35)

    cond_context = [f"- {c}: {severities.get(c, 'standard')}" for c in conditions]

    history_summary = "\n".join(
        f"- {m.get('description', 'meal')} (risk: {m.get('composite_score', 'N/A')})"
        for m in meal_history[:8]
    ) or "No history available"

    allergy_note = f"STRICT: Avoid these completely: {', '.join(allergies)}" if allergies else "No allergies"
    pref_note    = "Vegetarian (no meat/fish/egg)" if food_preference == "veg" else \
                   "Eggetarian (eggs OK, no meat/fish)" if food_preference == "eggetarian" else \
                   "Non-vegetarian (all foods OK)"

    prompt = f"""You are a clinical dietitian specialising in Indian metabolic health.
Create a 7-day personalised meal plan for this patient.

Patient:
- Conditions: {chr(10).join(cond_context) if cond_context else "None"}
- Age: {age}
- Food preference: {pref_note}
- {allergy_note}
- Daily calorie target: {target_cal} kcal

Recent meals (for variety — do not repeat these too often):
{history_summary}

Rules:
- Use authentic Indian foods
- Each meal must clinically match the conditions (low GI for diabetes, low sodium for hypertension, etc.)
- Breakfast ~{target_cal//5} kcal, Lunch ~{target_cal//3} kcal, Dinner ~{target_cal//4} kcal

Return ONLY valid JSON:
{{
  "Monday":    {{"breakfast": {{"meal": "...", "calories": 300, "rationale": "..."}}, "lunch": {{...}}, "dinner": {{...}} }},
  "Tuesday":   {{...}},
  "Wednesday": {{...}},
  "Thursday":  {{...}},
  "Friday":    {{...}},
  "Saturday":  {{...}},
  "Sunday":    {{...}}
}}
No preamble, no markdown."""

    raw = await _call(prompt)
    try:
        return json.loads(_clean_json(raw))
    except Exception:
        return {}


# ── 6. Bot response ───────────────────────────────────────────────────────────

async def bot_respond(user_message: str, context: dict) -> dict:
    """
    Main bot intelligence. Receives full daily context and responds.
    Returns: {reply, intent, food_logged, action}
    """
    profile       = context.get("profile", {})
    today_intake  = context.get("today_intake", {})
    diet_plan     = context.get("diet_plan", {})
    streak        = context.get("streak", 0)
    conversation  = context.get("conversation", [])
    conditions    = profile.get("conditions", [])
    severities    = profile.get("condition_severities", {})

    # Build diet plan summary for today
    from datetime import date
    today_name = date.today().strftime("%A")
    today_plan = {}
    if diet_plan and "plan_data" in diet_plan:
        today_plan = diet_plan["plan_data"].get(today_name, {})

    intake_summary = f"""
Today's intake so far:
- Calories: {today_intake.get('calories_consumed', 0):.0f} kcal
- Carbs:    {today_intake.get('carbs_consumed', 0):.1f}g
- Protein:  {today_intake.get('protein_consumed', 0):.1f}g
- Fat:      {today_intake.get('fat_consumed', 0):.1f}g
- Fiber:    {today_intake.get('fiber_consumed', 0):.1f}g
- Sodium:   {today_intake.get('sodium_consumed', 0):.0f}mg
- Sugar:    {today_intake.get('sugar_consumed', 0):.1f}g

Today's meal plan:
- Breakfast ({today_intake.get('breakfast_status','pending')}): {today_plan.get('breakfast', {}).get('meal','Not set')}
- Lunch ({today_intake.get('lunch_status','pending')}): {today_plan.get('lunch', {}).get('meal','Not set')}
- Dinner ({today_intake.get('dinner_status','pending')}): {today_plan.get('dinner', {}).get('meal','Not set')}

Extra foods logged today: {json.dumps(today_intake.get('extra_foods', []))}
Current streak: {streak} days
"""

    conversation_ctx = "\n".join(
        f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
        for m in conversation[-8:]
    )

    prompt = f"""You are NutriSense AI Coach — a clinical diet assistant for Indian patients.

Patient profile:
- Conditions: {conditions} with severities {severities}

{intake_summary}

Recent conversation:
{conversation_ctx if conversation_ctx else "No previous messages"}

User message: "{user_message}"

Respond as a helpful, clinical diet coach. You can:
1. Log extra food the user ate (detect food names in message)
2. Handle missed/skipped meals  
3. Answer "can I eat X?" with practical advice based on today's budget
4. Provide weekly summary if asked
5. Answer nutrition questions
6. Motivate and build habits
7. Give real-time corrective advice (e.g., "keep dinner light since you had ice cream")

Your response must be a plain text message to the user (warm, clear, under 150 words).
After the message, on a new line, add: |||INTENT:food_log|plan_check|permission_query|summary|question|habit

If user logged food, also add on another new line:
|||FOOD:food_name=grams

Example:
Great choice! [advice here]
|||INTENT:food_log
|||FOOD:apple=150"""

    raw = await _call(prompt)

    # Parse response
    reply  = raw
    intent = "question"
    food   = None

    lines = raw.split("\n")
    clean_lines = []
    for line in lines:
        if line.startswith("|||INTENT:"):
            intent = line.replace("|||INTENT:", "").strip()
        elif line.startswith("|||FOOD:"):
            food_str = line.replace("|||FOOD:", "").strip()
            if "=" in food_str:
                name, qty = food_str.split("=", 1)
                food = {"name": name.strip(), "quantity": float(qty.strip())}
        else:
            clean_lines.append(line)

    reply = "\n".join(clean_lines).strip()

    return {
        "reply":       reply,
        "intent":      intent,
        "food_logged": food,
    }