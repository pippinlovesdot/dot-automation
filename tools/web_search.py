"""
Web search tool using OpenRouter's native web search plugin.

Provides real-time web search capability for the agent.
Uses OpenRouter's plugins API with native search engine.
"""

import logging
from typing import Any

import httpx

from config.models import LLM_MODEL
from utils.api import OPENROUTER_URL, get_openrouter_headers

logger = logging.getLogger(__name__)

# Tool schema for auto-discovery
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information. Use this when you need to find recent news, events, prices, facts, or any information that might not be in your training data.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results (1-10, default 5)"
                }
            },
            "required": ["query"]
        }
    }
}


async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search the web using OpenRouter's native web search plugin.

    Args:
        query: Search query string.
        max_results: Maximum number of search results (1-10, default 5).

    Returns:
        Dict with 'content' (search summary) and 'sources' (list of citations).
    """
    logger.info(f"[WEB_SEARCH] Starting search: {query}")

    payload = {
        "model": LLM_MODEL,
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

    logger.info(f"[WEB_SEARCH] Sending request to OpenRouter with plugins: web")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers=get_openrouter_headers(),
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        logger.info(f"[WEB_SEARCH] Response received")

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

        logger.info(f"[WEB_SEARCH] Completed: {len(sources)} sources found")
        logger.info(f"[WEB_SEARCH] Content preview: {content[:200]}...")

        return {
            "content": content,
            "sources": sources
        }
