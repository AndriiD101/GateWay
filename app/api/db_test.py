from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/db", tags=["db-test"])


class TestUserCreate(BaseModel):
    email: EmailStr
    password_hash: str = "test_hash"


@router.get("/health")
def db_health(db: Session = Depends(get_db)) -> dict:
    try:
        value = db.execute(text("SELECT 1")).scalar_one()
        return {"status": "ok", "db": "connected", "result": value}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.post("/test-create-user")
def test_create_user(payload: TestUserCreate, db: Session = Depends(get_db)) -> dict:
    try:
        existing = db.scalar(select(User).where(User.email == payload.email))
        if existing is not None:
            raise HTTPException(status_code=409, detail="User already exists")

        user = User(email=payload.email, password_hash=payload.password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)

        return {"id": user.id, "email": user.email}
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.get("/test-users")
def test_users(db: Session = Depends(get_db)) -> list[dict]:
    try:
        users = db.scalars(select(User).order_by(User.id.asc())).all()
        return [{"id": user.id, "email": user.email} for user in users]
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database unavailable")
