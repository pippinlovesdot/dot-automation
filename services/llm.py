"""
LLM client for OpenRouter API.

Provides async interface for text generation with tool calling support.
Unified client for all LLM interactions in the bot.
"""

import json
import logging
from typing import Any

import httpx

from config.models import LLM_MODEL
from utils.api import OPENROUTER_URL, get_openrouter_headers

logger = logging.getLogger(__name__)


class LLMClient:
    """Async client for OpenRouter LLM API."""

    def __init__(self, model: str = LLM_MODEL):
        """
        Initialize LLM client.

        Args:
            model: Model identifier for OpenRouter.
        """
        self.model = model

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
                headers=get_openrouter_headers(),
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
                headers=get_openrouter_headers(),
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

            return json.loads(content)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Multi-turn chat completion with optional structured output.

        Used for agent flows where conversation history matters.

        Args:
            messages: List of message dicts with role and content.
            response_format: Optional JSON schema for structured output.

        Returns:
            Parsed JSON response if response_format provided, else raw content dict.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=get_openrouter_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.info(f"Chat response: {content[:200]}...")

            if response_format:
                return json.loads(content)
            return {"content": content}
