"""
Web search tool using OpenRouter's native web search plugin.

Provides real-time web search capability for the agent.
Uses OpenRouter's plugins API with native search engine.
"""

import logging
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SEARCH_MODEL = "anthropic/claude-sonnet-4.5"


async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search the web using OpenRouter's native web search plugin.

    Args:
        query: Search query string.
        max_results: Maximum number of search results (1-10, default 5).

    Returns:
        Dict with 'content' (search summary) and 'sources' (list of citations).
    """
    logger.info(f"Web search: {query}")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pippinlovesdot.com",
        "X-Title": "DOT Twitter Bot"
    }

    payload = {
        "model": SEARCH_MODEL,
        "messages": [
            {"role": "user", "content": query}
        ],
        "plugins": [
            {
                "id": "web",
                "max_results": max_results
            }
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        message = data["choices"][0]["message"]
        content = message.get("content", "")

        # Extract source citations from annotations
        sources = []
        for annotation in message.get("annotations", []):
            if annotation.get("type") == "url_citation":
                citation = annotation.get("url_citation", {})
                sources.append({
                    "url": citation.get("url", ""),
                    "title": citation.get("title", ""),
                    "snippet": citation.get("content", "")
                })

        logger.info(f"Web search completed: {len(sources)} sources found")

        return {
            "content": content,
            "sources": sources
        }
