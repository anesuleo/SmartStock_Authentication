import os
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Pick the correct .env file based on the APP_ENV environment variable.
# Defaults to .env.dev if not set.
envfile = {
    "dev": ".env.dev",
    "docker": ".env.docker",
    "test": ".env.test",
}.get(os.getenv("APP_ENV", "dev"), ".env.dev")

load_dotenv(envfile, override=True)

# Read database connection URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
RETRIES = int(os.getenv("DB_RETRIES", "10"))
DELAY = float(os.getenv("DB_RETRY_DELAY", "1.5"))

# SQLite needs check_same_thread=False to work with FastAPI.
# Postgres doesn't need this so we only add it for SQLite.
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

# Retry loop — useful when the database container is still starting up
for _ in range(RETRIES):
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # checks connection is alive before using it
            echo=SQL_ECHO,       # logs all SQL statements when True
            connect_args=connect_args,
        )
        with engine.connect():   # smoke test to confirm connection works
            pass
        break
    except OperationalError:
        time.sleep(DELAY)

# SessionLocal is a factory for creating database sessions.
# Each request gets its own session via the get_db dependency.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Automatically closes the session when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()