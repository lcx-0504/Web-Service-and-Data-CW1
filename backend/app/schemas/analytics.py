from pydantic import BaseModel


class NutrientSummary(BaseModel):
    calories: float
    protein: float
    fat: float
    carbs: float
    fiber: float


class DailySummaryResponse(BaseModel):
    date: str
    total: NutrientSummary
    meal_count: int


class DailyEntry(BaseModel):
    date: str
    total: NutrientSummary
    meal_count: int


class WeeklyTrendResponse(BaseModel):
    start_date: str
    end_date: str
    daily: list[DailyEntry]
    average: NutrientSummary


class NutrientBalance(BaseModel):
    nutrient: str
    actual: float
    recommended: float
    percentage: float  # actual / recommended * 100
    status: str  # "low" / "ok" / "high"


class BalanceResponse(BaseModel):
    date: str
    items: list[NutrientBalance]
