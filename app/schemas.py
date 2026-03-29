from datetime import datetime
from pydantic import BaseModel


# ── Request schemas ───────────────────────────────────────────────────────────
# These define what the client must send in the request body.
# FastAPI automatically validates incoming data against these models.

class LoginRequest(BaseModel):
    """Payload the client sends when attempting to log in."""
    username: str
    password: str


# ── Response schemas ──────────────────────────────────────────────────────────
# These define what the server sends back.
# FastAPI uses these to serialise the response and filter out unwanted fields.

class LoginResponse(BaseModel):
    """Returned to the client after a successful login."""
    token: str        # session token the client must include in future requests
    username: str
    role: str
    expires_at: datetime


class UserResponse(BaseModel):
    """Returned by the /me endpoint to identify the current user."""
    username: str
    role: str