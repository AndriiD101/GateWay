"""
Auth & user-management endpoints (MySQL-backed).

Routes
------
POST  /api/register              – Register a new account
POST  /api/login                 – Login, get JWT
GET   /api/me                    – Get own profile          [JWT]
PUT   /api/me                    – Update username/password [JWT]
DELETE /api/me                   – Delete own account       [JWT]
GET   /api/users                 – List all users           [JWT, admin]
GET   /api/users/{user_id}       – Get single user          [JWT, self or admin]
PUT   /api/users/{user_id}/role  – Change role              [JWT, admin]
DELETE /api/users/{user_id}      – Delete user              [JWT, admin]
"""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import create_access_token, get_current_user, require_admin
from app.mysql_db import get_mysql_connection
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, UpdateProfileRequest

router = APIRouter(prefix="/api", tags=["auth"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _db_error():
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No connection to the database. Please try again later.",
    )


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── register ──────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="Please fill in all fields.")

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="This username is already taken.")

            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'user')",
                (username, _hash(body.password)),
            )
        conn.commit()
        return {"message": "Registration successful! You can now log in."}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


# ── login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="Please fill in all fields.")

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = %s",
                (username,),
            )
            user = cur.fetchone()

        if not user or not _verify(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        token = create_access_token(
            {
                "sub": str(user["id"]),
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
            }
        )
        return LoginResponse(
            access_token=token,
            user_id=user["id"],
            username=user["username"],
            role=user["role"],
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


# ── own profile ───────────────────────────────────────────────────────────────

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user
    finally:
        conn.close()


@router.put("/me")
def update_me(body: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    """Update own username and/or password."""
    user_id = current_user["user_id"]
    if not body.username and not body.password:
        raise HTTPException(status_code=400, detail="Provide at least one field to update.")

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            if body.username:
                cur.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (body.username.strip(), user_id),
                )
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Username already taken.")
                cur.execute(
                    "UPDATE users SET username = %s WHERE id = %s",
                    (body.username.strip(), user_id),
                )
            if body.password:
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (_hash(body.password), user_id),
                )
        conn.commit()
        return {"message": "Profile updated successfully."}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_me(current_user: dict = Depends(get_current_user)):
    """Delete own account and all associated chat history."""
    user_id = current_user["user_id"]

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return {"message": "Account deleted."}
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


# ── admin: user directory ─────────────────────────────────────────────────────

@router.get("/users")
def list_users(_admin: dict = Depends(require_admin)):
    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users ORDER BY username")
            return cur.fetchall()
    finally:
        conn.close()


@router.get("/users/{user_id}")
def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user
    finally:
        conn.close()


@router.put("/users/{user_id}/role")
def change_role(user_id: int, body: dict, _admin: dict = Depends(require_admin)):
    """Change a user's role (admin only). Body: {"role": "admin"|"user"}"""
    new_role = body.get("role", "").strip()
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'.")

    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found.")
        conn.commit()
        return {"message": f"Role updated to '{new_role}'."}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()


@router.delete("/users/{user_id}")
def delete_user(user_id: int, _admin: dict = Depends(require_admin)):
    """Delete a user and their chat history (admin only)."""
    try:
        conn = get_mysql_connection()
    except Exception:
        _db_error()

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found.")
        conn.commit()
        return {"message": "User deleted."}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error.")
    finally:
        conn.close()
