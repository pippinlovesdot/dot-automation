"""
Image generation tool using OpenRouter API.

Generates images based on text prompts and reference images from assets folder.
Uses google/gemini-3-pro-image-preview model via OpenRouter.
"""

import base64
import logging
import random
from pathlib import Path

import httpx

from config.models import IMAGE_MODEL
from utils.api import OPENROUTER_URL, get_openrouter_headers

logger = logging.getLogger(__name__)

# Path to reference images folder
ASSETS_PATH = Path(__file__).parent.parent / "assets"

# System prompt for image generation
IMAGE_SYSTEM_PROMPT = """You are an image generation assistant. Your task is to generate images based on reference images provided and user instructions. Always output an image."""


def _get_reference_images() -> list[str]:
    """
    Get all reference images from assets folder as base64.

    Returns:
        List of base64-encoded images with data URI prefix.
    """
    if not ASSETS_PATH.exists():
        logger.warning(f"[IMAGE_GEN] Assets folder not found: {ASSETS_PATH}")
        return []

    images = []
    supported_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    for file_path in ASSETS_PATH.iterdir():
        if file_path.suffix.lower() in supported_extensions:
            try:
                with open(file_path, "rb") as f:
                    image_data = f.read()

                # Determine MIME type
                ext = file_path.suffix.lower()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".webp": "image/webp"
                }
                mime_type = mime_types.get(ext, "image/png")

                # Create data URI
                base64_data = base64.b64encode(image_data).decode()
                data_uri = f"data:{mime_type};base64,{base64_data}"
                images.append(data_uri)

                logger.debug(f"[IMAGE_GEN] Loaded reference image: {file_path.name}")
            except Exception as e:
                logger.error(f"[IMAGE_GEN] Error loading image {file_path}: {e}")

    logger.info(f"[IMAGE_GEN] Loaded {len(images)} reference images from assets")
    return images


def _select_reference_images(count: int = 2) -> list[str]:
    """
    Select reference images for generation.

    Args:
        count: Number of images to select.

    Returns:
        List of base64-encoded images.
    """
    all_images = _get_reference_images()

    if not all_images:
        return []

    if len(all_images) <= count:
        return all_images

    return random.sample(all_images, count)


async def generate_image(prompt: str) -> bytes:
    """
    Generate an image from a text prompt using reference images.

    This is the main tool function for image generation.
    Uses reference images from assets/ folder for consistent character appearance.

    Args:
        prompt: Text description of the image to generate.

    Returns:
        Raw image bytes (PNG format).
    """
    logger.info(f"[IMAGE_GEN] Starting generation for prompt: {prompt[:100]}...")

    reference_images = _select_reference_images(2)
    logger.info(f"[IMAGE_GEN] Using {len(reference_images)} reference images")

    # Build content array with images and text
    content = []

    for image_uri in reference_images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": image_uri
            }
        })

    content.append({
        "type": "text",
        "text": prompt
    })

    # Build request payload
    payload = {
        "model": IMAGE_MODEL,
        "messages": [
            {
                "role": "system",
                "content": IMAGE_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": content
            }
        ]
    }

    logger.info(f"[IMAGE_GEN] Sending request to OpenRouter")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers=get_openrouter_headers(),
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        logger.info(f"[IMAGE_GEN] Response received")

        # Extract image from response - images are in message.images array
        message = data.get("choices", [{}])[0].get("message", {})
        images = message.get("images", [])

        if images:
            # Get first image from images array
            image_url = images[0].get("image_url", {}).get("url", "")
            if image_url.startswith("data:"):
                # Extract base64 from data URI (remove "data:image/...;base64," prefix)
                base64_data = image_url.split(",", 1)[1]
                image_bytes = base64.b64decode(base64_data)
                logger.info(f"[IMAGE_GEN] Generated image: {len(image_bytes)} bytes")
                return image_bytes

        logger.error(f"[IMAGE_GEN] No image data in response: {list(message.keys())}")
        raise ValueError(f"No image data in response: {list(message.keys())}")
