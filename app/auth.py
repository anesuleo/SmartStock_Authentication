import secrets
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import get_db
from .models import UserDB, SessionDB
from .schemas import LoginRequest, LoginResponse, UserResponse

# All routes in this file will be prefixed with /api/auth
router = APIRouter(prefix="/api/auth", tags=["auth"])

# How long a session token stays valid after login
SESSION_TTL_HOURS = 8


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """
    Hash a plain-text password using SHA-256.
    Passwords are never stored or compared in plain text.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def _create_session(user: UserDB, db: Session) -> SessionDB:
    """
    Create a new session record for a user after a successful login.
    Generates a cryptographically secure random token and saves it to the database.
    """
    # secrets.token_hex gives us a secure random 64-character hex string
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
    Check that a token exists and has not expired.
    Raises 401 if invalid. Expired tokens are deleted automatically.
    """
    session = db.execute(
        select(SessionDB).where(SessionDB.token == token)
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )

    # Clean up and reject expired tokens
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired – please log in again",
        )

    return session


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user with username and password.
    Returns a session token on success.
    Returns 401 if credentials are wrong, 403 if the account is disabled.
    """
    # Look up the user by username
    user = db.execute(
        select(UserDB).where(UserDB.username == payload.username)
    ).scalar_one_or_none()

    # Check both user existence and password in one condition.
    # This avoids revealing whether the username or password was wrong
    # (prevents username enumeration attacks).
    if not user or user.hashed_password != _hash_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Reject disabled accounts
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # All checks passed — create and return a session
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
    Invalidate a session token by deleting it from the database.
    If the token doesn't exist we do nothing — already logged out.
    """
    session = db.execute(
        select(SessionDB).where(SessionDB.token == token)
    ).scalar_one_or_none()

    if session:
        db.delete(session)
        db.commit()


@router.get("/me", response_model=UserResponse)
def me(token: str, db: Session = Depends(get_db)):
    """
    Return the current user's info based on their session token.
    Used by the GUI to verify a session is still valid and get the username/role.
    """
    # Validate the token — raises 401 if invalid or expired
    session = _validate_token(token, db)

    # Fetch the user the session belongs to
    user = db.get(UserDB, session.user_id)
    return UserResponse(username=user.username, role=user.role)