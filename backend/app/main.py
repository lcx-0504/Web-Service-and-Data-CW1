from fastapi import FastAPI

app = FastAPI(
    title="NutriTrack API",
    description="Food Nutrition Tracking & Analysis API",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "NutriTrack API is running"}
