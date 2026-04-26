"""
Auth & user-management endpoints backed by Azure SQL (SQLAlchemy).
"""

import bcrypt
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, require_admin
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, UpdateProfileRequest

router = APIRouter(prefix="/api", tags=["auth"])
logger = logging.getLogger(__name__)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _to_username(user: User) -> str:
    return (user.username or user.email or "").strip()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="Please fill in all fields.")

    try:
        existing = db.scalar(select(User).where(User.email == username))
        if existing is not None:
            raise HTTPException(status_code=409, detail="This username is already taken.")

        user = User(
            email=username,
            username=username,
            password_hash=_hash(body.password),
            role="user",
        )
        db.add(user)
        db.commit()
        return {"message": "Registration successful! You can now log in."}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Register failed due to database error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No connection to the database. Please try again later.",
        )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="Please fill in all fields.")

    try:
        user = db.scalar(select(User).where(User.email == username))
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Login failed due to database error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No connection to the database. Please try again later.",
        )

    if user is None or not _verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(
        {
            "sub": str(user.id),
            "user_id": user.id,
            "username": _to_username(user),
            "role": user.role or "user",
        }
    )
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        username=_to_username(user),
        role=user.role or "user",
    )


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = int(current_user["user_id"])
    try:
        user = db.get(User, user_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Get profile failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")

    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    return {"id": user.id, "username": _to_username(user), "role": user.role or "user"}


@router.put("/me")
def update_me(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["user_id"])
    if not body.username and not body.password:
        raise HTTPException(status_code=400, detail="Provide at least one field to update.")

    try:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        if body.username:
            new_username = body.username.strip()
            existing = db.scalar(select(User).where(User.email == new_username, User.id != user_id))
            if existing is not None:
                raise HTTPException(status_code=409, detail="Username already taken.")
            user.email = new_username
            user.username = new_username

        if body.password:
            user.password_hash = _hash(body.password)

        db.commit()
        return {"message": "Profile updated successfully."}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Update profile failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = int(current_user["user_id"])
    try:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        db.delete(user)
        db.commit()
        return {"message": "Account deleted."}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Delete account failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")


@router.get("/users")
def list_users(_admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        users = db.scalars(select(User).order_by(User.email.asc())).all()
        return [
            {"id": user.id, "username": _to_username(user), "role": user.role or "user"}
            for user in users
        ]
    except SQLAlchemyError:
        db.rollback()
        logger.exception("List users failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")


@router.get("/users/{user_id}")
def get_user(user_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if int(current_user["user_id"]) != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        user = db.get(User, user_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Get user failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")

    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    return {"id": user.id, "username": _to_username(user), "role": user.role or "user"}


@router.put("/users/{user_id}/role")
def change_role(user_id: int, body: dict, _admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    new_role = str(body.get("role", "")).strip()
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'.")

    try:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        user.role = new_role
        db.commit()
        return {"message": f"Role updated to '{new_role}'."}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Change role failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")


@router.delete("/users/{user_id}")
def delete_user(user_id: int, _admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        db.delete(user)
        db.commit()
        return {"message": "User deleted."}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Delete user failed due to database error")
        raise HTTPException(status_code=503, detail="No connection to the database. Please try again later.")
