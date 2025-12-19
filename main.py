"""
Twitter Agent Bot - Auto-posting and Mention Handling.

FastAPI application with APScheduler for scheduled posts.
Version 1.3.2 - Improved Logging + Error Handling.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings
from services.database import Database
from services.autopost import AutoPostService
from services.mentions import MentionHandler
from services.tier_manager import TierManager
from services.unified_agent import UnifiedAgent

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
tier_manager: TierManager | None = None
unified_agent: UnifiedAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global autopost_service, mention_handler, tier_manager, unified_agent

    # Startup
    logger.info("Starting application...")

    # Connect to database
    await db.connect()
    logger.info("Database connected")

    # Initialize tier manager - detect API tier and limits (with db for fallback)
    tier_manager = TierManager(db)
    await tier_manager.initialize()

    # Initialize services with tier manager
    autopost_service = AutoPostService(db, tier_manager)
    mention_handler = MentionHandler(db, tier_manager)
    unified_agent = UnifiedAgent(db, tier_manager)
    logger.info("Services initialized")

    # Check connected Twitter account
    try:
        twitter_client = autopost_service.twitter
        me = twitter_client.get_me()
        logger.info("=" * 50)
        logger.info(f"TWITTER ACCOUNT: @{me['username']}")
        logger.info(f"TWITTER ID: {me['id']}")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"Failed to get Twitter account info: {e}")

    # Check which mode to use
    if settings.use_unified_agent:
        # NEW: Unified Agent mode
        logger.info("=" * 50)
        logger.info("MODE: UNIFIED AGENT (new architecture)")
        logger.info("=" * 50)

        scheduler.add_job(
            unified_agent.run,
            "interval",
            minutes=settings.agent_interval_minutes,
            id="unified_agent"
        )
        logger.info(f"Scheduled unified agent every {settings.agent_interval_minutes} minutes")

    else:
        # LEGACY: Separate autopost + mentions
        logger.info("=" * 50)
        logger.info("MODE: LEGACY (autopost + mentions)")
        logger.info("=" * 50)

        # Schedule autopost
        scheduler.add_job(
            autopost_service.run,
            "interval",
            minutes=settings.post_interval_minutes,
            id="autopost"
        )
        logger.info(f"Scheduled autopost every {settings.post_interval_minutes} minutes")

        # Schedule mentions processing only if tier supports it
        can_mentions, mentions_reason = tier_manager.can_use_mentions()
        if can_mentions:
            scheduler.add_job(
                mention_handler.check_mentions,
                "interval",
                minutes=settings.mentions_interval_minutes,
                id="mentions",
                kwargs={"dry_run": False}
            )
            logger.info(f"Scheduled mentions every {settings.mentions_interval_minutes} minutes")
        else:
            logger.info(f"Mentions scheduling skipped: {mentions_reason}")

    # Schedule hourly tier check (auto-detect subscription upgrades)
    scheduler.add_job(
        tier_manager.maybe_refresh_tier,
        "interval",
        hours=1,
        id="tier_refresh"
    )
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    scheduler.shutdown(wait=False)
    await db.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Twitter Agent Bot",
    description="Agent-based auto-posting Twitter bot with mention handling",
    version="1.3.2",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status."""
    db_ok = await db.ping()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "scheduler_running": scheduler.running,
        "tier": tier_manager.tier if tier_manager else "unknown",
        "version": "1.3.2"
    }


@app.get("/metrics")
async def metrics():
    """Get bot metrics and statistics."""
    return {
        "posts_total": await db.count_posts(),
        "posts_today": await db.count_posts_today(),
        "mentions_total": await db.count_mentions(),
        "mentions_today": await db.count_mentions_today(),
        "last_post_at": await db.get_last_post_time(),
        "last_mention_at": await db.get_last_mention_time()
    }


@app.get("/callback")
async def oauth_callback(oauth_token: str = None, oauth_verifier: str = None):
    """OAuth callback endpoint for Twitter authentication."""
    return {
        "status": "ok",
        "message": "OAuth callback received",
        "oauth_token": oauth_token,
        "oauth_verifier": oauth_verifier
    }


@app.post("/webhook/mentions")
async def handle_mentions_webhook(request: Request):
    """
    Handle incoming Twitter webhook for mentions.

    Note: Webhook-based mentions require Enterprise tier.
    For Basic/Pro tiers, use polling via /process-mentions endpoint.
    """
    if mention_handler is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        data = await request.json()
        logger.info(f"Received mention webhook: {data}")

        # Webhook-based processing is not supported with agent architecture
        # Use /process-mentions polling endpoint instead
        logger.warning("[WEBHOOK] Webhook received but agent architecture uses polling. Use /process-mentions instead.")

        return {
            "status": "received",
            "message": "Webhook received. Use /process-mentions for agent-based processing."
        }
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhook/mentions")
async def verify_webhook(crc_token: str = None):
    """Handle Twitter CRC challenge for webhook verification."""
    import hmac
    import hashlib
    import base64

    if not crc_token:
        raise HTTPException(status_code=400, detail="Missing crc_token")

    sha256_hash = hmac.new(
        settings.twitter_api_secret.encode(),
        msg=crc_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    response_token = base64.b64encode(sha256_hash).decode()

    return {"response_token": f"sha256={response_token}"}


@app.post("/trigger-post")
async def trigger_post():
    """
    Trigger agent-based autopost (legacy mode).

    The agent will:
    1. Create a plan (which tools to use)
    2. Execute tools step by step
    3. Generate final post text
    4. Post to Twitter
    """
    if autopost_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        logger.info("=" * 60)
        logger.info("ENDPOINT: /trigger-post called")
        logger.info("=" * 60)

        result = await autopost_service.run()

        logger.info(f"ENDPOINT: Agent result: success={result.get('success')}")

        return result

    except Exception as e:
        logger.error(f"ENDPOINT: Error in post: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger-agent")
async def trigger_agent():
    """
    Trigger unified agent cycle.

    The agent will:
    1. Load context (recent actions, rate limits)
    2. Use tools to decide what to do (post, reply, search, etc.)
    3. Execute actions until calling finish_cycle
    """
    if unified_agent is None:
        raise HTTPException(status_code=503, detail="Unified agent not initialized")

    try:
        logger.info("=" * 60)
        logger.info("ENDPOINT: /trigger-agent called")
        logger.info("=" * 60)

        result = await unified_agent.run()

        logger.info(f"ENDPOINT: Unified agent result: {result}")

        return result

    except Exception as e:
        logger.error(f"ENDPOINT: Error in unified agent: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-mentions")
async def check_mentions():
    """Fetch mentions WITHOUT processing (dry run)."""
    if mention_handler is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = await mention_handler.check_mentions(dry_run=True)
        return result
    except Exception as e:
        logger.error(f"Error checking mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-mentions")
async def process_mentions():
    """Fetch AND process mentions (actually reply)."""
    if mention_handler is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = await mention_handler.check_mentions(dry_run=False)
        return result
    except Exception as e:
        logger.error(f"Error processing mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tier-status")
async def get_tier_status():
    """Get current Twitter API tier status and usage."""
    if tier_manager is None:
        raise HTTPException(status_code=503, detail="Tier manager not initialized")

    return tier_manager.get_status()


@app.post("/tier-refresh")
async def refresh_tier():
    """Force refresh tier detection."""
    if tier_manager is None:
        raise HTTPException(status_code=503, detail="Tier manager not initialized")

    try:
        result = await tier_manager.detect_tier()
        return result
    except Exception as e:
        logger.error(f"Error refreshing tier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
