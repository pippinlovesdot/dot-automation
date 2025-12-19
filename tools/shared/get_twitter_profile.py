"""
Get Twitter user profile information.

Fetches public profile data from Twitter API.
"""

import logging

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "get_twitter_profile",
    "description": "Get a Twitter user's profile info (bio, followers, tweets count)",
    "params": {
        "username": {
            "type": "string",
            "description": "Twitter handle without @",
            "required": True
        }
    }
}


async def get_twitter_profile(username: str, twitter=None, **kwargs) -> str:
    """
    Get Twitter user profile by username.

    Args:
        username: Twitter handle (without @).
        twitter: TwitterClient instance.
        **kwargs: Additional context.

    Returns:
        Formatted string with profile info.
    """
    if not twitter:
        return "Error: Twitter client not available"

    # Remove @ if present
    username = username.lstrip("@")

    logger.info(f"[GET_PROFILE] Fetching profile for @{username}")

    profile = twitter.get_user_profile(username)

    if not profile:
        return f"Error: User @{username} not found"

    return f"""Profile for @{profile['username']}:
Bio: {profile['bio'] or 'No bio'}
Followers: {profile['followers']:,}
Following: {profile['following']:,}
Tweets: {profile['tweets']:,}
Location: {profile['location'] or 'Not specified'}"""
