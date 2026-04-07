# backend/models/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    full_name: Optional[str]         = None
    age: Optional[int]               = None
    gender: Optional[str]            = None
    conditions: Optional[List[str]]  = None
    condition_severities: Optional[Dict[str, str]] = None
    # Diabetes
    hba1c: Optional[float]           = None
    fasting_sugar: Optional[float]   = None
    # Obesity
    weight: Optional[float]          = None
    bmi: Optional[float]             = None
    # Hypertension
    systolic_bp: Optional[int]       = None
    diastolic_bp: Optional[int]      = None
    # Cholesterol
    ldl: Optional[float]             = None
    hdl: Optional[float]             = None
    triglycerides: Optional[float]   = None
    # Diet preferences
    food_preference: Optional[str]   = None
    allergies: Optional[List[str]]   = None
    # Doctor overrides
    doctor_gi_limit: Optional[int]         = None
    doctor_sodium_limit_mg: Optional[int]  = None
    doctor_calorie_target: Optional[int]   = None
    # App state
    onboarding_complete: Optional[bool]    = None


# ── Health Metrics ────────────────────────────────────────────────────────────

class MetricEntry(BaseModel):
    metric_type: str   # e.g. "hba1c", "fasting_sugar", "systolic_bp"
    value: float
    unit: Optional[str] = None
    source: str = "manual"


class ManualMetricsRequest(BaseModel):
    metrics: List[MetricEntry]


class LabExtractRequest(BaseModel):
    """Frontend sends base64-encoded lab report image or PDF."""
    file_base64: str
    mime_type: str = "image/jpeg"


class ConditionConfirmRequest(BaseModel):
    """User confirms auto-detected conditions after lab extraction."""
    confirmed_conditions: List[str]
    confirmed_severities: Dict[str, str] = {}
    metrics: List[MetricEntry] = []


# ── Meals ─────────────────────────────────────────────────────────────────────

class FoodItemInput(BaseModel):
    name: str
    quantity: float = 100.0  # grams — matches frontend field name


class MealAnalyzeRequest(BaseModel):
    food_items: List[FoodItemInput]
    description: Optional[str] = None
    image_url: Optional[str]   = None


# ── Diet Plan ─────────────────────────────────────────────────────────────────

class DietPlanRequest(BaseModel):
    food_preference: str              # "veg" | "nonveg" | "eggetarian"
    allergies: List[str] = []


# ── Bot ───────────────────────────────────────────────────────────────────────

class BotMessage(BaseModel):
    message: str


# ── Check-in ─────────────────────────────────────────────────────────────────

class CheckinRequest(BaseModel):
    energy_level: int   # 1-5
    cravings_level: int # 1-5
    notes: Optional[str] = None