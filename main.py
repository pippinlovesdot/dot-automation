"""
Twitter Bot with Auto-posting and Mention Handling.

FastAPI application with APScheduler for scheduled posts and mention responses.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings
from services.database import Database
from services.autopost import AutoPostService
from services.mentions import MentionHandler

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
mention_handler: MentionHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global autopost_service, mention_handler

    # Startup
    logger.info("Starting application...")

    # Connect to database
    await db.connect()
    logger.info("Database connected")

    # Initialize services
    autopost_service = AutoPostService(db)
    mention_handler = MentionHandler(db)

    # Schedule autopost job
    scheduler.add_job(
        autopost_service.run,
        "interval",
        minutes=settings.post_interval_minutes,
        id="autopost_job",
        replace_existing=True
    )

    # Schedule mentions job (every 20 minutes)
    scheduler.add_job(
        run_mentions_job,
        "interval",
        minutes=settings.mentions_interval_minutes,
        id="mentions_job",
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started: autopost every {settings.post_interval_minutes} min, mentions every {settings.mentions_interval_minutes} min")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    scheduler.shutdown(wait=False)
    await db.close()
    logger.info("Application shutdown complete")


async def run_mentions_job():
    """Scheduled job to process mentions."""
    if mention_handler is None:
        logger.warning("Mention handler not initialized")
        return

    try:
        logger.info("Running scheduled mentions check...")
        result = await mention_handler.process_mentions_batch()
        logger.info(f"Mentions job result: {result}")
    except Exception as e:
        logger.error(f"Error in mentions job: {e}")


app = FastAPI(
    title="Twitter Bot",
    description="Auto-posting Twitter bot with mention handling",
    version="1.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scheduler_running": scheduler.running,
        "version": "1.1.0"
    }


@app.get("/callback")
async def oauth_callback(oauth_token: str = None, oauth_verifier: str = None):
    """
    OAuth callback endpoint for Twitter authentication.

    Required for Twitter API Read+Write access.
    """
    return {
        "status": "ok",
        "message": "OAuth callback received",
        "oauth_token": oauth_token,
        "oauth_verifier": oauth_verifier
    }


@app.post("/trigger-post")
async def trigger_post():
    """Manually trigger an autopost."""
    if autopost_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        await autopost_service.run()
        return {"status": "posted"}
    except Exception as e:
        logger.error(f"Error triggering post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger-mentions")
async def trigger_mentions():
    """Manually trigger mentions processing."""
    if mention_handler is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = await mention_handler.process_mentions_batch()
        return result
    except Exception as e:
        logger.error(f"Error processing mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
