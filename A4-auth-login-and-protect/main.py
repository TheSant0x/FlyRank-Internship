import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi import Header
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
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


def require_user(authorization: str | None = Header(default=None)):
    """Reusable guard: verify the bearer token with Supabase and return the user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "Access token required"})
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail={"error": "Access token required"})
    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=401, detail={"error": "Invalid or expired token"}
        )
    return result.user


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
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": auth_in.email, "password": auth_in.password}
        )
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"},
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


@app.post("/auth/logout", status_code=204)
async def logout(user=Depends(require_user)):
    """End the user's session. Protected by the same guard."""
    supabase.auth.sign_out()
    return None
