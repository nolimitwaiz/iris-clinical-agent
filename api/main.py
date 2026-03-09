"""FastAPI application for Iris Core."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.utils.data_loader import load_drug_database, load_alternatives

load_dotenv()

# Shared state loaded at startup
app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load drug database and alternatives at startup."""
    app_state["drug_db"] = load_drug_database()
    app_state["alternatives"] = load_alternatives()
    yield
    app_state.clear()


app = FastAPI(
    title="Iris Core API",
    description="Heart failure care agent API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
from api.routes.patients import router as patients_router
from api.routes.chat import router as chat_router
from api.routes.voice_ws import router as voice_ws_router

app.include_router(patients_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(voice_ws_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    has_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "status": "ok",
        "gemini_configured": has_key,
        "drugs_loaded": len(app_state.get("drug_db", [])),
        "alternatives_loaded": len(app_state.get("alternatives", [])),
    }
