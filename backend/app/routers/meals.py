from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.user import User
from app.models.meal import Meal
from app.models.meal_item import MealItem
from app.models.food import Food
from app.schemas.meal import MealCreate, MealUpdate, MealResponse, MealListResponse
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/meals", tags=["Meals"])


def _meal_query_with_items():
    return select(Meal).options(selectinload(Meal.items).selectinload(MealItem.food))


@router.get("/", response_model=MealListResponse)
def list_meals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count_result = db.execute(
        select(func.count(Meal.id)).where(Meal.user_id == current_user.id)
    )
    total = count_result.scalar()

    query = (
        _meal_query_with_items()
        .where(Meal.user_id == current_user.id)
        .order_by(Meal.date.desc(), Meal.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = db.execute(query)
    meals = result.scalars().unique().all()

    return MealListResponse(items=meals, total=total)


@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        _meal_query_with_items().where(Meal.id == meal_id, Meal.user_id == current_user.id)
    )
    meal = result.scalar_one_or_none()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


@router.post("/", response_model=MealResponse, status_code=201)
def create_meal(
    data: MealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate all food_ids exist
    if data.items:
        food_ids = [item.food_id for item in data.items]
        result = db.execute(select(func.count(Food.id)).where(Food.id.in_(food_ids)))
        if result.scalar() != len(set(food_ids)):
            raise HTTPException(status_code=400, detail="One or more food_id not found")

    meal = Meal(
        user_id=current_user.id,
        date=data.date,
        meal_type=data.meal_type,
        notes=data.notes,
    )
    db.add(meal)
    db.flush()  # get meal.id

    for item in data.items:
        db.add(MealItem(meal_id=meal.id, food_id=item.food_id, quantity=item.quantity))

    db.commit()

    # Re-fetch with items loaded
    result = db.execute(_meal_query_with_items().where(Meal.id == meal.id))
    return result.scalar_one()


@router.put("/{meal_id}", response_model=MealResponse)
def update_meal(
    meal_id: int,
    data: MealUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        _meal_query_with_items().where(Meal.id == meal_id, Meal.user_id == current_user.id)
    )
    meal = result.scalar_one_or_none()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    if data.date is not None:
        meal.date = data.date
    if data.meal_type is not None:
        meal.meal_type = data.meal_type
    if data.notes is not None:
        meal.notes = data.notes

    if data.items is not None:
        # Validate food_ids
        food_ids = [item.food_id for item in data.items]
        if food_ids:
            result = db.execute(select(func.count(Food.id)).where(Food.id.in_(food_ids)))
            if result.scalar() != len(set(food_ids)):
                raise HTTPException(status_code=400, detail="One or more food_id not found")

        # Replace items: delete old, add new
        for old_item in meal.items:
            db.delete(old_item)
        db.flush()

        for item in data.items:
            db.add(MealItem(meal_id=meal.id, food_id=item.food_id, quantity=item.quantity))

    db.commit()

    # Re-fetch
    result = db.execute(_meal_query_with_items().where(Meal.id == meal.id))
    return result.scalar_one()


@router.delete("/{meal_id}", status_code=204)
def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Meal).where(Meal.id == meal_id, Meal.user_id == current_user.id)
    )
    meal = result.scalar_one_or_none()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    db.delete(meal)
    db.commit()
