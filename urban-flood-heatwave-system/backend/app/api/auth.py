"""Simple JWT auth endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.config import settings
import jwt

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


DEMO_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "resident": {"password": "resident123", "role": "resident"},
}


@router.post("/token")
async def login(req: LoginRequest):
    user = DEMO_USERS.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(401, "Invalid credentials")

    payload = {
        "sub": req.username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}
