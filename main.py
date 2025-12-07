"""
Twitter Bot with Auto-posting and Mention Handling.

FastAPI application with APScheduler for scheduled posts.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings
from services.database import Database
from services.autopost import AutoPostService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
db = Database()
scheduler = AsyncIOScheduler()
autopost_service: AutoPostService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global autopost_service

    # Startup
    logger.info("Starting application...")

    # Connect to database
    await db.connect()
    logger.info("Database connected")

    # Initialize services
    autopost_service = AutoPostService(db)

    # Schedule autopost job
    scheduler.add_job(
        autopost_service.run,
        "interval",
        minutes=settings.post_interval_minutes,
        id="autopost_job",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Scheduler started, posting every {settings.post_interval_minutes} minutes")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    scheduler.shutdown(wait=False)
    await db.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Twitter Bot",
    description="Auto-posting Twitter bot with mention handling",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "scheduler_running": scheduler.running}


@app.get("/callback")
async def oauth_callback(oauth_token: str = None, oauth_verifier: str = None):
    """
    OAuth callback endpoint for Twitter authentication.

    Required for Twitter API Read+Write access.
    This is called after user authorizes the app.
    """
    # For a bot that uses its own credentials, this just needs to exist
    # The actual auth is done via Access Token in .env
    return {
        "status": "ok",
        "message": "OAuth callback received",
        "oauth_token": oauth_token,
        "oauth_verifier": oauth_verifier
    }


@app.post("/trigger-post")
async def trigger_post():
    """Manually trigger an autopost (for testing)."""
    if autopost_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        await autopost_service.run()
        return {"status": "posted"}
    except Exception as e:
        logger.error(f"Error triggering post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
