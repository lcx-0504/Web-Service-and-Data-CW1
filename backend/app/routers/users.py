from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import ProfileUpdate, ProfileResponse
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])


def _profile_warnings(user: User) -> list[str]:
    """Generate soft warnings for unusual but allowed profile values."""
    warnings = []
    if user.height is not None:
        if user.height < 50:
            warnings.append(f"Height {user.height} cm is unusually low. Please verify.")
        elif user.height > 250:
            warnings.append(f"Height {user.height} cm is unusually high. Please verify.")
    if user.weight is not None:
        if user.weight < 20:
            warnings.append(f"Weight {user.weight} kg is unusually low. Please verify.")
        elif user.weight > 300:
            warnings.append(f"Weight {user.weight} kg is unusually high. Please verify.")
    if user.age is not None:
        if user.age > 120:
            warnings.append(f"Age {user.age} is unusually high. Please verify.")
    return warnings


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    resp = ProfileResponse.model_validate(current_user)
    resp.warnings = _profile_warnings(current_user)
    return resp


@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    resp = ProfileResponse.model_validate(current_user)
    resp.warnings = _profile_warnings(current_user)
    return resp
