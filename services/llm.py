"""
LLM client for OpenRouter API.

Provides async interface for text generation with structured output support.
Uses anthropic/claude-sonnet-4.5 for text generation.
"""

import json
import logging
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TEXT_MODEL = "anthropic/claude-sonnet-4.5"


class LLMClient:
    """Async client for OpenRouter LLM API."""

    def __init__(self, model: str = TEXT_MODEL):
        """
        Initialize LLM client.

        Args:
            model: Model identifier for OpenRouter.
        """
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pippinlovesdot.com",
            "X-Title": "DOT Twitter Bot"
        }

    async def generate(self, system: str, user: str) -> str:
        """
        Generate text completion.

        Args:
            system: System prompt defining behavior.
            user: User message to respond to.

        Returns:
            Generated text response.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.info(f"Generated response: {content[:100]}...")
            return content

    async def generate_structured(
        self,
        system: str,
        user: str,
        response_format: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate structured JSON output.

        Args:
            system: System prompt defining behavior.
            user: User message to respond to.
            response_format: JSON schema for structured output.

        Returns:
            Parsed JSON response.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 500,
                    "response_format": response_format
                }
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.info(f"Generated structured response: {content}")

            # Parse JSON response
            return json.loads(content)
