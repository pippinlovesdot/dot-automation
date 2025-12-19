"""
Reply to a tweet.

Posts a reply to Twitter with optional image generation.
Only available on Basic+ tier.
"""

import logging

from tools.legacy.image_generation import generate_image
from config.settings import settings

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "create_reply",
    "description": "Reply to a tweet (Basic+ tier only)",
    "params": {
        "text": {
            "type": "string",
            "description": "Reply text (max 280 characters)",
            "required": True
        },
        "reply_to_tweet_id": {
            "type": "string",
            "description": "Tweet ID to reply to",
            "required": True
        },
        "reply_to_author": {
            "type": "string",
            "description": "Username of the tweet author (without @)",
            "required": True
        },
        "include_image": {
            "type": "boolean",
            "description": "Whether to generate and attach an image (true/false)",
            "required": True
        }
    },
    "tier": "basic+"
}


async def create_reply(
    text: str,
    reply_to_tweet_id: str,
    reply_to_author: str = "unknown",
    include_image: bool = True,  # Default True for testing
    tools_used: list[str] | None = None,
    twitter=None,
    db=None,
    tier_manager=None,
    **kwargs
) -> str:
    """
    Reply to a tweet.

    Args:
        text: Reply text (max 280 chars).
        reply_to_tweet_id: Tweet ID to reply to.
        reply_to_author: Twitter handle of the original author.
        include_image: Whether to generate and attach an image.
        tools_used: List of tools used before this reply (for tracking).
        twitter: TwitterClient instance.
        db: Database instance.
        tier_manager: TierManager instance.
        **kwargs: Additional context.

    Returns:
        Result string with success status and remaining replies.
    """
    text = text.strip()

    # Handle string "true"/"false" from LLM
    if isinstance(include_image, str):
        include_image = include_image.lower() in ("true", "1", "yes")

    # Clean up author
    reply_to_author = reply_to_author.lstrip("@") if reply_to_author else "unknown"

    logger.info(f"[CREATE_REPLY] Replying to @{reply_to_author}, include_image={include_image}, tools_used={tools_used}")

    # Check tier
    if tier_manager:
        can_use, reason = tier_manager.can_use_mentions()
        if not can_use:
            return f"Error: {reason}"

    if not twitter:
        return "Error: Twitter client not available"

    if not db:
        return "Error: Database not available"

    # Check rate limit (tier-based)
    replies_today = await db.count_actions_today("reply")
    tier_manager = kwargs.get("tier_manager")
    daily_limit = tier_manager.get_daily_limits()[1] if tier_manager else 50

    if replies_today >= daily_limit:
        return f"Error: Daily reply limit reached ({daily_limit}). Cannot reply."

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
                logger.info(f"[CREATE_REPLY] Image generated and uploaded")
        except Exception as e:
            logger.error(f"[CREATE_REPLY] Image generation failed: {e}")

    # Post reply
    try:
        await twitter.reply(text, reply_to_tweet_id, media_ids=media_ids)
    except Exception as e:
        logger.error(f"[CREATE_REPLY] Reply failed: {e}")
        return f"Error replying: {e}"

    # Save to actions table
    await db.save_action(
        action_type="reply",
        text=text,
        reply_to_tweet_id=reply_to_tweet_id,
        reply_to_author=reply_to_author,
        include_picture=image_generated
    )

    # Update pending mention with our reply (or create if not exists)
    tools_used_str = ",".join(tools_used) if tools_used else None

    if await db.mention_exists(reply_to_tweet_id, include_pending=True):
        # Update existing pending mention
        await db.update_mention(
            tweet_id=reply_to_tweet_id,
            our_reply=text,
            action="agent_replied",
            tools_used=tools_used_str
        )
    else:
        # Fallback: create new mention record
        await db.save_mention(
            tweet_id=reply_to_tweet_id,
            author_handle=reply_to_author,
            author_text="",
            our_reply=text,
            action="agent_replied",
            tools_used=tools_used_str
        )

    remaining = daily_limit - replies_today - 1

    return f"Replied successfully to {reply_to_tweet_id}! Image: {'yes' if image_generated else 'no'}. Remaining replies today: {remaining}"
