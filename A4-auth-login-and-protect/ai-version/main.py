"""AI-generated Supabase auth API (quarantined for review)."""

import os

from fastapi import FastAPI, HTTPException, Request
from supabase import create_client

app = FastAPI()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_KEY", "sb_publishable_key_placeholder"),
)


@app.post("/auth/signup", status_code=201)
async def signup(request: Request):
    body = await request.json()
    email = body.get("email")
    password = body.get("password")
    result = supabase.auth.sign_up({"email": email, "password": password})
    return {"user": result.user.email}


@app.post("/auth/login")
async def login(request: Request):
    body = await request.json()
    result = supabase.auth.sign_in_with_password(
        {"email": body.get("email"), "password": body.get("password")}
    )
    return {"access_token": result.session.access_token}


@app.get("/public/info")
async def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
async def profile(request: Request):
    auth = request.headers.get("authorization", "")
    token = auth.split(" ")[1] if " " in auth else auth
    user = supabase.auth.get_user(token).user
    return {"id": user.id, "email": user.email}
