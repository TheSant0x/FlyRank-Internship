import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
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


class AuthIn(BaseModel):
    email: str = Field(min_length=1, description="User email, must not be empty")
    password: str = Field(min_length=1, description="Password, must not be empty")


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
