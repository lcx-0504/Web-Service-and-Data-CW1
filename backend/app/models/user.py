from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(128))

    # Personal info for personalized nutrition calculation
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # cm
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # kg
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # male / female
    activity_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # sedentary / light / moderate / active / very_active

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meals: Mapped[list["Meal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
