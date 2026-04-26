"""
Chat history endpoints backed by Azure SQL (SQLAlchemy).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import ChatMessage
from app.schemas import ChatMessageCreate

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/history")
def get_chat_history(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = int(current_user["user_id"])

    try:
        messages = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc())
        ).all()
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages[-100:]
        ]
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No connection to the database. Please try again later.",
        )


@router.post("/message", status_code=status.HTTP_201_CREATED)
def save_chat_message(
    body: ChatMessageCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["user_id"])

    if body.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'.")

    try:
        msg = ChatMessage(user_id=user_id, role=body.role, message=body.message.strip())
        db.add(msg)
        db.commit()
        return {"message": "Saved"}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Server error.")


@router.delete("/history", status_code=status.HTTP_200_OK)
def clear_chat_history(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = int(current_user["user_id"])

    try:
        messages = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user_id)).all()
        for msg in messages:
            db.delete(msg)
        db.commit()
        return {"message": "Chat history cleared."}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Server error.")


@router.get("/history/{user_id}")
def get_user_chat_history(user_id: int, _admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        messages = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc())
        ).all()
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages[-500:]
        ]
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No connection to the database. Please try again later.",
        )
