from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from .models import Base
from .auth import router as auth_router


# Creates all database tables on startup if they don't already exist
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

# Allow requests from the GUI (running on a different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the auth router — all endpoints will be prefixed with /api/auth
app.include_router(auth_router)


@app.get("/health")
def health():
    """Simple health check to confirm the service is running."""
    return {"status": "ok"}