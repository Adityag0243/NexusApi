from fastapi import APIRouter, Depends
from src.dependencies import get_current_user
from src.models.models import User

router = APIRouter(tags=["Users"])

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's profile and organisation.
    """
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "organisation_id": str(current_user.organisation_id),
        "role": current_user.role
    }