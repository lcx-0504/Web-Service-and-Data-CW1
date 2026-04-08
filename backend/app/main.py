from fastapi import FastAPI

from app.routers import auth, foods, meals, analytics

app = FastAPI(
    title="NutriTrack API",
    description="Food Nutrition Tracking & Analysis API",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(foods.router)
app.include_router(meals.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    return {"message": "NutriTrack API is running"}
