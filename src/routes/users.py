from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.dependencies import get_current_user, cookie_sec
from src.models.models import User

router = APIRouter(tags=["Users"])

@router.get("/me")
async def read_users_me(
    auth_cookie: str = Depends(cookie_sec),        
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the profile of the currently authenticated user and their organisation.
    """
    # Fetch user with their organisation using selectinload
    stmt = select(User).options(selectinload(User.organisation)).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user_with_org = result.scalar_one()

    return {
        "id": str(user_with_org.id),
        "email": user_with_org.email,
        "name": user_with_org.name,
        "role": user_with_org.role,
        "organisation": {
            "id": str(user_with_org.organisation.id),
            "name": user_with_org.organisation.name,
            "slug": user_with_org.organisation.slug
        }
    }