# backend/services/metrics_service.py
"""
Auto-detect health conditions and severities from metric values.
All thresholds from ADA 2023, AHA 2021, ICMR-NIN 2020.
"""
from typing import Dict, Tuple, List


def detect_conditions(metrics: dict) -> Tuple[List[str], Dict[str, str]]:
    """
    Given a dict of metric_type→value, auto-detect conditions and severities.
    Returns (conditions_list, severities_dict).
    """
    conditions = []
    severities = {}

    hba1c         = metrics.get("hba1c")
    fasting_sugar = metrics.get("fasting_sugar")
    systolic      = metrics.get("systolic_bp")
    diastolic     = metrics.get("diastolic_bp")
    bmi           = metrics.get("bmi")
    weight        = metrics.get("weight")
    ldl           = metrics.get("ldl")
    total_chol    = metrics.get("total_cholesterol")
    triglycerides = metrics.get("triglycerides")

    # ── Diabetes detection (ADA 2023) ─────────────────────────────────────────
    if hba1c is not None or fasting_sugar is not None:
        is_diabetic = (
            (hba1c is not None and hba1c >= 6.5) or
            (fasting_sugar is not None and fasting_sugar >= 126)
        )
        is_prediabetic = (
            (hba1c is not None and 5.7 <= hba1c < 6.5) or
            (fasting_sugar is not None and 100 <= fasting_sugar < 126)
        )

        if is_diabetic:
            conditions.append("Diabetes")
            if (hba1c and hba1c >= 8.0) or (fasting_sugar and fasting_sugar >= 180):
                severities["Diabetes"] = "uncontrolled"
            else:
                severities["Diabetes"] = "controlled"
        elif is_prediabetic:
            conditions.append("Diabetes")
            severities["Diabetes"] = "prediabetes"

    # ── Hypertension detection (AHA 2021) ─────────────────────────────────────
    if systolic is not None or diastolic is not None:
        s = systolic or 0
        d = diastolic or 0

        if s >= 140 or d >= 90:
            conditions.append("Hypertension")
            severities["Hypertension"] = "stage2"
        elif s >= 130 or d >= 80:
            conditions.append("Hypertension")
            severities["Hypertension"] = "stage1"
        elif s >= 120:
            conditions.append("Hypertension")
            severities["Hypertension"] = "elevated"

    # ── Obesity detection (ICMR-NIN 2020 Asian cut-offs) ─────────────────────
    if bmi is not None:
        if bmi >= 32.5:
            conditions.append("Obesity")
            severities["Obesity"] = "class2"
        elif bmi >= 27.5:
            conditions.append("Obesity")
            severities["Obesity"] = "class1"
        elif bmi >= 23.0:
            conditions.append("Obesity")
            severities["Obesity"] = "overweight"

    # ── Cholesterol detection (AHA/ACC 2019) ──────────────────────────────────
    high_chol = (
        (ldl is not None and ldl >= 130) or
        (total_chol is not None and total_chol >= 200) or
        (triglycerides is not None and triglycerides >= 150)
    )
    very_high = (
        (ldl is not None and ldl >= 160) or
        (triglycerides is not None and triglycerides >= 200)
    )

    if high_chol:
        conditions.append("Cholesterol")
        severities["Cholesterol"] = "high" if very_high else "borderline"

    return conditions, severities


def metrics_to_profile_fields(metrics_list: list) -> dict:
    """Convert a list of MetricEntry dicts into profile fields for upsert."""
    field_map = {
        "hba1c":         "hba1c",
        "fasting_sugar": "fasting_sugar",
        "weight":        "weight",
        "bmi":           "bmi",
        "systolic_bp":   "systolic_bp",
        "diastolic_bp":  "diastolic_bp",
        "ldl":           "ldl",
        "hdl":           "hdl",
        "triglycerides": "triglycerides",
    }
    result = {}
    for m in metrics_list:
        field = field_map.get(m["metric_type"])
        if field:
            result[field] = m["value"]
    return result