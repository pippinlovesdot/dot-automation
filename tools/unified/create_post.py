"""
Create a new tweet.

Posts to Twitter with optional image generation.
"""

import logging

from tools.legacy.image_generation import generate_image
from config.settings import settings

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "create_post",
    "description": "Create a new tweet (max 280 chars, optional image)",
    "params": {
        "text": {
            "type": "string",
            "description": "Tweet text (max 280 characters)",
            "required": True
        },
        "include_image": {
            "type": "boolean",
            "description": "Generate and attach an image",
            "required": True
        }
    }
}


async def create_post(text: str, include_image: bool = False, twitter=None, db=None, **kwargs) -> str:
    """
    Create a new tweet.

    Args:
        text: Tweet text (max 280 chars).
        include_image: Whether to generate and attach an image.
        twitter: TwitterClient instance.
        db: Database instance.
        **kwargs: Additional context.

    Returns:
        Result string with tweet ID and remaining posts.
    """
    text = text.strip()

    # Handle string "true"/"false" from LLM
    if isinstance(include_image, str):
        include_image = include_image.lower() in ("true", "1", "yes")

    logger.info(f"[CREATE_POST] === INPUT PARAMS ===")
    logger.info(f"[CREATE_POST] text: {text[:80]}...")
    logger.info(f"[CREATE_POST] include_image: {include_image} (type: {type(include_image).__name__})")

    if not twitter:
        return "Error: Twitter client not available"

    if not db:
        return "Error: Database not available"

    # Check rate limit (tier-based)
    posts_today = await db.count_actions_today("post")
    tier_manager = kwargs.get("tier_manager")
    daily_limit = tier_manager.get_daily_limits()[0] if tier_manager else 15

    if posts_today >= daily_limit:
        return f"Error: Daily post limit reached ({daily_limit}). Cannot post."

    # Truncate if needed
    if len(text) > 280:
        text = text[:277] + "..."

    # Generate image if requested
    media_ids = None
    image_generated = False
    if include_image:
        try:
            image_bytes = await generate_image(text)
            if image_bytes:
                media_id = await twitter.upload_media(image_bytes)
                media_ids = [media_id]
                image_generated = True
                logger.info("[CREATE_POST] Image generated and uploaded")
        except Exception as e:
            logger.error(f"[CREATE_POST] Image generation failed: {e}")

    # Post to Twitter
    try:
        tweet_data = await twitter.post(text, media_ids=media_ids)
        tweet_id = tweet_data["id"]
    except Exception as e:
        logger.error(f"[CREATE_POST] Post failed: {e}")
        return f"Error posting: {e}"

    # Save to database
    await db.save_action(
        action_type="post",
        text=text,
        tweet_id=tweet_id,
        include_picture=image_generated
    )

    remaining = daily_limit - posts_today - 1

    return f"Posted successfully! Tweet ID: {tweet_id}. Image: {'yes' if image_generated else 'no'}. Remaining posts today: {remaining}"
