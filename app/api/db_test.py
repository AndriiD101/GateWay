from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/db", tags=["db-test"])


class TestUserCreate(BaseModel):
    email: EmailStr
    password_hash: str = "test_hash"


@router.get("/health")
def db_health(db: Session = Depends(get_db)) -> dict:
    value = db.execute(text("SELECT 1")).scalar_one()
    return {"status": "ok", "db": "connected", "result": value}


@router.post("/test-create-user")
def test_create_user(payload: TestUserCreate, db: Session = Depends(get_db)) -> dict:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(email=payload.email, password_hash=payload.password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email}


@router.get("/test-users")
def test_users(db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User).order_by(User.id.asc())).all()
    return [{"id": user.id, "email": user.email} for user in users]
