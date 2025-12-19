"""
Get conversation history with a Twitter user.

Fetches past interactions from the database.
"""

import logging

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "get_conversation_history",
    "description": "Get your past conversation history with a user from database",
    "params": {
        "username": {
            "type": "string",
            "description": "Twitter handle without @",
            "required": True
        }
    }
}


async def get_conversation_history(username: str, db=None, **kwargs) -> str:
    """
    Get conversation history with a user from database.

    Args:
        username: Twitter handle (without @).
        db: Database instance.
        **kwargs: Additional context.

    Returns:
        Formatted string with conversation history.
    """
    if not db:
        return "Error: Database not available"

    # Remove @ if present
    username = username.lstrip("@").lower()

    # Get from mentions table (contains both user messages and our replies)
    history = await db.get_user_mention_history(username, limit=10)

    if not history or history == "No previous conversations with this user.":
        return f"No previous conversations with @{username}"

    return f"Conversation history with @{username}:\n{history}"
