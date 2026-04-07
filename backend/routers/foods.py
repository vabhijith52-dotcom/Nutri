# backend/routers/foods.py
from fastapi import APIRouter, Query
from services.scoring_engine import search_foods, RAW_FOODS

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    return search_foods(q)


@router.get("/all")
def list_all():
    return [{"id": k, "name": v["name"], "category": _cat(k)}
            for k, v in RAW_FOODS.items()]


def _cat(food_id: str) -> str:
    cats = {
        "grain": ["rice","roti","idli","dosa","upma","poha","oats","bread","paratha","jowar","bajra"],
        "dal":   ["moong","rajma","chana","toor","urad","masoor","peas","soya","sprouted"],
        "vegetable": ["spinach","potato","sweet_potato","cauliflower","brinjal","okra","tomato",
                      "carrot","bottle","bitter","corn","onion","capsicum","drumstick"],
        "fruit": ["banana","apple","mango","orange","guava","papaya","watermelon","grapes","pear","pomegranate"],
        "dairy": ["milk","curd","paneer","ghee","butter","cheese","buttermilk"],
        "protein": ["chicken","egg","fish","mutton","tofu","soya_milk"],
        "south_indian": ["sambar","rasam","coconut_chutney","uttapam","pongal","medu"],
        "north_indian": ["dal_makhani","palak","chole","aloo","kadhi","rajma_chawal"],
        "snack": ["samosa","pakoda","dhokla","roasted_chana","peanuts","murmura","sev","mixed_nuts"],
        "beverage": ["chai","tea","lassi","sugarcane","coconut_water"],
        "oil": ["mustard_oil","coconut_oil","olive_oil","pickle","chutney"],
    }
    for cat, keys in cats.items():
        if any(k in food_id for k in keys):
            return cat
    return "other"