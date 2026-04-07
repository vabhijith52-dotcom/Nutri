# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, metrics, meals, foods, diet, progress, bot

app = FastAPI(
    title="NutriSense API",
    description="AI-Powered Indian Metabolic Health Platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080",
                   "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(metrics.router)
app.include_router(meals.router)
app.include_router(foods.router)
app.include_router(diet.router)
app.include_router(progress.router)
app.include_router(bot.router)


@app.get("/")
def root():
    return {"status": "NutriSense API running", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}