import secrets
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import get_db
from .models import UserDB, SessionDB

# All routes in this file will be prefixed with /api/auth
router = APIRouter(prefix="/api/auth", tags=["auth"])

# How long a session stays valid after login
SESSION_TTL_HOURS = 8


# ── Schemas ───────────────────────────────────────────────────────────────────
# Pydantic models that define the shape of request and response bodies.
# FastAPI uses these to automatically validate incoming data and
# serialise outgoing data.

class LoginRequest(BaseModel):
    """What the client sends when logging in."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """What the server sends back on a successful login."""
    token: str       # the session token the client must include in future requests
    username: str
    role: str
    expires_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """
    Hash a plain-text password using SHA-256.
    Passwords are never stored or compared in plain text.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def _create_session(user: UserDB, db: Session) -> SessionDB:
    """
    Create a new session for a user after a successful login.
    Generates a cryptographically random token, sets an expiry time,
    saves it to the database, and returns the session object.
    """
    # secrets.token_hex gives us a secure random token (64 hex chars)
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)

    session = SessionDB(
        token=token,
        user_id=user.id,
        expires_at=expires,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _validate_token(token: str, db: Session) -> SessionDB:
    """
    Check that a token exists in the database and has not expired.
    Raises a 401 error if the token is invalid or expired.
    Expired tokens are deleted from the database automatically.
    """
    # Look up the session by token
    session = db.execute(
        select(SessionDB).where(SessionDB.token == token)
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )

    # If the token has passed its expiry time, clean it up and reject
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired – please log in again"
        )

    return session


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user with username and password.
    On success, creates a session and returns a token.
    Returns 401 if credentials are wrong, 403 if the account is disabled.
    """
    # Look up the user by username
    user = db.execute(
        select(UserDB).where(UserDB.username == payload.username)
    ).scalar_one_or_none()

    # Reject if user doesn't exist or password hash doesn't match.
    # We check both in one condition to avoid revealing which one failed
    # (prevents username enumeration attacks).
    if not user or user.hashed_password != _hash_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Reject if the account has been disabled by an admin
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Credentials are valid — create and return a session
    session = _create_session(user, db)
    return LoginResponse(
        token=session.token,
        username=user.username,
        role=user.role,
        expires_at=session.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str, db: Session = Depends(get_db)):
    """
    Invalidate a session token.
    Deletes the session from the database so the token can no longer be used.
    If the token doesn't exist, we do nothing (already logged out).
    """
    session = db.execute(
        select(SessionDB).where(SessionDB.token == token)
    ).scalar_one_or_none()

    if session:
        db.delete(session)
        db.commit()


@router.get("/me")
def me(token: str, db: Session = Depends(get_db)):
    """
    Return the currently logged-in user's info based on their session token.
    Used by the GUI to verify a session is still valid and get the username/role.
    """
    # Validate the token first — raises 401 if invalid or expired
    session = _validate_token(token, db)

    # Fetch the user the session belongs to
    user = db.get(UserDB, session.user_id)
    return {"username": user.username, "role": user.role}