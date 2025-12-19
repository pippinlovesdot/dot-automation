"""
Get unread mentions from Twitter.

Fetches mentions and filters out already processed ones.
Only available on Basic+ tier.
"""

import logging

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "get_mentions",
    "description": "Get unread mentions/replies to you (Basic+ tier only)",
    "params": {},
    "tier": "basic+"
}

# Whitelist for testing (empty = all users)
MENTIONS_WHITELIST = []


async def get_mentions(twitter=None, db=None, tier_manager=None, **kwargs) -> str:
    """
    Get unread mentions from Twitter.

    Saves mentions to DB as 'pending' so author_text is preserved for history.

    Args:
        twitter: TwitterClient instance.
        db: Database instance.
        tier_manager: TierManager instance.
        **kwargs: Additional context.

    Returns:
        Formatted string with mentions list.
    """
    logger.info("[GET_MENTIONS] Fetching mentions")

    # Check tier
    if tier_manager:
        can_use, reason = tier_manager.can_use_mentions()
        if not can_use:
            return f"Error: {reason}"

    if not twitter:
        return "Error: Twitter client not available"

    if not db:
        return "Error: Database not available"

    try:
        mentions = twitter.get_mentions(since_id=None)
    except Exception as e:
        logger.error(f"[GET_MENTIONS] Failed: {e}")
        return f"Error fetching mentions: {e}"

    if not mentions:
        return "No new mentions found."

    # Filter by whitelist if set
    if MENTIONS_WHITELIST:
        mentions = [
            m for m in mentions
            if m["user"]["screen_name"].lower() in [w.lower() for w in MENTIONS_WHITELIST]
        ]
        if not mentions:
            return "No new mentions from whitelisted users."

    # Filter out already processed
    unprocessed = []
    for mention in mentions:
        tweet_id = mention["id_str"]
        if not await db.mention_exists(tweet_id):
            author = mention["user"]["screen_name"]
            text = mention["text"]
            unprocessed.append(f"- tweet_id: {tweet_id}\n  from: @{author}\n  text: {text}")

            # Save to DB as pending (so we have author_text for history)
            await db.save_mention(
                tweet_id=tweet_id,
                author_handle=author,
                author_text=text,
                our_reply=None,
                action="pending"
            )

    if not unprocessed:
        return "No new unprocessed mentions."

    logger.info(f"[GET_MENTIONS] Found {len(unprocessed)} unprocessed mentions")
    return f"Found {len(unprocessed)} unprocessed mentions:\n\n" + "\n\n".join(unprocessed)
