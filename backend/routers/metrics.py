# backend/routers/metrics.py
import base64
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from models.schemas import ManualMetricsRequest, ConditionConfirmRequest
from core.dependencies import get_current_user
from services import supabase_service as db
from services.gemini_service import extract_lab_metrics
from services.metrics_service import detect_conditions, metrics_to_profile_fields

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/manual")
def save_manual_metrics(body: ManualMetricsRequest, user=Depends(get_current_user)):
    """Save manually entered metrics and return auto-detected conditions for confirmation."""
    metrics_list = [m.model_dump() for m in body.metrics]

    # Save time-series readings
    db.save_metrics(user.id, metrics_list)

    # Update profile fields
    profile_fields = metrics_to_profile_fields(metrics_list)
    if profile_fields:
        db.upsert_profile(user.id, profile_fields)

    # Auto-detect conditions (for frontend confirmation screen)
    flat_metrics = {m["metric_type"]: m["value"] for m in metrics_list}
    detected_conditions, detected_severities = detect_conditions(flat_metrics)

    return {
        "saved":                 len(metrics_list),
        "detected_conditions":   detected_conditions,
        "detected_severities":   detected_severities,
        "message":               "Metrics saved. Please confirm the detected conditions.",
    }


@router.post("/extract-lab")
async def extract_from_lab(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Upload lab report image/PDF → Gemini extracts metrics → return for confirmation."""
    if file.content_type not in ["image/jpeg","image/png","image/jpg","application/pdf"]:
        raise HTTPException(400, "Upload must be JPG, PNG, or PDF.")

    image_bytes = await file.read()
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(413, "File too large. Max 15MB.")

    mime = file.content_type if file.content_type.startswith("image") else "image/jpeg"
    result = await extract_lab_metrics(image_bytes, mime)

    extracted = result.get("extracted", {})
    flat_metrics = {k: v for k, v in extracted.items() if v is not None}
    auto_conditions, auto_severities = detect_conditions(flat_metrics)

    return {
        "extracted":             extracted,
        "detected_conditions":   result.get("suggested_conditions") or auto_conditions,
        "detected_severities":   result.get("suggested_severities") or auto_severities,
        "notes":                 result.get("notes", ""),
        "message":               "Lab report analyzed. Please review and confirm.",
    }


@router.post("/confirm-extracted")
def confirm_metrics(body: ConditionConfirmRequest, user=Depends(get_current_user)):
    """User confirms auto-detected conditions. Updates profile and saves metrics."""
    # Save time-series metrics
    if body.metrics:
        db.save_metrics(user.id, [m.model_dump() for m in body.metrics])

    # Update profile with confirmed conditions
    profile_fields = {}
    if body.metrics:
        profile_fields.update(metrics_to_profile_fields([m.model_dump() for m in body.metrics]))
    profile_fields["conditions"]            = body.confirmed_conditions
    profile_fields["condition_severities"]  = body.confirmed_severities

    db.upsert_profile(user.id, profile_fields)

    return {
        "message":    "Conditions confirmed and profile updated.",
        "conditions": body.confirmed_conditions,
        "severities": body.confirmed_severities,
    }


@router.get("/history")
def metrics_history(user=Depends(get_current_user), metric_type: str = None):
    return db.get_metrics_history(user.id, metric_type)


@router.get("/latest")
def latest_metrics(user=Depends(get_current_user)):
    return db.get_latest_metrics(user.id)