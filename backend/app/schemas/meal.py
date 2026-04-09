import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.food import FoodResponse


class MealItemCreate(BaseModel):
    food_id: int
    quantity: float = Field(..., gt=0, le=10000, description="Quantity in grams (0-10000)")


class MealItemResponse(BaseModel):
    id: int
    food_id: int
    quantity: float
    food: FoodResponse

    model_config = {"from_attributes": True}


class MealCreate(BaseModel):
    date: dt.date
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    notes: Optional[str] = None
    items: list[MealItemCreate] = Field(..., min_length=1, description="At least one food item required")

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, v: dt.date) -> dt.date:
        if v > dt.date.today():
            raise ValueError("Cannot log meals for future dates")
        return v


class MealUpdate(BaseModel):
    date: Optional[dt.date] = None
    meal_type: Optional[Literal["breakfast", "lunch", "dinner", "snack"]] = None
    notes: Optional[str] = None
    items: Optional[list[MealItemCreate]] = None

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, v: Optional[dt.date]) -> Optional[dt.date]:
        if v is not None and v > dt.date.today():
            raise ValueError("Cannot log meals for future dates")
        return v

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: Optional[list[MealItemCreate]]) -> Optional[list[MealItemCreate]]:
        if v is not None and len(v) == 0:
            raise ValueError("Items list cannot be empty when provided")
        return v


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
