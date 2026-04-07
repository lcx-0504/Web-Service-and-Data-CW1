from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    fdc_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meal_items: Mapped[list["MealItem"]] = relationship(back_populates="food")
