import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="Task Auth API",
    description="A secure API with Supabase Auth: sign up, log in, log out, and protected routes.",
    version="1.0",
)

security = HTTPBearer(auto_error=False)

login_attempts = {}


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    """The API promises 400 for missing/empty fields, not FastAPI's default 422."""
    return JSONResponse(
        status_code=400,
        content={"error": "email and password are required"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Keep error responses in the assignment's flat {"error": ...} shape."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
    else:
        content = {"error": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content)


class AuthIn(BaseModel):
    email: str = Field(min_length=1, description="User email, must not be empty")
    password: str = Field(min_length=1, description="Password, must not be empty")


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """Reusable guard: verify the bearer token with Supabase and return the user."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail={"error": "Access token required"})
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(status_code=401, detail={"error": "Access token required"})
    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=401, detail={"error": "Invalid or expired token"}
        )
    return result.user


def require_admin(user=Depends(require_user)):
    """Guard for admin-only routes. 401 if unknown, 403 if known but not admin."""
    if user.app_metadata.get("role") != "admin":
        raise HTTPException(status_code=403, detail={"error": "Admin access required"})
    return user


@app.get("/")
async def root():
    """Describe the API and list its endpoints."""
    return {
        "name": "Task Auth API",
        "version": "1.0",
        "endpoints": [
            "POST /auth/signup",
            "POST /auth/login",
            "POST /auth/logout",
            "GET /protected/profile",
            "GET /public/info",
        ],
    }


@app.post("/auth/signup", status_code=201)
async def signup(auth_in: AuthIn):
    """Create a new user account via Supabase. The server never sees the password."""
    try:
        result = supabase.auth.sign_up(
            {"email": auth_in.email, "password": auth_in.password}
        )
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Signup failed, check the email and try again"},
        )
    user = result.user
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.post("/auth/login")
async def login(auth_in: AuthIn):
    """Authenticate with Supabase and return the JWT access token plus refresh token."""
    now = int(time.time())
    window = login_attempts.setdefault(auth_in.email, [0, 0.0])
    if window[0] >= 5 and now - window[1] < 60:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many login attempts, try again later"},
        )
    window[0] += 1
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": auth_in.email, "password": auth_in.password}
        )
    except Exception:
        window[1] = now
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"},
        )
    window[0] = 0
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
        "expires_in": result.session.expires_in,
    }


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, description="Refresh token from login")


@app.post("/auth/refresh")
async def refresh(refresh_in: RefreshIn):
    """Exchange a refresh token for a fresh access token without logging in again."""
    try:
        result = supabase.auth.refresh_session(refresh_in.refresh_token)
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid refresh token"},
        )
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
        "expires_in": result.session.expires_in,
    }


@app.get("/public/info")
async def public_info():
    """Open, public data. No auth required."""
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
async def protected_profile(user=Depends(require_user)):
    """Locked door. The guard already verified the token; this just shapes the reply."""
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/protected/dashboard")
async def protected_dashboard(user=Depends(require_user)):
    """Second protected route reusing the same guard - no new auth code."""
    return {"message": f"Welcome back, {user.email}! This is your dashboard."}


@app.get("/protected/admin")
async def protected_admin(user=Depends(require_admin)):
    """Admin-only route. A logged-in non-admin gets 403, not 401."""
    return {"message": f"Admin panel for {user.email}"}


@app.post("/auth/logout", status_code=204)
async def logout(user=Depends(require_user)):
    """End the user's session. Protected by the same guard."""
    supabase.auth.sign_out()
    return None
