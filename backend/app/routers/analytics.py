from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.meal import Meal
from app.models.meal_item import MealItem
from app.models.food import Food
from app.auth.jwt import get_current_user
from app.schemas.analytics import (
    NutrientSummary,
    DailySummaryResponse,
    DailyEntry,
    WeeklyTrendResponse,
    NutrientBalance,
    BalanceResponse,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# FDA Daily Reference Values (fallback when user has no profile)
FDA_DEFAULTS = {
    "calories": 2000.0,
    "protein": 50.0,
    "fat": 65.0,
    "carbs": 300.0,
    "fiber": 25.0,
}

# Activity level multipliers (Harris-Benedict)
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def _get_personalized_daily(user: User) -> dict[str, float]:
    """Calculate personalized daily recommended values based on user profile.

    Uses Mifflin-St Jeor equation for BMR, then multiplies by activity factor.
    Falls back to FDA defaults if profile is incomplete.
    """
    if not all([user.height, user.weight, user.age, user.gender]):
        return FDA_DEFAULTS.copy()

    # Mifflin-St Jeor BMR
    if user.gender == "male":
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
    else:
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161

    multiplier = ACTIVITY_MULTIPLIERS.get(user.activity_level or "moderate", 1.55)
    tdee = bmr * multiplier

    # Macros based on TDEE (balanced diet: 20% protein, 25% fat, 55% carbs)
    return {
        "calories": round(tdee, 1),
        "protein": round(tdee * 0.20 / 4, 1),     # 4 kcal/g protein
        "fat": round(tdee * 0.25 / 9, 1),          # 9 kcal/g fat
        "carbs": round(tdee * 0.55 / 4, 1),        # 4 kcal/g carbs
        "fiber": 25.0,                               # FDA fixed
    }


async def _get_daily_totals(db: AsyncSession, user_id: int, target_date: date) -> tuple[NutrientSummary, int]:
    """Calculate total nutrients for a user on a given date."""
    query = (
        select(MealItem.quantity, Food.calories, Food.protein, Food.fat, Food.carbs, Food.fiber)
        .join(Meal, MealItem.meal_id == Meal.id)
        .join(Food, MealItem.food_id == Food.id)
        .where(Meal.user_id == user_id, Meal.date == target_date)
    )
    result = await db.execute(query)
    rows = result.all()

    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}
    for qty, cal, pro, fat, carb, fib in rows:
        factor = qty / 100.0
        totals["calories"] += cal * factor
        totals["protein"] += pro * factor
        totals["fat"] += fat * factor
        totals["carbs"] += carb * factor
        totals["fiber"] += fib * factor

    # Round to 2 decimal places
    summary = NutrientSummary(**{k: round(v, 2) for k, v in totals.items()})

    # Count distinct meals
    meal_count_q = (
        select(Meal.id)
        .where(Meal.user_id == user_id, Meal.date == target_date)
    )
    meal_result = await db.execute(meal_count_q)
    meal_count = len(meal_result.all())

    return summary, meal_count


@router.get("/daily", response_model=DailySummaryResponse)
async def daily_summary(
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    summary, meal_count = await _get_daily_totals(db, current_user.id, date)
    return DailySummaryResponse(date=str(date), total=summary, meal_count=meal_count)


@router.get("/weekly", response_model=WeeklyTrendResponse)
async def weekly_trend(
    start: date = Query(..., description="Start date (YYYY-MM-DD), will show 7 days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    daily_entries = []
    total_sums = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}
    days_with_data = 0

    for i in range(7):
        d = start + timedelta(days=i)
        summary, meal_count = await _get_daily_totals(db, current_user.id, d)
        daily_entries.append(DailyEntry(date=str(d), total=summary, meal_count=meal_count))
        if meal_count > 0:
            days_with_data += 1
            for k in total_sums:
                total_sums[k] += getattr(summary, k)

    divisor = max(days_with_data, 1)
    average = NutrientSummary(**{k: round(v / divisor, 2) for k, v in total_sums.items()})

    return WeeklyTrendResponse(
        start_date=str(start),
        end_date=str(start + timedelta(days=6)),
        daily=daily_entries,
        average=average,
    )


@router.get("/balance", response_model=BalanceResponse)
async def nutrition_balance(
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    summary, _ = await _get_daily_totals(db, current_user.id, date)
    daily_rec = _get_personalized_daily(current_user)

    items = []
    for nutrient, recommended in daily_rec.items():
        actual = getattr(summary, nutrient)
        pct = round(actual / recommended * 100, 1) if recommended > 0 else 0.0

        if pct < 80:
            status = "low"
        elif pct > 120:
            status = "high"
        else:
            status = "ok"

        items.append(NutrientBalance(
            nutrient=nutrient,
            actual=actual,
            recommended=recommended,
            percentage=pct,
            status=status,
        ))

    return BalanceResponse(date=str(date), items=items)
