
from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone

from app.database import db
from app.schemas.user import UserRegister, UserLogin
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister):

    email = user.email.strip().lower()

    existing_user = db.users.find_one({
        "email": email
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = {
        "name": user.name.strip(),
        "email": email,
        "password": hash_password(user.password),
        "role": "citizen",
        "created_at": datetime.now(timezone.utc)
    }

    try:
        result = db.users.insert_one(new_user)

    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    return {
        "message": "Registration successful",
        "user_id": str(result.inserted_id),
        "name": new_user["name"],
        "email": email,
        "role": "citizen"
    }


@router.post("/login")
def login(user: UserLogin):

    email = user.email.strip().lower()

    existing_user = db.users.find_one({
        "email": email
    })

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user.password,
        existing_user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    role = existing_user.get("role", "citizen")

    token = create_access_token({
        "sub": str(existing_user["_id"]),
        "role": role
    })

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(existing_user["_id"]),
            "name": existing_user["name"],
            "email": existing_user["email"],
            "role": role
        }
    }
