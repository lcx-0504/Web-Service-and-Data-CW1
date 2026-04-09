from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$",
                          description="3-50 chars, letters/digits/underscore only")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128, description="At least 6 characters")


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    height: Optional[float] = Field(None, gt=0, le=300, description="Height in cm (1-300)")
    weight: Optional[float] = Field(None, gt=0, le=500, description="Weight in kg (1-500)")
    age: Optional[int] = Field(None, ge=1, le=130, description="Age in years (1-130)")
    gender: Optional[Literal["male", "female"]] = None
    activity_level: Optional[Literal["sedentary", "light", "moderate", "active", "very_active"]] = None


class ProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    warnings: list[str] = []

    model_config = {"from_attributes": True}
