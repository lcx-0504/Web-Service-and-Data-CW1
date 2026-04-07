from sqlalchemy import Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MealItem(Base):
    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey("meals.id", ondelete="CASCADE"))
    food_id: Mapped[int] = mapped_column(Integer, ForeignKey("foods.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[float] = mapped_column(Float)  # grams

    meal: Mapped["Meal"] = relationship(back_populates="items")
    food: Mapped["Food"] = relationship(back_populates="meal_items")
