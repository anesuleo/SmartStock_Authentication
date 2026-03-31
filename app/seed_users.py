"""
app/seed_users.py
 
Creates default user accounts on first run.
Run this once after the database is created:
    python -m app.seed_users
 
Default accounts:
    admin / admin123  (role: admin)
    staff / staff123  (role: staff)
 
Change these passwords in any real environment!
"""
 
import hashlib
import sys
import os
 
# Allow running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
 
from app.database import SessionLocal, engine
from app.models import Base, UserDB
 
 
def _hash(password: str) -> str:
    """Hash a plain-text password using SHA-256 before storing it."""
    return hashlib.sha256(password.encode()).hexdigest()
 
 
# Default users to create on first run
DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "staff", "password": "staff123", "role": "staff"},
]
 
 
def seed_users():
    # Create all tables if they don't exist yet
    Base.metadata.create_all(bind=engine)
 
    db = SessionLocal()
    created = 0
 
    for u in DEFAULT_USERS:
        # Skip if the user already exists — safe to run multiple times
        exists = db.query(UserDB).filter_by(username=u["username"]).first()
        if not exists:
            db.add(UserDB(
                username=u["username"],
                hashed_password=_hash(u["password"]),
                role=u["role"],
                is_active=True,
            ))
            created += 1
            print(f"  Created user: {u['username']} ({u['role']})")
        else:
            print(f"  Skipped (already exists): {u['username']}")
 
    db.commit()
    db.close()
    print(f"\nDone. {created} user(s) created.")
 
 
if __name__ == "__main__":
    seed_users()