from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.food import Food
from app.schemas.food import FoodResponse, FoodListResponse

router = APIRouter(prefix="/api/foods", tags=["Foods"])


@router.get("/", response_model=FoodListResponse)
async def list_foods(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Food)
    count_query = select(func.count(Food.id))

    if category:
        query = query.where(Food.category == category)
        count_query = count_query.where(Food.category == category)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Food.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    foods = result.scalars().all()

    return FoodListResponse(items=foods, total=total, page=page, per_page=per_page)


@router.get("/search", response_model=FoodListResponse)
async def search_foods(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q}%"
    query = select(Food).where(Food.name.ilike(pattern))
    count_query = select(func.count(Food.id)).where(Food.name.ilike(pattern))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Food.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    foods = result.scalars().all()

    return FoodListResponse(items=foods, total=total, page=page, per_page=per_page)


@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(food_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Food).where(Food.id == food_id))
    food = result.scalar_one_or_none()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food
