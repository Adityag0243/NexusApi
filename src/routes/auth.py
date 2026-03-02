import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models.models import User, Organisation
from src.config import settings
import jwt
from datetime import datetime, timedelta
import urllib.parse
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/google")
async def login_google():
    """
    Redirects the user to Google login.
    """
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    # This physically redirects the browser
    return RedirectResponse(url=google_auth_url)

@router.get("/callback")
async def auth_callback(code: str, db: AsyncSession = Depends(get_db)):
    # 1. Exchange 'code' for access token from Google
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Google authentication failed") 
        
        google_data = token_res.json()
        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_data['access_token']}"}
        )
        user_info = user_info_res.json()

    email = user_info["email"]
    name = user_info.get("name")
    google_id = user_info["sub"]
    domain = email.split("@")[-1]

    # 2. Multi-tenant Logic 
    # Check if an organization for this email domain already exists
    org_stmt = select(Organisation).where(Organisation.slug == domain)
    result = await db.execute(org_stmt)
    org = result.scalar_one_or_none()

    role = "member"
    if not org:
        # Create new org and make first user an admin 
        org = Organisation(name=domain.capitalize(), slug=domain)
        db.add(org)
        await db.flush() # Get the org ID
        role = "admin"
    
    # 3. Create or Update User [cite: 59]
    user_stmt = select(User).where(User.email == email)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            name=name,
            google_id=google_id,
            organisation_id=org.id,
            role=role
        )
        db.add(user)
    
    await db.commit()

    # 4. Generate signed JWT 
    payload = {
        "user_id": str(user.id),
        "organisation_id": str(org.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    
    redirect_url = "http://localhost:8000/docs" if "localhost" in settings.GOOGLE_REDIRECT_URI else "https://nexusapi-2m3c.onrender.com/docs"
    print(redirect_url)
    response = RedirectResponse(url=redirect_url) 
    print(response)
    is_production = "localhost" not in settings.GOOGLE_REDIRECT_URI
    print(is_production)


    print("token : ", token)

    response.set_cookie(
        key="access_token", 
        value=f"Bearer {token}", 
        httponly=True,   
        secure=is_production,     
        samesite="lax",   
        max_age=3600     
    )

    return response