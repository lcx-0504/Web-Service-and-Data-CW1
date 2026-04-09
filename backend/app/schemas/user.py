from typing import Optional

from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    email: str
    password: str


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
    height: Optional[float] = None   # cm
    weight: Optional[float] = None   # kg
    age: Optional[int] = None
    gender: Optional[str] = None     # male / female
    activity_level: Optional[str] = None  # sedentary / light / moderate / active / very_active


class ProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None

    model_config = {"from_attributes": True}
