"""
OpenRouter API configuration.

Centralized constants and helper functions for OpenRouter API calls.
Used by all services and tools that interact with OpenRouter.
"""

from config.settings import settings

# OpenRouter API endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_openrouter_headers() -> dict:
    """
    Get headers for OpenRouter API requests.

    Returns:
        dict: Headers including authorization, content type, and metadata.
    """
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pippinlovesdot.com",
        "X-Title": "DOT Twitter Bot"
    }
