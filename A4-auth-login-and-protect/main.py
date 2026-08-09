import os

from dotenv import load_dotenv
from fastapi import FastAPI
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
