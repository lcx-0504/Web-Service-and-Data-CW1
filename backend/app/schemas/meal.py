import datetime as dt
from typing import Optional

from pydantic import BaseModel

from app.schemas.food import FoodResponse


class MealItemCreate(BaseModel):
    food_id: int
    quantity: float  # grams


class MealItemResponse(BaseModel):
    id: int
    food_id: int
    quantity: float
    food: FoodResponse

    model_config = {"from_attributes": True}


class MealCreate(BaseModel):
    date: dt.date
    meal_type: str  # breakfast/lunch/dinner/snack
    notes: Optional[str] = None
    items: list[MealItemCreate] = []


class MealUpdate(BaseModel):
    date: Optional[dt.date] = None
    meal_type: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[list[MealItemCreate]] = None


class MealResponse(BaseModel):
    id: int
    user_id: int
    date: dt.date
    meal_type: str
    notes: Optional[str]
    items: list[MealItemResponse]

    model_config = {"from_attributes": True}


class MealListResponse(BaseModel):
    items: list[MealResponse]
    total: int
