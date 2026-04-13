import hashlib
import pytest
from datetime import datetime, timedelta
 
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from app.models import Base, UserDB, SessionDB
from app.database import get_db
from app.main import app
 
 
# ── Test database setup ───────────────────────────────────────────────────────
# We use a named in-memory SQLite database with shared cache so that
# both the test fixtures and the API's dependency override see the same data.
 
TEST_DB_URL = "sqlite:///file::memory:?cache=shared&uri=true"
 
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False, "uri": True},
)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
 
 
def override_get_db():
    """Replace the real database with the test database for all requests."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()
 
 
# Tell FastAPI to use the test database instead of the real one
app.dependency_overrides[get_db] = override_get_db
 
 
@pytest.fixture(autouse=True)
def reset_db():
    """
    Runs before and after every test.
    Creates all tables before the test and drops them after,
    so each test starts with a completely clean database.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
 
 
@pytest.fixture()
def db():
    """Provides a database session for directly inserting test data."""
    session = TestSession()
    yield session
    session.close()
 
 
@pytest.fixture()
def client():
    """Provides a TestClient for making requests to the API."""
    return TestClient(app)
 
 
def _hash(password: str) -> str:
    """Hash a password the same way the auth service does."""
    return hashlib.sha256(password.encode()).hexdigest()
 
 
def _make_user(db, username="alice", password="secret", role="staff", active=True):
    """Helper to insert a test user directly into the database."""
    user = UserDB(
        username=username,
        hashed_password=_hash(password),
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
 
 
# ── Login tests ───────────────────────────────────────────────────────────────
 
def test_login_success(client, db):
    """A valid username and password should return a token."""
    _make_user(db)
    res = client.post("/api/auth/login", json={"username": "alice", "password": "secret"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["username"] == "alice"
    assert data["role"] == "staff"
 
 
def test_login_wrong_password(client, db):
    """A correct username but wrong password should return 401."""
    _make_user(db)
    res = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert res.status_code == 401
 
 
def test_login_unknown_user(client, db):
    """A username that doesn't exist should return 401."""
    res = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert res.status_code == 401
 
 
def test_login_disabled_account(client, db):
    """A disabled account should return 403 even with correct credentials."""
    _make_user(db, active=False)
    res = client.post("/api/auth/login", json={"username": "alice", "password": "secret"})
    assert res.status_code == 403
 
 
# ── /me tests ─────────────────────────────────────────────────────────────────
 
def test_me_valid_token(client, db):
    """A valid token should return the current user's info."""
    _make_user(db)
    token = client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret"}
    ).json()["token"]
 
    res = client.get("/api/auth/me", params={"token": token})
    assert res.status_code == 200
    assert res.json()["username"] == "alice"
 
 
def test_me_invalid_token(client):
    """A made-up token should return 401."""
    res = client.get("/api/auth/me", params={"token": "fake-token"})
    assert res.status_code == 401
 
 
def test_me_expired_token(client, db):
    """An expired token should return 401 and be deleted from the database."""
    user = _make_user(db)
 
    # Insert an already-expired session directly into the database
    expired = SessionDB(
        token="expired-token-xyz",
        user_id=user.id,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db.add(expired)
    db.commit()
 
    res = client.get("/api/auth/me", params={"token": "expired-token-xyz"})
    assert res.status_code == 401
 
 
# ── Logout tests ──────────────────────────────────────────────────────────────
 
def test_logout_invalidates_token(client, db):
    """After logging out, the token should no longer be valid."""
    _make_user(db)
    token = client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret"}
    ).json()["token"]
 
    # Log out
    res = client.post("/api/auth/logout", params={"token": token})
    assert res.status_code == 204
 
    # Token should now be rejected
    res = client.get("/api/auth/me", params={"token": token})
    assert res.status_code == 401