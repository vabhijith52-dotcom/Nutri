# backend/services/scoring_engine.py
"""
NutriSense Scoring Engine
All nutrient data: IFCT 2017 (NIN Hyderabad)
GI values: Sydney GI Database (Atkinson 2008, Diabetes Care 31(12))
Thresholds: peer-reviewed literature cited inline

Returns risk_score 0-100 where:
  0-35  = Low Risk   (Safe)
  36-65 = Moderate Risk
  66+   = High Risk  (Avoid)

Plus FlagResult list matching the frontend FlagResult interface:
  {label, severity, message, category, moderation}
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from copy import deepcopy
import difflib


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — ~95 INDIAN FOODS DATABASE
# All values per 100g. Scale to actual quantity consumed.
# gi = None  → not tested, uncertain (gets 0.5 credit)
# gi = -1    → not applicable — no carbs (gets full credit)
# ─────────────────────────────────────────────────────────────────────────────

RAW_FOODS: Dict[str, dict] = {

    # ── Grains & Staples (14) ────────────────────────────────────────────────
    "white_rice": {
        "name":"White Rice (cooked)","serving_g":150,
        "calories":194,"carbs_g":43.0,"sugar_g":0.1,"fiber_g":0.6,"protein_g":4.0,
        "fat_g":0.4,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":1,
        "potassium_mg":55,"magnesium_mg":12,"calcium_mg":10,"cholesterol_mg":0,"gi":73
    },
    "basmati_rice": {
        "name":"Basmati Rice (cooked)","serving_g":150,
        "calories":180,"carbs_g":39.0,"sugar_g":0.1,"fiber_g":0.6,"protein_g":4.0,
        "fat_g":0.3,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":1,
        "potassium_mg":59,"magnesium_mg":13,"calcium_mg":10,"cholesterol_mg":0,"gi":55
    },
    "brown_rice": {
        "name":"Brown Rice (cooked)","serving_g":150,
        "calories":178,"carbs_g":37.0,"sugar_g":0.6,"fiber_g":2.2,"protein_g":4.0,
        "fat_g":1.3,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":4,
        "potassium_mg":150,"magnesium_mg":44,"calcium_mg":10,"cholesterol_mg":0,"gi":50
    },
    "whole_wheat_roti": {
        "name":"Whole Wheat Roti","serving_g":40,
        "calories":110,"carbs_g":22.0,"sugar_g":0.5,"fiber_g":2.8,"protein_g":3.5,
        "fat_g":1.5,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":120,
        "potassium_mg":80,"magnesium_mg":25,"calcium_mg":20,"cholesterol_mg":0,"gi":62
    },
    "maida_roti": {
        "name":"Maida Roti (white flour)","serving_g":40,
        "calories":120,"carbs_g":24.0,"sugar_g":0.8,"fiber_g":0.8,"protein_g":3.2,
        "fat_g":1.8,"sat_fat_g":0.4,"trans_fat_g":0.0,"sodium_mg":130,
        "potassium_mg":40,"magnesium_mg":10,"calcium_mg":12,"cholesterol_mg":0,"gi":70
    },
    "idli": {
        "name":"Idli","serving_g":100,
        "calories":140,"carbs_g":30.0,"sugar_g":0.5,"fiber_g":1.2,"protein_g":4.5,
        "fat_g":0.3,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":250,
        "potassium_mg":75,"magnesium_mg":15,"calcium_mg":22,"cholesterol_mg":0,"gi":77
    },
    "dosa": {
        "name":"Plain Dosa","serving_g":100,
        "calories":168,"carbs_g":28.0,"sugar_g":0.3,"fiber_g":1.0,"protein_g":4.5,
        "fat_g":5.0,"sat_fat_g":0.7,"trans_fat_g":0.0,"sodium_mg":350,
        "potassium_mg":70,"magnesium_mg":18,"calcium_mg":15,"cholesterol_mg":0,"gi":77
    },
    "upma": {
        "name":"Upma","serving_g":150,
        "calories":180,"carbs_g":28.0,"sugar_g":1.5,"fiber_g":2.0,"protein_g":4.5,
        "fat_g":6.0,"sat_fat_g":1.0,"trans_fat_g":0.0,"sodium_mg":320,
        "potassium_mg":120,"magnesium_mg":20,"calcium_mg":18,"cholesterol_mg":0,"gi":65
    },
    "poha": {
        "name":"Poha (beaten rice)","serving_g":150,
        "calories":220,"carbs_g":40.0,"sugar_g":2.0,"fiber_g":1.5,"protein_g":4.0,
        "fat_g":5.0,"sat_fat_g":0.8,"trans_fat_g":0.0,"sodium_mg":300,
        "potassium_mg":100,"magnesium_mg":18,"calcium_mg":15,"cholesterol_mg":0,"gi":72
    },
    "rolled_oats": {
        "name":"Rolled Oats (cooked)","serving_g":150,
        "calories":150,"carbs_g":27.0,"sugar_g":0.5,"fiber_g":4.0,"protein_g":5.0,
        "fat_g":3.0,"sat_fat_g":0.5,"trans_fat_g":0.0,"sodium_mg":5,
        "potassium_mg":160,"magnesium_mg":40,"calcium_mg":20,"cholesterol_mg":0,"gi":55
    },
    "white_bread": {
        "name":"White Bread (2 slices)","serving_g":60,
        "calories":159,"carbs_g":29.4,"sugar_g":3.0,"fiber_g":1.6,"protein_g":5.4,
        "fat_g":1.9,"sat_fat_g":0.4,"trans_fat_g":0.0,"sodium_mg":295,
        "potassium_mg":72,"magnesium_mg":14,"calcium_mg":52,"cholesterol_mg":0,"gi":75
    },
    "paratha_plain": {
        "name":"Plain Paratha","serving_g":80,
        "calories":270,"carbs_g":36.0,"sugar_g":0.8,"fiber_g":2.5,"protein_g":6.0,
        "fat_g":11.0,"sat_fat_g":2.5,"trans_fat_g":0.1,"sodium_mg":240,
        "potassium_mg":110,"magnesium_mg":30,"calcium_mg":25,"cholesterol_mg":5,"gi":62
    },
    "jowar_roti": {
        "name":"Jowar Roti (sorghum)","serving_g":50,
        "calories":130,"carbs_g":26.0,"sugar_g":0.3,"fiber_g":4.5,"protein_g":4.2,
        "fat_g":1.2,"sat_fat_g":0.2,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":180,"magnesium_mg":55,"calcium_mg":30,"cholesterol_mg":0,"gi":55
    },
    "bajra_roti": {
        "name":"Bajra Roti (pearl millet)","serving_g":50,
        "calories":118,"carbs_g":21.0,"sugar_g":0.3,"fiber_g":4.0,"protein_g":4.0,
        "fat_g":1.5,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":3,
        "potassium_mg":195,"magnesium_mg":60,"calcium_mg":28,"cholesterol_mg":0,"gi":54
    },

    # ── Dals & Legumes (10) ──────────────────────────────────────────────────
    "moong_dal": {
        "name":"Moong Dal (cooked)","serving_g":150,
        "calories":147,"carbs_g":25.0,"sugar_g":1.8,"fiber_g":7.6,"protein_g":10.0,
        "fat_g":0.7,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":14,
        "potassium_mg":370,"magnesium_mg":48,"calcium_mg":35,"cholesterol_mg":0,"gi":38
    },
    "rajma": {
        "name":"Rajma (Kidney Beans, cooked)","serving_g":150,
        "calories":165,"carbs_g":30.0,"sugar_g":0.4,"fiber_g":9.8,"protein_g":10.5,
        "fat_g":0.7,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":10,
        "potassium_mg":505,"magnesium_mg":60,"calcium_mg":50,"cholesterol_mg":0,"gi":29
    },
    "chana": {
        "name":"Chana / Chickpeas (cooked)","serving_g":150,
        "calories":180,"carbs_g":30.0,"sugar_g":5.0,"fiber_g":8.0,"protein_g":10.5,
        "fat_g":3.0,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":11,
        "potassium_mg":430,"magnesium_mg":50,"calcium_mg":60,"cholesterol_mg":0,"gi":33
    },
    "toor_dal": {
        "name":"Toor Dal / Arhar Dal (cooked)","serving_g":150,
        "calories":155,"carbs_g":28.0,"sugar_g":1.5,"fiber_g":6.5,"protein_g":9.5,
        "fat_g":0.8,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":12,
        "potassium_mg":400,"magnesium_mg":45,"calcium_mg":40,"cholesterol_mg":0,"gi":42
    },
    "urad_dal": {
        "name":"Urad Dal (cooked)","serving_g":150,
        "calories":165,"carbs_g":29.0,"sugar_g":1.0,"fiber_g":7.0,"protein_g":11.0,
        "fat_g":0.7,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":8,
        "potassium_mg":360,"magnesium_mg":55,"calcium_mg":45,"cholesterol_mg":0,"gi":43
    },
    "masoor_dal": {
        "name":"Masoor Dal / Red Lentils (cooked)","serving_g":150,
        "calories":145,"carbs_g":25.0,"sugar_g":2.0,"fiber_g":8.0,"protein_g":9.0,
        "fat_g":0.5,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":9,
        "potassium_mg":350,"magnesium_mg":40,"calcium_mg":35,"cholesterol_mg":0,"gi":31
    },
    "chana_dal": {
        "name":"Chana Dal (Bengal Gram, cooked)","serving_g":150,
        "calories":185,"carbs_g":30.5,"sugar_g":4.8,"fiber_g":8.5,"protein_g":10.0,
        "fat_g":2.5,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":10,
        "potassium_mg":420,"magnesium_mg":48,"calcium_mg":55,"cholesterol_mg":0,"gi":27
    },
    "green_peas": {
        "name":"Green Peas (cooked)","serving_g":100,
        "calories":84,"carbs_g":15.6,"sugar_g":5.7,"fiber_g":5.5,"protein_g":5.4,
        "fat_g":0.4,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":3,
        "potassium_mg":244,"magnesium_mg":33,"calcium_mg":25,"cholesterol_mg":0,"gi":51
    },
    "soya_chunks": {
        "name":"Soya Chunks (cooked)","serving_g":100,
        "calories":145,"carbs_g":10.0,"sugar_g":3.0,"fiber_g":4.0,"protein_g":18.0,
        "fat_g":3.5,"sat_fat_g":0.5,"trans_fat_g":0.0,"sodium_mg":20,
        "potassium_mg":300,"magnesium_mg":60,"calcium_mg":80,"cholesterol_mg":0,"gi":18
    },
    "sprouted_moong": {
        "name":"Sprouted Moong","serving_g":100,
        "calories":45,"carbs_g":8.0,"sugar_g":1.5,"fiber_g":3.0,"protein_g":4.5,
        "fat_g":0.3,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":5,
        "potassium_mg":280,"magnesium_mg":28,"calcium_mg":22,"cholesterol_mg":0,"gi":25
    },

    # ── Vegetables (14) ──────────────────────────────────────────────────────
    "spinach": {
        "name":"Spinach (cooked)","serving_g":100,
        "calories":29,"carbs_g":4.0,"sugar_g":0.5,"fiber_g":2.5,"protein_g":3.0,
        "fat_g":0.4,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":80,
        "potassium_mg":540,"magnesium_mg":80,"calcium_mg":100,"cholesterol_mg":0,"gi":15
    },
    "boiled_potato": {
        "name":"Boiled Potato","serving_g":150,
        "calories":130,"carbs_g":30.0,"sugar_g":1.5,"fiber_g":2.2,"protein_g":3.0,
        "fat_g":0.1,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":8,
        "potassium_mg":540,"magnesium_mg":30,"calcium_mg":12,"cholesterol_mg":0,"gi":82
    },
    "sweet_potato": {
        "name":"Sweet Potato (baked)","serving_g":130,
        "calories":112,"carbs_g":26.0,"sugar_g":5.4,"fiber_g":3.8,"protein_g":2.1,
        "fat_g":0.1,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":7,
        "potassium_mg":440,"magnesium_mg":30,"calcium_mg":38,"cholesterol_mg":0,"gi":63
    },
    "cauliflower": {
        "name":"Cauliflower (cooked)","serving_g":100,
        "calories":25,"carbs_g":5.0,"sugar_g":2.4,"fiber_g":2.0,"protein_g":1.9,
        "fat_g":0.3,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":30,
        "potassium_mg":175,"magnesium_mg":15,"calcium_mg":22,"cholesterol_mg":0,"gi":15
    },
    "brinjal": {
        "name":"Brinjal / Eggplant (cooked)","serving_g":100,
        "calories":33,"carbs_g":7.0,"sugar_g":3.5,"fiber_g":3.0,"protein_g":1.0,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":230,"magnesium_mg":14,"calcium_mg":9,"cholesterol_mg":0,"gi":15
    },
    "okra": {
        "name":"Okra / Bhindi (cooked)","serving_g":100,
        "calories":35,"carbs_g":7.0,"sugar_g":1.5,"fiber_g":3.2,"protein_g":2.0,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":8,
        "potassium_mg":300,"magnesium_mg":55,"calcium_mg":82,"cholesterol_mg":0,"gi":20
    },
    "tomato": {
        "name":"Tomato (raw)","serving_g":100,
        "calories":18,"carbs_g":3.9,"sugar_g":2.6,"fiber_g":1.2,"protein_g":0.9,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":5,
        "potassium_mg":237,"magnesium_mg":11,"calcium_mg":10,"cholesterol_mg":0,"gi":15
    },
    "carrot": {
        "name":"Carrot (raw)","serving_g":100,
        "calories":41,"carbs_g":9.6,"sugar_g":4.7,"fiber_g":2.8,"protein_g":0.9,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":69,
        "potassium_mg":320,"magnesium_mg":12,"calcium_mg":33,"cholesterol_mg":0,"gi":47
    },
    "bottle_gourd": {
        "name":"Bottle Gourd / Lauki (cooked)","serving_g":150,
        "calories":25,"carbs_g":5.0,"sugar_g":2.0,"fiber_g":2.0,"protein_g":1.2,
        "fat_g":0.1,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":190,"magnesium_mg":18,"calcium_mg":20,"cholesterol_mg":0,"gi":15
    },
    "bitter_gourd": {
        "name":"Bitter Gourd / Karela (cooked)","serving_g":100,
        "calories":17,"carbs_g":3.7,"sugar_g":1.7,"fiber_g":2.8,"protein_g":1.0,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":5,
        "potassium_mg":296,"magnesium_mg":17,"calcium_mg":19,"cholesterol_mg":0,"gi":14
    },
    "corn": {
        "name":"Sweet Corn (cooked)","serving_g":100,
        "calories":96,"carbs_g":21.0,"sugar_g":4.5,"fiber_g":2.4,"protein_g":3.4,
        "fat_g":1.5,"sat_fat_g":0.2,"trans_fat_g":0.0,"sodium_mg":15,
        "potassium_mg":270,"magnesium_mg":37,"calcium_mg":2,"cholesterol_mg":0,"gi":52
    },
    "onion": {
        "name":"Onion (raw)","serving_g":80,
        "calories":32,"carbs_g":7.4,"sugar_g":3.4,"fiber_g":1.4,"protein_g":0.9,
        "fat_g":0.1,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":3,
        "potassium_mg":144,"magnesium_mg":10,"calcium_mg":18,"cholesterol_mg":0,"gi":10
    },
    "capsicum": {
        "name":"Green Capsicum (raw)","serving_g":100,
        "calories":20,"carbs_g":4.6,"sugar_g":2.4,"fiber_g":1.7,"protein_g":0.9,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":3,
        "potassium_mg":175,"magnesium_mg":10,"calcium_mg":7,"cholesterol_mg":0,"gi":15
    },
    "drumstick": {
        "name":"Drumstick / Moringa (cooked)","serving_g":100,
        "calories":37,"carbs_g":8.5,"sugar_g":2.0,"fiber_g":3.2,"protein_g":2.1,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":42,
        "potassium_mg":335,"magnesium_mg":45,"calcium_mg":185,"cholesterol_mg":0,"gi":20
    },

    # ── Fruits (10) ──────────────────────────────────────────────────────────
    "banana": {
        "name":"Banana","serving_g":120,
        "calories":107,"carbs_g":27.2,"sugar_g":14.4,"fiber_g":3.1,"protein_g":1.3,
        "fat_g":0.4,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":1,
        "potassium_mg":422,"magnesium_mg":32,"calcium_mg":6,"cholesterol_mg":0,"gi":62
    },
    "apple": {
        "name":"Apple","serving_g":150,
        "calories":78,"carbs_g":20.8,"sugar_g":15.6,"fiber_g":3.6,"protein_g":0.4,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":1,
        "potassium_mg":148,"magnesium_mg":9,"calcium_mg":8,"cholesterol_mg":0,"gi":38
    },
    "mango": {
        "name":"Mango","serving_g":150,
        "calories":99,"carbs_g":25.0,"sugar_g":22.5,"fiber_g":2.6,"protein_g":1.4,
        "fat_g":0.4,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":168,"magnesium_mg":12,"calcium_mg":11,"cholesterol_mg":0,"gi":60
    },
    "orange": {
        "name":"Orange","serving_g":130,
        "calories":61,"carbs_g":15.3,"sugar_g":12.2,"fiber_g":3.1,"protein_g":1.2,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":0,
        "potassium_mg":181,"magnesium_mg":13,"calcium_mg":52,"cholesterol_mg":0,"gi":43
    },
    "guava": {
        "name":"Guava","serving_g":120,
        "calories":68,"carbs_g":14.3,"sugar_g":8.9,"fiber_g":5.4,"protein_g":2.6,
        "fat_g":1.0,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":284,"magnesium_mg":22,"calcium_mg":18,"cholesterol_mg":0,"gi":12
    },
    "papaya": {
        "name":"Papaya","serving_g":150,
        "calories":59,"carbs_g":15.1,"sugar_g":11.3,"fiber_g":2.5,"protein_g":0.8,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":8,
        "potassium_mg":264,"magnesium_mg":21,"calcium_mg":34,"cholesterol_mg":0,"gi":60
    },
    "watermelon": {
        "name":"Watermelon","serving_g":200,
        "calories":60,"carbs_g":15.2,"sugar_g":12.4,"fiber_g":0.8,"protein_g":1.2,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":170,"magnesium_mg":18,"calcium_mg":10,"cholesterol_mg":0,"gi":72
    },
    "grapes": {
        "name":"Grapes","serving_g":120,
        "calories":82,"carbs_g":21.5,"sugar_g":18.1,"fiber_g":1.1,"protein_g":0.9,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":191,"magnesium_mg":7,"calcium_mg":10,"cholesterol_mg":0,"gi":53
    },
    "pear": {
        "name":"Pear","serving_g":150,
        "calories":86,"carbs_g":23.2,"sugar_g":15.6,"fiber_g":4.6,"protein_g":0.5,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":1,
        "potassium_mg":116,"magnesium_mg":8,"calcium_mg":9,"cholesterol_mg":0,"gi":38
    },
    "pomegranate": {
        "name":"Pomegranate","serving_g":100,
        "calories":83,"carbs_g":18.7,"sugar_g":13.7,"fiber_g":4.0,"protein_g":1.7,
        "fat_g":1.2,"sat_fat_g":0.1,"trans_fat_g":0.0,"sodium_mg":3,
        "potassium_mg":236,"magnesium_mg":12,"calcium_mg":10,"cholesterol_mg":0,"gi":35
    },

    # ── Dairy (8) ────────────────────────────────────────────────────────────
    "whole_milk": {
        "name":"Whole Milk","serving_g":200,
        "calories":122,"carbs_g":9.6,"sugar_g":10.2,"fiber_g":0.0,"protein_g":6.4,
        "fat_g":6.6,"sat_fat_g":4.2,"trans_fat_g":0.1,"sodium_mg":86,
        "potassium_mg":320,"magnesium_mg":22,"calcium_mg":240,"cholesterol_mg":24,"gi":31
    },
    "low_fat_milk": {
        "name":"Low-Fat Milk","serving_g":200,
        "calories":84,"carbs_g":9.8,"sugar_g":10.2,"fiber_g":0.0,"protein_g":6.6,
        "fat_g":1.8,"sat_fat_g":1.1,"trans_fat_g":0.0,"sodium_mg":88,
        "potassium_mg":330,"magnesium_mg":22,"calcium_mg":248,"cholesterol_mg":8,"gi":32
    },
    "low_fat_curd": {
        "name":"Low-Fat Curd (Dahi)","serving_g":150,
        "calories":90,"carbs_g":12.0,"sugar_g":8.0,"fiber_g":0.0,"protein_g":8.5,
        "fat_g":2.0,"sat_fat_g":1.3,"trans_fat_g":0.0,"sodium_mg":115,
        "potassium_mg":250,"magnesium_mg":18,"calcium_mg":250,"cholesterol_mg":12,"gi":36
    },
    "paneer": {
        "name":"Paneer (Cottage Cheese)","serving_g":100,
        "calories":265,"carbs_g":3.4,"sugar_g":0.5,"fiber_g":0.0,"protein_g":18.3,
        "fat_g":20.8,"sat_fat_g":13.0,"trans_fat_g":0.0,"sodium_mg":34,
        "potassium_mg":90,"magnesium_mg":8,"calcium_mg":490,"cholesterol_mg":55,"gi":None
    },
    "ghee": {
        "name":"Ghee","serving_g":10,
        "calories":90,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":0.0,
        "fat_g":10.0,"sat_fat_g":6.2,"trans_fat_g":0.1,"sodium_mg":0,
        "potassium_mg":1,"magnesium_mg":0,"calcium_mg":0,"cholesterol_mg":27,"gi":-1
    },
    "butter": {
        "name":"Butter","serving_g":10,
        "calories":72,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":0.1,
        "fat_g":8.1,"sat_fat_g":5.1,"trans_fat_g":0.2,"sodium_mg":64,
        "potassium_mg":3,"magnesium_mg":0,"calcium_mg":2,"cholesterol_mg":22,"gi":-1
    },
    "cheese": {
        "name":"Cheese (processed)","serving_g":30,
        "calories":105,"carbs_g":0.4,"sugar_g":0.2,"fiber_g":0.0,"protein_g":6.5,
        "fat_g":8.6,"sat_fat_g":5.5,"trans_fat_g":0.1,"sodium_mg":415,
        "potassium_mg":38,"magnesium_mg":8,"calcium_mg":185,"cholesterol_mg":26,"gi":0
    },
    "buttermilk": {
        "name":"Buttermilk (Chaas)","serving_g":200,
        "calories":40,"carbs_g":5.0,"sugar_g":5.0,"fiber_g":0.0,"protein_g":3.0,
        "fat_g":0.5,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":120,
        "potassium_mg":160,"magnesium_mg":14,"calcium_mg":130,"cholesterol_mg":5,"gi":36
    },

    # ── Proteins (8) ─────────────────────────────────────────────────────────
    "chicken_breast": {
        "name":"Chicken Breast (grilled)","serving_g":100,
        "calories":165,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":31.0,
        "fat_g":3.6,"sat_fat_g":1.0,"trans_fat_g":0.0,"sodium_mg":74,
        "potassium_mg":256,"magnesium_mg":28,"calcium_mg":15,"cholesterol_mg":85,"gi":-1
    },
    "chicken_curry": {
        "name":"Chicken Curry","serving_g":150,
        "calories":215,"carbs_g":5.0,"sugar_g":2.0,"fiber_g":1.0,"protein_g":20.0,
        "fat_g":13.0,"sat_fat_g":3.5,"trans_fat_g":0.0,"sodium_mg":520,
        "potassium_mg":280,"magnesium_mg":25,"calcium_mg":30,"cholesterol_mg":75,"gi":None
    },
    "whole_egg": {
        "name":"Whole Egg (boiled)","serving_g":50,
        "calories":78,"carbs_g":0.6,"sugar_g":0.1,"fiber_g":0.0,"protein_g":6.3,
        "fat_g":5.3,"sat_fat_g":1.6,"trans_fat_g":0.0,"sodium_mg":62,
        "potassium_mg":63,"magnesium_mg":6,"calcium_mg":25,"cholesterol_mg":186,"gi":None
    },
    "egg_white": {
        "name":"Egg White (boiled)","serving_g":50,
        "calories":26,"carbs_g":0.3,"sugar_g":0.1,"fiber_g":0.0,"protein_g":5.5,
        "fat_g":0.1,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":55,
        "potassium_mg":80,"magnesium_mg":10,"calcium_mg":3,"cholesterol_mg":0,"gi":-1
    },
    "fish_rohu": {
        "name":"Fish / Rohu (cooked)","serving_g":100,
        "calories":97,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":17.6,
        "fat_g":2.8,"sat_fat_g":0.7,"trans_fat_g":0.0,"sodium_mg":58,
        "potassium_mg":334,"magnesium_mg":30,"calcium_mg":650,"cholesterol_mg":66,"gi":-1
    },
    "mutton": {
        "name":"Mutton (cooked)","serving_g":100,
        "calories":294,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":25.6,
        "fat_g":20.6,"sat_fat_g":8.8,"trans_fat_g":0.2,"sodium_mg":72,
        "potassium_mg":292,"magnesium_mg":24,"calcium_mg":12,"cholesterol_mg":97,"gi":-1
    },
    "tofu": {
        "name":"Tofu","serving_g":100,
        "calories":76,"carbs_g":1.9,"sugar_g":0.5,"fiber_g":0.3,"protein_g":8.0,
        "fat_g":4.8,"sat_fat_g":0.7,"trans_fat_g":0.0,"sodium_mg":7,
        "potassium_mg":121,"magnesium_mg":30,"calcium_mg":350,"cholesterol_mg":0,"gi":15
    },
    "soya_milk": {
        "name":"Soya Milk (unsweetened)","serving_g":200,
        "calories":80,"carbs_g":6.0,"sugar_g":4.0,"fiber_g":1.0,"protein_g":6.4,
        "fat_g":3.6,"sat_fat_g":0.5,"trans_fat_g":0.0,"sodium_mg":100,
        "potassium_mg":290,"magnesium_mg":34,"calcium_mg":120,"cholesterol_mg":0,"gi":34
    },

    # ── South Indian Dishes (6) ───────────────────────────────────────────────
    "sambar": {
        "name":"Sambar","serving_g":200,
        "calories":130,"carbs_g":16.0,"sugar_g":4.0,"fiber_g":4.0,"protein_g":6.0,
        "fat_g":5.0,"sat_fat_g":1.2,"trans_fat_g":0.0,"sodium_mg":600,
        "potassium_mg":400,"magnesium_mg":35,"calcium_mg":60,"cholesterol_mg":0,"gi":55
    },
    "rasam": {
        "name":"Rasam","serving_g":200,
        "calories":60,"carbs_g":8.0,"sugar_g":3.0,"fiber_g":1.5,"protein_g":2.0,
        "fat_g":2.5,"sat_fat_g":0.5,"trans_fat_g":0.0,"sodium_mg":450,
        "potassium_mg":280,"magnesium_mg":20,"calcium_mg":30,"cholesterol_mg":0,"gi":35
    },
    "coconut_chutney": {
        "name":"Coconut Chutney","serving_g":50,
        "calories":95,"carbs_g":5.0,"sugar_g":2.5,"fiber_g":2.5,"protein_g":1.5,
        "fat_g":8.0,"sat_fat_g":6.5,"trans_fat_g":0.0,"sodium_mg":120,
        "potassium_mg":180,"magnesium_mg":25,"calcium_mg":10,"cholesterol_mg":0,"gi":None
    },
    "uttapam": {
        "name":"Uttapam (with vegetables)","serving_g":120,
        "calories":195,"carbs_g":30.0,"sugar_g":2.0,"fiber_g":2.5,"protein_g":6.0,
        "fat_g":5.5,"sat_fat_g":1.0,"trans_fat_g":0.0,"sodium_mg":380,
        "potassium_mg":150,"magnesium_mg":25,"calcium_mg":30,"cholesterol_mg":0,"gi":72
    },
    "pongal": {
        "name":"Ven Pongal","serving_g":200,
        "calories":305,"carbs_g":42.0,"sugar_g":0.5,"fiber_g":3.0,"protein_g":8.0,
        "fat_g":10.0,"sat_fat_g":4.0,"trans_fat_g":0.1,"sodium_mg":400,
        "potassium_mg":130,"magnesium_mg":30,"calcium_mg":25,"cholesterol_mg":12,"gi":58
    },
    "medu_vada": {
        "name":"Medu Vada","serving_g":80,
        "calories":215,"carbs_g":22.0,"sugar_g":1.0,"fiber_g":3.5,"protein_g":8.0,
        "fat_g":10.0,"sat_fat_g":1.5,"trans_fat_g":0.2,"sodium_mg":390,
        "potassium_mg":180,"magnesium_mg":30,"calcium_mg":35,"cholesterol_mg":0,"gi":74
    },

    # ── North Indian Dishes (6) ───────────────────────────────────────────────
    "dal_makhani": {
        "name":"Dal Makhani","serving_g":200,
        "calories":285,"carbs_g":32.0,"sugar_g":2.5,"fiber_g":8.5,"protein_g":12.0,
        "fat_g":11.0,"sat_fat_g":5.5,"trans_fat_g":0.0,"sodium_mg":580,
        "potassium_mg":430,"magnesium_mg":58,"calcium_mg":90,"cholesterol_mg":20,"gi":30
    },
    "palak_paneer": {
        "name":"Palak Paneer","serving_g":200,
        "calories":295,"carbs_g":10.0,"sugar_g":2.0,"fiber_g":4.0,"protein_g":16.0,
        "fat_g":22.0,"sat_fat_g":12.0,"trans_fat_g":0.0,"sodium_mg":420,
        "potassium_mg":500,"magnesium_mg":65,"calcium_mg":380,"cholesterol_mg":55,"gi":None
    },
    "chole": {
        "name":"Chole (Chickpea Curry)","serving_g":200,
        "calories":250,"carbs_g":35.0,"sugar_g":6.0,"fiber_g":10.0,"protein_g":12.0,
        "fat_g":7.0,"sat_fat_g":0.8,"trans_fat_g":0.0,"sodium_mg":560,
        "potassium_mg":480,"magnesium_mg":55,"calcium_mg":70,"cholesterol_mg":0,"gi":33
    },
    "aloo_sabzi": {
        "name":"Aloo Sabzi (Potato Curry)","serving_g":150,
        "calories":175,"carbs_g":28.0,"sugar_g":2.0,"fiber_g":3.5,"protein_g":3.5,
        "fat_g":6.5,"sat_fat_g":1.2,"trans_fat_g":0.0,"sodium_mg":380,
        "potassium_mg":480,"magnesium_mg":28,"calcium_mg":20,"cholesterol_mg":0,"gi":65
    },
    "kadhi": {
        "name":"Kadhi (Yogurt Curry)","serving_g":200,
        "calories":180,"carbs_g":18.0,"sugar_g":6.0,"fiber_g":2.0,"protein_g":7.0,
        "fat_g":9.0,"sat_fat_g":3.5,"trans_fat_g":0.0,"sodium_mg":520,
        "potassium_mg":220,"magnesium_mg":22,"calcium_mg":180,"cholesterol_mg":15,"gi":45
    },
    "rajma_chawal": {
        "name":"Rajma Chawal","serving_g":300,
        "calories":395,"carbs_g":72.0,"sugar_g":2.5,"fiber_g":11.0,"protein_g":16.0,
        "fat_g":5.0,"sat_fat_g":0.8,"trans_fat_g":0.0,"sodium_mg":480,
        "potassium_mg":620,"magnesium_mg":72,"calcium_mg":58,"cholesterol_mg":0,"gi":40
    },

    # ── Snacks & Street Food (8) ──────────────────────────────────────────────
    "samosa": {
        "name":"Samosa (fried)","serving_g":100,
        "calories":308,"carbs_g":30.0,"sugar_g":1.5,"fiber_g":2.0,"protein_g":5.0,
        "fat_g":19.0,"sat_fat_g":3.5,"trans_fat_g":1.8,"sodium_mg":380,
        "potassium_mg":230,"magnesium_mg":20,"calcium_mg":25,"cholesterol_mg":0,"gi":72
    },
    "pakoda": {
        "name":"Pakoda / Bhajji (fried)","serving_g":100,
        "calories":320,"carbs_g":28.0,"sugar_g":2.0,"fiber_g":3.0,"protein_g":8.0,
        "fat_g":20.0,"sat_fat_g":2.5,"trans_fat_g":1.2,"sodium_mg":420,
        "potassium_mg":280,"magnesium_mg":30,"calcium_mg":55,"cholesterol_mg":0,"gi":65
    },
    "dhokla": {
        "name":"Dhokla (steamed)","serving_g":100,
        "calories":150,"carbs_g":24.0,"sugar_g":3.0,"fiber_g":2.5,"protein_g":6.5,
        "fat_g":3.5,"sat_fat_g":0.5,"trans_fat_g":0.0,"sodium_mg":250,
        "potassium_mg":150,"magnesium_mg":20,"calcium_mg":35,"cholesterol_mg":0,"gi":35
    },
    "roasted_chana": {
        "name":"Roasted Chana","serving_g":50,
        "calories":180,"carbs_g":28.5,"sugar_g":4.5,"fiber_g":8.5,"protein_g":9.5,
        "fat_g":3.0,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":8,
        "potassium_mg":350,"magnesium_mg":45,"calcium_mg":50,"cholesterol_mg":0,"gi":22
    },
    "peanuts": {
        "name":"Peanuts (roasted)","serving_g":30,
        "calories":171,"carbs_g":5.0,"sugar_g":1.2,"fiber_g":2.4,"protein_g":7.8,
        "fat_g":14.6,"sat_fat_g":2.0,"trans_fat_g":0.0,"sodium_mg":4,
        "potassium_mg":183,"magnesium_mg":48,"calcium_mg":18,"cholesterol_mg":0,"gi":14
    },
    "murmura": {
        "name":"Murmura / Puffed Rice","serving_g":30,
        "calories":108,"carbs_g":24.0,"sugar_g":0.2,"fiber_g":0.5,"protein_g":1.9,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":25,"magnesium_mg":8,"calcium_mg":3,"cholesterol_mg":0,"gi":70
    },
    "sev": {
        "name":"Sev (fried gram noodles)","serving_g":30,
        "calories":160,"carbs_g":19.0,"sugar_g":1.5,"fiber_g":2.0,"protein_g":4.5,
        "fat_g":8.0,"sat_fat_g":1.5,"trans_fat_g":0.3,"sodium_mg":180,
        "potassium_mg":90,"magnesium_mg":20,"calcium_mg":25,"cholesterol_mg":0,"gi":55
    },
    "mixed_nuts": {
        "name":"Mixed Nuts (almonds/cashew/walnut)","serving_g":30,
        "calories":183,"carbs_g":7.0,"sugar_g":1.5,"fiber_g":2.2,"protein_g":5.0,
        "fat_g":16.0,"sat_fat_g":2.5,"trans_fat_g":0.0,"sodium_mg":2,
        "potassium_mg":195,"magnesium_mg":55,"calcium_mg":30,"cholesterol_mg":0,"gi":15
    },

    # ── Beverages (5) ────────────────────────────────────────────────────────
    "masala_chai": {
        "name":"Masala Chai (with milk + sugar)","serving_g":150,
        "calories":65,"carbs_g":10.0,"sugar_g":8.0,"fiber_g":0.0,"protein_g":2.5,
        "fat_g":1.5,"sat_fat_g":0.8,"trans_fat_g":0.0,"sodium_mg":30,
        "potassium_mg":120,"magnesium_mg":8,"calcium_mg":90,"cholesterol_mg":5,"gi":45
    },
    "black_tea": {
        "name":"Black Tea (no sugar)","serving_g":200,
        "calories":4,"carbs_g":0.9,"sugar_g":0.0,"fiber_g":0.0,"protein_g":0.1,
        "fat_g":0.0,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":7,
        "potassium_mg":88,"magnesium_mg":4,"calcium_mg":4,"cholesterol_mg":0,"gi":0
    },
    "lassi_sweet": {
        "name":"Sweet Lassi","serving_g":250,
        "calories":175,"carbs_g":28.0,"sugar_g":24.0,"fiber_g":0.0,"protein_g":7.5,
        "fat_g":4.5,"sat_fat_g":2.8,"trans_fat_g":0.0,"sodium_mg":140,
        "potassium_mg":360,"magnesium_mg":22,"calcium_mg":290,"cholesterol_mg":16,"gi":62
    },
    "sugarcane_juice": {
        "name":"Sugarcane Juice","serving_g":200,
        "calories":113,"carbs_g":28.0,"sugar_g":27.0,"fiber_g":0.0,"protein_g":0.4,
        "fat_g":0.2,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":3,
        "potassium_mg":42,"magnesium_mg":12,"calcium_mg":10,"cholesterol_mg":0,"gi":70
    },
    "coconut_water": {
        "name":"Coconut Water","serving_g":240,
        "calories":45,"carbs_g":11.0,"sugar_g":9.0,"fiber_g":0.0,"protein_g":1.7,
        "fat_g":0.5,"sat_fat_g":0.4,"trans_fat_g":0.0,"sodium_mg":252,
        "potassium_mg":600,"magnesium_mg":60,"calcium_mg":57,"cholesterol_mg":0,"gi":55
    },

    # ── Oils & Condiments (6) ─────────────────────────────────────────────────
    "mustard_oil": {
        "name":"Mustard Oil","serving_g":10,
        "calories":88,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":0.0,
        "fat_g":10.0,"sat_fat_g":1.2,"trans_fat_g":0.0,"sodium_mg":0,
        "potassium_mg":0,"magnesium_mg":0,"calcium_mg":0,"cholesterol_mg":0,"gi":-1
    },
    "coconut_oil": {
        "name":"Coconut Oil","serving_g":10,
        "calories":88,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":0.0,
        "fat_g":10.0,"sat_fat_g":8.6,"trans_fat_g":0.0,"sodium_mg":0,
        "potassium_mg":0,"magnesium_mg":0,"calcium_mg":0,"cholesterol_mg":0,"gi":-1
    },
    "olive_oil": {
        "name":"Olive Oil","serving_g":10,
        "calories":88,"carbs_g":0.0,"sugar_g":0.0,"fiber_g":0.0,"protein_g":0.0,
        "fat_g":10.0,"sat_fat_g":1.4,"trans_fat_g":0.0,"sodium_mg":0,
        "potassium_mg":0,"magnesium_mg":0,"calcium_mg":0,"cholesterol_mg":0,"gi":-1
    },
    "mango_pickle": {
        "name":"Mango Pickle / Achar","serving_g":20,
        "calories":42,"carbs_g":5.0,"sugar_g":2.5,"fiber_g":1.0,"protein_g":0.5,
        "fat_g":2.5,"sat_fat_g":0.3,"trans_fat_g":0.0,"sodium_mg":1100,
        "potassium_mg":50,"magnesium_mg":5,"calcium_mg":10,"cholesterol_mg":0,"gi":20
    },
    "green_chutney": {
        "name":"Green Chutney (mint/coriander)","serving_g":30,
        "calories":20,"carbs_g":3.5,"sugar_g":1.0,"fiber_g":1.5,"protein_g":0.8,
        "fat_g":0.4,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":85,
        "potassium_mg":100,"magnesium_mg":12,"calcium_mg":30,"cholesterol_mg":0,"gi":25
    },
    "tamarind_chutney": {
        "name":"Tamarind Chutney","serving_g":20,
        "calories":55,"carbs_g":14.0,"sugar_g":10.0,"fiber_g":0.8,"protein_g":0.3,
        "fat_g":0.1,"sat_fat_g":0.0,"trans_fat_g":0.0,"sodium_mg":210,
        "potassium_mg":85,"magnesium_mg":12,"calcium_mg":15,"cholesterol_mg":0,"gi":65
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FoodItem:
    food_id: str
    data: dict

    def scale(self, quantity_g: float) -> "FoodItem":
        """Scale all nutrient fields proportionally to quantity_g. GI is NEVER scaled."""
        if quantity_g <= 0:
            raise ValueError(f"quantity_g must be > 0, got {quantity_g}")
        ratio = quantity_g / self.data["serving_g"]
        scaled = deepcopy(self.data)
        scaled["serving_g"] = quantity_g
        for f in ["calories","carbs_g","sugar_g","fiber_g","protein_g","fat_g",
                  "sat_fat_g","trans_fat_g","sodium_mg","potassium_mg",
                  "magnesium_mg","calcium_mg","cholesterol_mg"]:
            scaled[f] = round(self.data[f] * ratio, 2)
        # GI is intrinsic — not a quantity-dependent value
        return FoodItem(self.food_id, scaled)


@dataclass
class Thresholds:
    """All clinical cutoffs — from_profile() tightens these based on user's conditions."""
    # Diabetes
    gi_limit:               int   = 55    # Atkinson 2008
    gl_limit:               float = 10.0  # Salmeron 1997
    fiber_carb_ratio_min:   float = 0.10  # ADA 2023
    sugar_carb_ratio_max:   float = 0.25  # WHO 2015
    protein_fat_buffer_min: float = 0.25  # Nuttall 2006
    # Hypertension
    sodium_limit_mg:        float = 500.0  # AHA 2021
    sodium_instant_fail_mg: float = 600.0  # Mente 2017 Lancet
    k_na_ratio_min:         float = 2.0    # DASH Sacks 2001
    # Obesity
    energy_density_max:     float = 1.5    # Rolls 2009 kcal/g
    protein_satiety_min:    float = 0.15   # Weigle 2005
    fat_cal_ratio_max:      float = 0.35   # ICMR-NIN 2020
    # Cholesterol
    cholesterol_limit_mg:   float = 200.0  # AHA/ACC 2019
    sat_fat_ratio_max:      float = 0.07   # Mensink 2016
    trans_fat_limit_g:      float = 1.0    # WHO REPLACE 2018
    # Shared instant fails
    sugar_instant_fail_g:   float = 12.0   # ADA 2023

    @classmethod
    def from_profile(cls, profile: dict) -> "Thresholds":
        t = cls()
        conditions  = profile.get("conditions") or []
        severities  = profile.get("condition_severities") or {}
        age         = profile.get("age") or 35

        if "diabetes" in conditions or "Diabetes" in conditions:
            sev = severities.get("Diabetes", severities.get("diabetes", "controlled"))
            if sev == "uncontrolled":
                t.gi_limit               = 45 if age >= 65 else 50
                t.gl_limit               = 8.0
                t.sugar_instant_fail_g   = 8.0
                t.fiber_carb_ratio_min   = 0.15
            elif sev == "prediabetes":
                t.gi_limit  = 60
                t.gl_limit  = 12.0
            # Age-adjusted GI tightening (ADA 2023)
            if age >= 65 and sev != "prediabetes":
                t.gi_limit = max(t.gi_limit - 5, 40)
                t.gl_limit = max(t.gl_limit - 2, 6.0)

        if "hypertension" in conditions or "Hypertension" in conditions:
            sev = severities.get("Hypertension", severities.get("hypertension", "stage1"))
            if sev == "stage2":
                t.sodium_limit_mg        = 400.0
                t.sodium_instant_fail_mg = 450.0
                t.k_na_ratio_min         = 3.0
            elif sev == "elevated":
                t.sodium_limit_mg        = 550.0
                t.sodium_instant_fail_mg = 650.0

        if "obesity" in conditions or "Obesity" in conditions:
            sev = severities.get("Obesity", severities.get("obesity", "class1"))
            if sev == "class2":
                t.energy_density_max  = 1.2
                t.protein_satiety_min = 0.20
                t.fat_cal_ratio_max   = 0.30

        # Doctor overrides — always highest priority
        if profile.get("doctor_gi_limit"):
            t.gi_limit = int(profile["doctor_gi_limit"])
        if profile.get("doctor_sodium_limit_mg"):
            t.sodium_limit_mg        = float(profile["doctor_sodium_limit_mg"])
            t.sodium_instant_fail_mg = t.sodium_limit_mg + 50

        return t


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — CONDITION SCORERS
# Returns list of FlagResult dicts matching frontend interface:
# {label, severity: 'low'|'medium'|'high', message, category, moderation}
# Also returns score 0.0 - 5.0
# ─────────────────────────────────────────────────────────────────────────────

def _flag(label: str, sev: str, msg: str, cat: str, mod: str = "") -> dict:
    return {"label": label, "severity": sev, "message": msg,
            "category": cat, "moderation": mod}


def _score_diabetes(d: dict, t: Thresholds) -> tuple[float, list]:
    flags, score = [], 0.0

    gi = d["gi"]
    net_carbs = max(0.0, d["carbs_g"] - d["fiber_g"])

    # 1. GI (1.0 pt)
    if gi == -1:
        score += 1.0
    elif gi is None:
        score += 0.5  # uncertain — partial credit
        flags.append(_flag("GI Unknown","low",
            "GI not available — partial credit only.","diabetes",
            "Verify glycemic impact before including in regular diet."))
    elif gi <= t.gi_limit:
        score += 1.0
    else:
        sev = "high" if gi > 70 else "medium"
        flags.append(_flag(f"High GI ({gi})", sev,
            f"GI {gi} exceeds your {t.gi_limit} limit — will spike blood sugar.","diabetes",
            f"Replace with lower-GI alternative (GI ≤ {t.gi_limit})."))

    # 2. GL (1.0 pt) — GL = (GI × net_carbs) / 100
    if gi is not None and gi > 0:
        gl = round((gi * net_carbs) / 100, 1)
        if gl <= t.gl_limit:
            score += 1.0
        else:
            sev = "high" if gl > 20 else "medium"
            flags.append(_flag(f"Glycemic Load {gl}", sev,
                f"GL {gl} exceeds {t.gl_limit} limit.","diabetes",
                f"Reduce portion by ~30% to bring GL under {t.gl_limit}."))
    elif d["carbs_g"] == 0:
        score += 1.0
    else:
        score += 0.5

    # 3. Fiber:Carb ratio (1.0 pt)
    if d["carbs_g"] > 0:
        fc = d["fiber_g"] / d["carbs_g"]
        if fc >= t.fiber_carb_ratio_min:
            score += 1.0
        else:
            flags.append(_flag("Low Fiber:Carb Ratio","medium",
                f"Fiber:Carb ratio {fc:.2f} is below {t.fiber_carb_ratio_min} minimum.","diabetes",
                "Add vegetables or swap for whole grains to improve ratio."))
    else:
        score += 1.0

    # 4. Sugar proportion (1.0 pt)
    if d["carbs_g"] > 0:
        sr = d["sugar_g"] / d["carbs_g"]
        if sr <= t.sugar_carb_ratio_max:
            score += 1.0
        else:
            flags.append(_flag("High Sugar Proportion","high",
                f"Sugar is {sr:.0%} of carbs — above {t.sugar_carb_ratio_max:.0%} limit.","diabetes",
                f"Reduce sugar by {round(d['sugar_g'] - d['carbs_g']*t.sugar_carb_ratio_max,1)}g."))
    else:
        score += 1.0

    # 5. Protein-fat buffer (1.0 pt)
    if d["calories"] > 0:
        buf = (d["protein_g"]*4 + d["fat_g"]*9) / d["calories"]
        if buf >= t.protein_fat_buffer_min:
            score += 1.0
        else:
            flags.append(_flag("Low Protein-Fat Buffer","low",
                f"Protein+fat is only {buf:.0%} of calories — poor glucose buffer.","diabetes",
                "Add protein source (dal/egg) to slow glucose absorption."))
    else:
        score += 1.0

    return round(min(score, 5.0), 2), flags


def _score_hypertension(d: dict, t: Thresholds) -> tuple[float, list]:
    flags, score = [], 0.0

    # 1. Sodium (1.5 pt)
    if d["sodium_mg"] <= t.sodium_limit_mg * 0.4:
        score += 1.5
    elif d["sodium_mg"] <= t.sodium_limit_mg:
        score += 0.75
        flags.append(_flag("Moderate Sodium","low",
            f"Sodium {d['sodium_mg']:.0f}mg is acceptable but monitor daily total.","hypertension",
            "Keep total daily sodium under 1500mg."))
    else:
        sev = "high" if d["sodium_mg"] > t.sodium_instant_fail_mg else "medium"
        flags.append(_flag("High Sodium","medium" if sev=="medium" else "high",
            f"Sodium {d['sodium_mg']:.0f}mg exceeds {t.sodium_limit_mg:.0f}mg limit.","hypertension",
            f"Reduce sodium by {d['sodium_mg']-t.sodium_limit_mg:.0f}mg. Avoid processed foods."))

    # 2. K:Na ratio (1.0 pt)
    if d["sodium_mg"] > 0:
        kna = d["potassium_mg"] / d["sodium_mg"]
        if kna >= t.k_na_ratio_min:
            score += 1.0
        else:
            flags.append(_flag("Poor K:Na Ratio","medium",
                f"K:Na ratio {kna:.1f} below {t.k_na_ratio_min} minimum.","hypertension",
                "Add potassium-rich foods: spinach, rajma, coconut water."))
    else:
        score += 1.0

    # 3. Magnesium (0.5 pt)
    if d["magnesium_mg"] >= 25:
        score += 0.5
    else:
        flags.append(_flag("Low Magnesium","low",
            f"Magnesium {d['magnesium_mg']}mg — helps regulate blood pressure.","hypertension",
            "Include nuts, green leafy vegetables for magnesium."))

    # 4. Fiber (0.5 pt)
    if d["fiber_g"] >= 3:
        score += 0.5
    else:
        flags.append(_flag("Low Fiber","low",
            f"Fiber {d['fiber_g']}g — dietary fiber reduces arterial stiffness.","hypertension",
            "Add 5g+ fiber: vegetables, whole grains, or dal."))

    # 5. Saturated fat ratio (0.5 pt)
    if d["calories"] > 0:
        sr = (d["sat_fat_g"]*9) / d["calories"]
        if sr <= 0.10:
            score += 0.5
        else:
            flags.append(_flag("High Saturated Fat","medium",
                f"Saturated fat {sr:.0%} of calories — increases arterial stiffness.","hypertension",
                "Replace ghee/butter with mustard or olive oil."))

    # 6. Sugar:calorie ratio (0.5 pt)
    if d["calories"] > 0:
        scr = (d["sugar_g"]*4) / d["calories"]
        if scr <= 0.15:
            score += 0.5
        else:
            flags.append(_flag("High Sugar Intake","low",
                f"Sugar is {scr:.0%} of calories — excess sugar raises BP via insulin.","hypertension",
                "Reduce sweet beverages and desserts."))

    return round(min(score, 5.0), 2), flags


def _score_obesity(d: dict, t: Thresholds) -> tuple[float, list]:
    flags, score = [], 0.0

    # 1. Energy density (1.5 pt)
    ed = d["calories"] / d["serving_g"] if d["serving_g"] > 0 else 999
    if ed <= t.energy_density_max * 0.6:
        score += 1.5
    elif ed <= t.energy_density_max:
        score += 0.75
        flags.append(_flag("Moderate Energy Density","low",
            f"Energy density {ed:.2f} kcal/g — consider smaller portion.","obesity",""))
    else:
        sev = "high" if ed > 3.0 else "medium"
        flags.append(_flag(f"High Energy Density ({ed:.1f} kcal/g)", sev,
            f"Calorie density {ed:.2f} kcal/g exceeds {t.energy_density_max} limit.","obesity",
            f"Reduce portion by {round((1 - t.energy_density_max/ed)*100)}% or swap to lower-calorie option."))

    # 2. Protein satiety ratio (1.5 pt)
    if d["calories"] > 0:
        psr = (d["protein_g"]*4) / d["calories"]
        if psr >= t.protein_satiety_min:
            score += 1.5
        else:
            flags.append(_flag("Low Protein Content","medium",
                f"Protein is {psr:.0%} of calories — low satiety may cause overeating.","obesity",
                f"Add {round((t.protein_satiety_min - psr)*d['calories']/4)}g more protein (egg/dal/chicken)."))

    # 3. Fiber (1.0 pt)
    if d["fiber_g"] >= 3:
        score += 1.0
    elif d["fiber_g"] >= 1.5:
        score += 0.5
        flags.append(_flag("Moderate Fiber","low",
            f"Fiber {d['fiber_g']}g — aim for 5g+ per meal for satiety.","obesity","Add vegetables or legumes."))
    else:
        flags.append(_flag("Low Fiber","medium",
            f"Fiber only {d['fiber_g']}g — very low satiety value.","obesity",
            "Add 100g vegetables or 50g dal for fiber boost."))

    # 4. Fat:calorie ratio (0.5 pt)
    if d["calories"] > 0:
        fcr = (d["fat_g"]*9) / d["calories"]
        if fcr <= t.fat_cal_ratio_max:
            score += 0.5
        else:
            flags.append(_flag("High Fat Content","medium",
                f"Fat is {fcr:.0%} of calories — high energy density.","obesity",
                f"Reduce fat by {round(d['fat_g'] - t.fat_cal_ratio_max*d['calories']/9, 1)}g."))

    # 5. Sugar:calorie ratio (0.5 pt)
    if d["calories"] > 0:
        scr = (d["sugar_g"]*4) / d["calories"]
        if scr <= 0.20:
            score += 0.5
        else:
            flags.append(_flag("High Sugar","medium",
                f"Sugar {d['sugar_g']}g adds empty calories without satiety.","obesity",
                "Replace sweet items with whole fruit or reduce sugar."))

    return round(min(score, 5.0), 2), flags


def _score_cholesterol(d: dict, t: Thresholds) -> tuple[float, list]:
    flags, score = [], 0.0

    # 1. Dietary cholesterol (1.0 pt)
    if d["cholesterol_mg"] == 0:
        score += 1.0
    elif d["cholesterol_mg"] <= 100:
        score += 0.75
    elif d["cholesterol_mg"] <= t.cholesterol_limit_mg:
        score += 0.25
        flags.append(_flag("Moderate Cholesterol","low",
            f"Dietary cholesterol {d['cholesterol_mg']}mg — monitor total daily intake.","cholesterol",""))
    else:
        flags.append(_flag("High Dietary Cholesterol","high",
            f"Dietary cholesterol {d['cholesterol_mg']}mg exceeds {t.cholesterol_limit_mg}mg limit.","cholesterol",
            "Limit egg yolks/organ meats. Prefer plant-based proteins."))

    # 2. Trans fat (1.0 pt) — WHO REPLACE 2018: zero tolerance
    if d["trans_fat_g"] == 0:
        score += 1.0
    elif d["trans_fat_g"] < 0.5:
        score += 0.5
        flags.append(_flag("Trace Trans Fat","low",
            f"Small amount of trans fat {d['trans_fat_g']}g detected.","cholesterol",
            "Avoid foods fried in vanaspati or partially hydrogenated oils."))
    else:
        sev = "high" if d["trans_fat_g"] >= t.trans_fat_limit_g else "medium"
        flags.append(_flag(f"Trans Fat {d['trans_fat_g']}g", sev,
            f"Trans fat {d['trans_fat_g']}g directly raises LDL and lowers HDL.","cholesterol",
            "Avoid all fried snacks (samosa/pakoda) made with vanaspati."))

    # 3. Saturated fat ratio (1.0 pt)
    if d["calories"] > 0:
        sr = (d["sat_fat_g"]*9) / d["calories"]
        if sr <= t.sat_fat_ratio_max:
            score += 1.0
        elif sr <= 0.12:
            score += 0.5
            flags.append(_flag("Moderate Sat Fat","low",
                f"Saturated fat {sr:.0%} of calories — slightly elevated.","cholesterol",
                "Use less ghee/butter. Switch to mustard/olive oil."))
        else:
            flags.append(_flag("High Saturated Fat","high",
                f"Saturated fat {sr:.0%} raises LDL cholesterol.","cholesterol",
                f"Reduce sat fat by {round(d['sat_fat_g'] - t.sat_fat_ratio_max*d['calories']/9, 1)}g."))

    # 4. Soluble fiber LDL proxy (1.0 pt)
    if d["fiber_g"] >= 4:
        score += 1.0
    elif d["fiber_g"] >= 2:
        score += 0.5
        flags.append(_flag("Low Soluble Fiber","low",
            f"Fiber {d['fiber_g']}g — soluble fiber lowers LDL.","cholesterol",
            "Add oats, rajma, or fruits for LDL-lowering fiber."))
    else:
        flags.append(_flag("Very Low Fiber","medium",
            f"Fiber {d['fiber_g']}g — insufficient to reduce LDL.","cholesterol",
            "Include 8-10g soluble fiber daily: oats, apples, rajma."))

    # 5. Unsaturated fat ratio (1.0 pt)
    unsat = max(0.0, d["fat_g"] - d["sat_fat_g"] - d["trans_fat_g"])
    if d["fat_g"] > 0.5:
        ur = unsat / d["fat_g"]
        if ur >= 0.70:
            score += 1.0
        elif ur >= 0.50:
            score += 0.5
            flags.append(_flag("Low Unsaturated Fat","low",
                f"Unsaturated fat ratio {ur:.0%} — prefer heart-healthy fats.","cholesterol",
                "Use olive/mustard oil. Add nuts and seeds."))
        else:
            flags.append(_flag("Poor Fat Quality","medium",
                f"Only {ur:.0%} of fat is unsaturated — bad for LDL/HDL ratio.","cholesterol",
                "Replace saturated fats with olive oil, avocado, fish."))
    else:
        score += 1.0  # negligible fat

    return round(min(score, 5.0), 2), flags


CONDITION_SCORERS = {
    "Diabetes":     _score_diabetes,
    "Hypertension": _score_hypertension,
    "Obesity":      _score_obesity,
    "Cholesterol":  _score_cholesterol,
}

CONDITION_ALIASES = {
    "diabetis":"Diabetes","diabetic":"Diabetes","dm":"Diabetes","t2dm":"Diabetes","type2":"Diabetes",
    "hypertension":"Hypertension","bp":"Hypertension","htn":"Hypertension","high blood pressure":"Hypertension",
    "obesity":"Obesity","overweight":"Obesity","obese":"Obesity",
    "cholesterol":"Cholesterol","hyperlipidemia":"Cholesterol","high cholesterol":"Cholesterol",
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — FUZZY SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def search_foods(query: str, limit: int = 8) -> List[dict]:
    """Fuzzy search food database. Returns [{id, name}] sorted by match quality."""
    q = query.lower().strip()
    q_id = q.replace(" ", "_")
    ids = list(RAW_FOODS.keys())
    names_lower = [RAW_FOODS[fid]["name"].lower() for fid in ids]

    seen = set()
    results = []

    # 1. Exact substring match on ID
    for fid in ids:
        if q_id in fid or fid in q_id:
            if fid not in seen:
                seen.add(fid)
                results.append({"id": fid, "name": RAW_FOODS[fid]["name"]})

    # 2. Fuzzy on IDs
    for fid in difflib.get_close_matches(q_id, ids, n=5, cutoff=0.4):
        if fid not in seen:
            seen.add(fid)
            results.append({"id": fid, "name": RAW_FOODS[fid]["name"]})

    # 3. Substring match on display names
    for i, nm in enumerate(names_lower):
        if q in nm or nm in q:
            fid = ids[i]
            if fid not in seen:
                seen.add(fid)
                results.append({"id": fid, "name": RAW_FOODS[fid]["name"]})

    # 4. Fuzzy on display names
    for nm in difflib.get_close_matches(q, names_lower, n=3, cutoff=0.45):
        fid = ids[names_lower.index(nm)]
        if fid not in seen:
            seen.add(fid)
            results.append({"id": fid, "name": RAW_FOODS[fid]["name"]})

    return results[:limit]


def _map_name_to_id(name: str) -> Optional[str]:
    """Map a free-text food name (from Gemini or user) to a RAW_FOODS key."""
    results = search_foods(name, limit=1)
    return results[0]["id"] if results else None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — MAIN SCORING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def score_food(food_id: str, quantity_g: float, user_profile: dict) -> dict:
    """
    Score a single food item against user's active conditions.

    Returns:
        dict with:
          - food_name, quantity_g
          - risk_score (0-100, matches frontend: lower = safer)
          - flags: {flags: [{label,severity,message,category,moderation}]}
          - nutrition (per actual quantity consumed)
          - per_condition_scores {condition: score/5.0}
          - error (if validation fails)
          - suggestions (if food_id not found)
    """
    # Validation
    if food_id not in RAW_FOODS:
        suggestions = search_foods(food_id)
        return {"error": f"Food '{food_id}' not found.", "suggestions": suggestions}

    if quantity_g <= 0:
        return {"error": "Quantity must be a positive number."}

    conditions = []
    for c in (user_profile.get("conditions") or []):
        key = c.lower().strip()
        conditions.append(CONDITION_ALIASES.get(key, c))
    conditions = list(dict.fromkeys(conditions))  # deduplicate

    if not conditions:
        return {"error": "no_conditions",
                "message": "No health conditions set. Please update your profile."}

    # Scale to actual quantity
    food = FoodItem(food_id, RAW_FOODS[food_id]).scale(quantity_g)
    d = food.data

    # Personalised thresholds
    t = Thresholds.from_profile({**user_profile, "conditions": conditions})

    # Score each active condition
    all_flags = []
    per_condition_scores = {}
    total_score, max_score = 0.0, 0.0

    for cond in conditions:
        if cond in CONDITION_SCORERS:
            sc, flags = CONDITION_SCORERS[cond](d, t)
            per_condition_scores[cond] = {"score": sc, "max_score": 5.0, "passed": sc >= 3.0}
            total_score += sc
            max_score   += 5.0
            all_flags.extend(flags)

    # Triple-threat instant fails — caps composite at 55 and forces High Risk
    instant_fail = False

    if ("Hypertension" in conditions or "hypertension" in conditions) \
            and d["sodium_mg"] > t.sodium_instant_fail_mg:
        all_flags.append(_flag(
            "⛔ SODIUM INSTANT FAIL", "high",
            f"Sodium {d['sodium_mg']:.0f}mg exceeds {t.sodium_instant_fail_mg:.0f}mg hard limit.",
            "hypertension",
            f"Reduce sodium by {d['sodium_mg']-t.sodium_instant_fail_mg:.0f}mg immediately."
        ))
        instant_fail = True

    if ("Cholesterol" in conditions or "cholesterol" in conditions) \
            and d["trans_fat_g"] >= t.trans_fat_limit_g:
        all_flags.append(_flag(
            "⛔ TRANS FAT INSTANT FAIL", "high",
            f"Trans fat {d['trans_fat_g']}g ≥ {t.trans_fat_limit_g}g WHO zero-tolerance limit.",
            "cholesterol",
            "Avoid all vanaspati-fried foods completely."
        ))
        instant_fail = True

    if any(c in conditions for c in ("Diabetes","diabetes","Obesity","obesity")) \
            and d["sugar_g"] > t.sugar_instant_fail_g:
        all_flags.append(_flag(
            "⛔ SUGAR INSTANT FAIL", "high",
            f"Sugar {d['sugar_g']}g exceeds {t.sugar_instant_fail_g}g instant-fail threshold.",
            "diabetes",
            f"Reduce sugar by {d['sugar_g']-t.sugar_instant_fail_g:.1f}g minimum."
        ))
        instant_fail = True

    # Composite percentage → risk_score
    if max_score > 0:
        good_pct = (total_score / max_score) * 100
    else:
        good_pct = 50.0

    # Protective bonuses (max +5 percentage points to good_pct)
    bonus = 0.0
    if d["sodium_mg"] > 0 and (d["potassium_mg"] / d["sodium_mg"]) >= 4.0:
        bonus += 2.0
    if d["fiber_g"] >= 6:
        bonus += 2.0
    gi = d["gi"]
    if gi and gi > 0:
        net_carbs = max(0.0, d["carbs_g"] - d["fiber_g"])
        gl = (gi * net_carbs) / 100
        if gl <= 7:
            bonus += 1.5
    if d["cholesterol_mg"] == 0:
        bonus += 1.5

    good_pct = min(100.0, good_pct + bonus)

    if instant_fail:
        good_pct = min(good_pct, 45.0)

    # Convert "good_pct" to risk_score (frontend expects: lower = safer)
    # risk_score = 100 - good_pct, mapped to 0-100
    risk_score = round(100.0 - good_pct, 1)

    nutrition = {
        "calories":   d["calories"],   "carbs":    d["carbs_g"],
        "sugar":      d["sugar_g"],    "fiber":    d["fiber_g"],
        "protein":    d["protein_g"],  "fat":      d["fat_g"],
        "sodium":     d["sodium_mg"],  "potassium":d["potassium_mg"],
        "cholesterol":d["cholesterol_mg"],
    }

    return {
        "food_id":               food_id,
        "food_name":             RAW_FOODS[food_id]["name"],
        "quantity_g":            quantity_g,
        "risk_score":            risk_score,
        "flags":                 {"flags": all_flags},
        "per_condition_scores":  per_condition_scores,
        "nutrition":             nutrition,
        "instant_fail":          instant_fail,
    }


def score_meal(food_items: list, user_profile: dict) -> dict:
    """
    Score a complete meal (multiple food items).
    Aggregates per-food scores and returns meal-level result.

    food_items: [{"name": str, "quantity": float}, ...]
    """
    scored_items = []
    total_nutrition = {k: 0.0 for k in
        ["calories","carbs","sugar","fiber","protein","fat","sodium","potassium","cholesterol"]}
    per_item_nutrition = {}
    all_flags = []
    all_condition_totals: dict = {}
    has_instant_fail = False

    for item in food_items:
        food_id = _map_name_to_id(item["name"])
        qty     = float(item.get("quantity", 100))

        if not food_id:
            # Food not found — skip but note it
            continue

        result = score_food(food_id, qty, user_profile)
        if "error" in result:
            continue

        scored_items.append({
            "food_id":   food_id,
            "food_name": result["food_name"],
            "quantity":  qty,
            "risk_score":result["risk_score"],
        })

        # Aggregate nutrients
        for k in total_nutrition:
            total_nutrition[k] += result["nutrition"].get(k, 0)

        # Per-item nutrition (used by frontend AnalysisDashboard)
        per_item_nutrition[result["food_name"]] = {
            "calories": result["nutrition"]["calories"],
            "carbs":    result["nutrition"]["carbs"],
            "sugar":    result["nutrition"]["sugar"],
            "fiber":    result["nutrition"]["fiber"],
            "protein":  result["nutrition"]["protein"],
            "fat":      result["nutrition"]["fat"],
            "sodium":   result["nutrition"]["sodium"],
        }

        # Collect flags
        all_flags.extend(result["flags"]["flags"])
        if result["instant_fail"]:
            has_instant_fail = True

        # Aggregate per-condition scores
        for cond, cs in result["per_condition_scores"].items():
            if cond not in all_condition_totals:
                all_condition_totals[cond] = {"score": 0.0, "max_score": 0.0}
            all_condition_totals[cond]["score"]     += cs["score"]
            all_condition_totals[cond]["max_score"] += cs["max_score"]

    # Meal-level composite risk score
    if all_condition_totals:
        total_good  = sum(v["score"]     for v in all_condition_totals.values())
        total_max   = sum(v["max_score"] for v in all_condition_totals.values())
        good_pct    = (total_good / total_max * 100) if total_max > 0 else 50.0
    else:
        good_pct = 50.0

    if has_instant_fail:
        good_pct = min(good_pct, 45.0)

    risk_score = round(100.0 - good_pct, 1)
    rounded_nutrition = {k: round(v, 1) for k, v in total_nutrition.items()}

    return {
        "risk_score":         risk_score,
        "flags":              {"flags": all_flags},
        "nutrition_data":     rounded_nutrition,
        "per_item_nutrition": per_item_nutrition,
        "scored_items":       scored_items,
        "has_instant_fail":   has_instant_fail,
    }