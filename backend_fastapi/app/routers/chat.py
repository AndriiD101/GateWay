"""
Chat history endpoints (MySQL-backed).

Routes
------
GET    /api/chat/history         – Get own chat history     [JWT]
POST   /api/chat/message         – Save a chat message      [JWT]
DELETE /api/chat/history         – Clear own chat history   [JWT]
GET    /api/chat/history/{user_id} – Admin: view user chat  [JWT, admin]
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, require_admin
from app.mysql_db import get_mysql_connection
from app.schemas import ChatMessageCreate

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _db_error():
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No connection to the database. Please try again later.",
    )


@router.get("/history")
def get_chat_history(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's chat history (max 100 messages)."""
    user_id = current_user["user_id"]

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, role, message, created_at "
                "FROM chat_messages WHERE user_id = %s "
                "ORDER BY created_at ASC LIMIT 100",
                (user_id,),
            )
            rows = cur.fetchall()
        # Convert datetime objects to ISO strings for JSON serialisation
        for row in rows:
            if hasattr(row.get("created_at"), "isoformat"):
                row["created_at"] = row["created_at"].isoformat()
        return rows
    finally:
        conn.close()


@router.post("/message", status_code=status.HTTP_201_CREATED)
def save_chat_message(body: ChatMessageCreate, current_user: dict = Depends(get_current_user)):
    """Persist a single chat message for the authenticated user."""
    user_id = current_user["user_id"]

    if body.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'.")

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages (user_id, role, message) VALUES (%s, %s, %s)",
                (user_id, body.role, body.message.strip()),
            )
        conn.commit()
        return {"message": "Saved"}
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


@router.delete("/history", status_code=status.HTTP_200_OK)
def clear_chat_history(current_user: dict = Depends(get_current_user)):
    """Delete all chat messages for the authenticated user."""
    user_id = current_user["user_id"]

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"message": "Chat history cleared."}
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


@router.get("/history/{user_id}")
def get_user_chat_history(user_id: int, _admin: dict = Depends(require_admin)):
    """Admin: view any user's chat history."""
    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, role, message, created_at "
                "FROM chat_messages WHERE user_id = %s "
                "ORDER BY created_at ASC LIMIT 500",
                (user_id,),
            )
            rows = cur.fetchall()
        for row in rows:
            if hasattr(row.get("created_at"), "isoformat"):
                row["created_at"] = row["created_at"].isoformat()
        return rows
    finally:
        conn.close()
