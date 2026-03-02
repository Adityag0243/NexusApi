import jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config import settings
from src.database import get_db 
from src.models.models import User

cookie_sec = APIKeyCookie(name="access_token", auto_error=False)

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Extracts and validates JWT from either Cookies or Headers, and fetches user."""
    # 1. Try Cookie
    token = request.cookies.get("access_token")
    
    # 2. Try Header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Missing authentication token in both cookies and headers."
            )

    # 3. Clean string
    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "").strip()

        # 4. Decode
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        
        user_stmt = select(User).where(User.id == user_id)
        result = await db.execute(user_stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found or deleted")
            
        request.state.user_id = str(user.id)
        request.state.organisation_id = str(user.organisation_id)
            
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except Exception as e:
        # Catch any other JWT decode errors (invalid token, bad signature, etc.)
        # so it doesn't crash the server with a 500 error
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def require_role(required_role: str):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role} role"
            )
        return current_user
    return role_checker
