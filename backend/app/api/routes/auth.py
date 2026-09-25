import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordRequestForm
from app.database.session import get_db
from app.database.models import User
from app.schemas.user import UserCreate, UserResponse
from app.auth.security import get_password_hash, verify_password, create_access_token, encrypt_token
from app.config import settings
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])
oauth_states: dict[str, float] = {}

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

import httpx
from fastapi.responses import RedirectResponse

@router.get("/github/login")
async def github_login():
    state = secrets.token_urlsafe(32)
    oauth_states[state] = __import__("time").time() + settings.GITHUB_OAUTH_STATE_TTL_SECONDS
    response = RedirectResponse(f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=repo%20user&state={state}")
    response.set_cookie("github_oauth_state", state, httponly=True, samesite="none", secure=settings.FRONTEND_URL.startswith("https"), max_age=settings.GITHUB_OAUTH_STATE_TTL_SECONDS)
    return response

@router.get("/github/callback")
async def github_callback(code: str, state: str, request: Request, db: AsyncSession = Depends(get_db)):
    expires_at = oauth_states.pop(state, 0)
    if not secrets.compare_digest(state, request.cookies.get("github_oauth_state", "")) or expires_at < __import__("time").time():
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    try:
      async with httpx.AsyncClient(timeout=10) as client:
        # Exchange code for access token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code
            }
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Could not authenticate with GitHub")
            
        # Get user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_response.raise_for_status()
        github_user = user_response.json()
        
        username = github_user.get("login")
        email = github_user.get("email") or f"{username}@users.noreply.github.com"
        
        # Check if user exists, if not create them
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        encrypted_token = encrypt_token(access_token)
        
        if not user:
            user = User(username=username, email=email, hashed_password="", github_access_token=encrypted_token)
            db.add(user)
        else:
            user.github_access_token = encrypted_token
            
        await db.commit()
        await db.refresh(user)
            
        # Generate JWT token
        jwt_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": user.username}, expires_delta=jwt_expires
        )
        
        response = RedirectResponse(f"{settings.FRONTEND_URL}/dashboard#token={jwt_token}")
        response.delete_cookie("github_oauth_state")
        return response
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="GitHub authentication is unavailable")
