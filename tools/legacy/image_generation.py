"""
Image generation tool using OpenRouter API.

Generates images based on text prompts and reference images from assets folder.
Uses google/gemini-3-pro-image-preview model via OpenRouter.

Used by Legacy autopost. Unified agent uses include_image flag in create_post.
"""

import base64
import logging
from pathlib import Path

import httpx

from config.models import IMAGE_MODEL
from config.settings import settings
from utils.api import OPENROUTER_URL, get_openrouter_headers

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "generate_image",
    "description": "Generate an image based on a text description using reference images for consistent character appearance",
    "params": {
        "prompt": {
            "type": "string",
            "description": "Text description of the image to generate",
            "required": True
        }
    }
}

# Path to reference images folder
ASSETS_PATH = Path(__file__).parent.parent.parent / "assets"

# System prompt for image generation
IMAGE_SYSTEM_PROMPT = """You are an image generation assistant.

Your task is to generate images based on:
1. Reference images provided (for consistent character appearance)
2. User's text description

Guidelines:
- Always output an image
- Maintain character consistency with reference images
- Follow the user's prompt for scene, action, and style
- Characters should be small in frame (8-15% of image)
- Create visually interesting and varied compositions

Generate the image now based on the user's prompt."""


def _get_reference_images() -> list[str]:
    """Get all reference images from assets folder as base64."""
    if not ASSETS_PATH.exists():
        logger.warning(f"[IMAGE_GEN] Assets folder not found: {ASSETS_PATH}")
        return []

    images = []
    supported_extensions = {".png", ".jpg", ".jpeg", ".jfif", ".gif", ".webp"}

    for file_path in ASSETS_PATH.iterdir():
        if file_path.suffix.lower() in supported_extensions:
            try:
                with open(file_path, "rb") as f:
                    image_data = f.read()

                ext = file_path.suffix.lower()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".jfif": "image/jpeg",
                    ".gif": "image/gif",
                    ".webp": "image/webp"
                }
                mime_type = mime_types.get(ext, "image/png")

                base64_data = base64.b64encode(image_data).decode()
                data_uri = f"data:{mime_type};base64,{base64_data}"
                images.append(data_uri)

            except Exception as e:
                logger.error(f"[IMAGE_GEN] Error loading image {file_path}: {e}")

    logger.info(f"[IMAGE_GEN] Loaded {len(images)} reference images from assets")
    return images


async def generate_image(prompt: str, **kwargs) -> bytes | None:
    """
    Generate an image from a text prompt using reference images.

    Args:
        prompt: Text description of the image to generate.
        **kwargs: Additional context (not used).

    Returns:
        Raw image bytes (PNG format), or None on error.
    """
    # Check if image generation is enabled
    if not settings.enable_image_generation:
        logger.info("[IMAGE_GEN] Image generation is disabled")
        return None

    logger.info(f"[IMAGE_GEN] Starting generation for prompt: {prompt[:100]}...")

    reference_images = _get_reference_images()
    logger.info(f"[IMAGE_GEN] Using ALL {len(reference_images)} reference images")

    content = []
    for image_uri in reference_images:
        content.append({
            "type": "image_url",
            "image_url": {"url": image_uri}
        })

    content.append({
        "type": "text",
        "text": prompt
    })

    payload = {
        "model": IMAGE_MODEL,
        "messages": [
            {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
    }

    logger.info(f"[IMAGE_GEN] Sending request to OpenRouter")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=get_openrouter_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        logger.info(f"[IMAGE_GEN] Response received")

        message = data.get("choices", [{}])[0].get("message", {})
        images = message.get("images", [])

        if images:
            image_url = images[0].get("image_url", {}).get("url", "")
            if image_url.startswith("data:"):
                base64_data = image_url.split(",", 1)[1]
                image_bytes = base64.b64decode(base64_data)
                logger.info(f"[IMAGE_GEN] Generated image: {len(image_bytes)} bytes")
                return image_bytes

        logger.error(f"[IMAGE_GEN] No image data in response")
        return None

    except httpx.TimeoutException:
        logger.error(f"[IMAGE_GEN] Timeout after 120s")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"[IMAGE_GEN] API error: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"[IMAGE_GEN] Unexpected error: {e}")
        return None
