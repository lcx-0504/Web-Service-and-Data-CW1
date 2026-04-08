from pydantic import BaseModel


class FoodResponse(BaseModel):
    id: int
    fdc_id: int | None
    name: str
    category: str
    calories: float
    protein: float
    fat: float
    carbs: float
    fiber: float

    model_config = {"from_attributes": True}


class FoodListResponse(BaseModel):
    items: list[FoodResponse]
    total: int
    page: int
    per_page: int
