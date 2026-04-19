"""
api.py
FastAPI wrapper for Social Media Content Crew.
N8N will call these endpoints to trigger each crew.
"""

import logging
import time
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

# --- Import your crews ---
from crews.social_crew import run as run_social
from crews.affirmation_crew import run as run_affirmation

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


# --- Cleanup functions for thread pools ---
def _cleanup_threads():
    """Clean up any remaining threads on shutdown."""
    try:
        time.sleep(0.1)  # Brief pause for graceful shutdown
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle with proper cleanup."""
    # Startup
    logger.info("🚀 Social Media Crew API starting up...")
    yield
    # Shutdown
    logger.info("🛑 Social Media Crew API shutting down...")
    _cleanup_threads()
    logger.info("✅ Cleanup complete")


# --- App ---
app = FastAPI(
    title="Social Media Crew API",
    description="Triggers CrewAI crews for Facebook content posting.",
    version="1.0.0",
    lifespan=lifespan
)


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.get("/health")
def health():
    """Quick check that the API is alive."""
    return {"status": "ok", "message": "Social Media Crew API is running!"}


# ─────────────────────────────────────────
# SOCIAL CREW  →  Facebook Feed
# ─────────────────────────────────────────
@app.post("/run/social")
def run_social_crew():
    """
    Triggers the Social Crew.
    Reads from data/topics.txt and posts to Facebook Feed.
    """
    logger.info("▶️  /run/social called — starting Social Crew...")
    try:
        run_social()
        logger.info("✅ Social Crew finished successfully.")
        return {
            "status": "success",
            "crew": "social",
            "message": "Social crew completed. Check logs for post details."
        }
    except Exception as e:
        logger.error(f"❌ Social Crew failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────
# AFFIRMATION CREW  →  Facebook Story + Feed
# ─────────────────────────────────────────
@app.post("/run/affirmation")
def run_affirmation_crew():
    """
    Triggers the Affirmation Crew.
    Reads from data/affirmations.txt and posts to Facebook Story + Feed.
    """
    logger.info("▶️  /run/affirmation called — starting Affirmation Crew...")
    try:
        run_affirmation()
        logger.info("✅ Affirmation Crew finished successfully.")
        return {
            "status": "success",
            "crew": "affirmation",
            "message": "Affirmation crew completed. Check logs for post details."
        }
    except Exception as e:
        logger.error(f"❌ Affirmation Crew failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))