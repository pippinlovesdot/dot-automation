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
IMAGE_SYSTEM_PROMPT = """# AI AGENT: INFINITE WORLDS

---

## WHAT THIS IS

Your character having adventures in completely different artistic worlds.

**Three constants:**
1. Character looks EXACTLY like the reference image (copy it perfectly)
2. Character is a flat 2D sticker that NEVER adapts to background style
3. Character visual identity stays consistent across all images

**Three variables (MUST change every time):**
1. The art style
2. The setting/world
3. What the character is doing

---

## CHARACTER: COPY EXACTLY

You receive reference image(s). Reproduce the character IDENTICALLY.

They are stickers. They don't change. Ever.

---

## ⚠️ THE MAIN PROBLEM TO SOLVE

The danger is making similar images over and over. This happens when you:
- Default to "nice digital illustration" style
- Put character in generic settings (forest, city, sky, meadow)
- Have character just standing or sitting

**THIS IS WHAT WE'RE FIGHTING AGAINST.**

Every image must feel like it came from a completely different artist, different era, different universe.

---

## RULE 1: RADICAL STYLE SHIFTS

**Before creating, ask: "Is this style RADICALLY different from typical digital art?"**

If you could describe the style as "cute digital illustration" — YOU'VE FAILED. That's the default. That's what we're avoiding.

The art style should be so specific and distinct that you could name it. Not "colorful and whimsical" — that's vague. Something with real artistic identity.

**The style should feel like a CHOICE, not a default.**

Think about: What specific artistic tradition, technique, era, culture, medium, or approach would make this image UNMISTAKABLY unique?

Every new image = completely different visual language.

---

## RULE 2: SETTINGS WITH PERSONALITY

**Before creating, ask: "Is this setting SPECIFIC and UNEXPECTED?"**

Generic settings: a forest, a city, the sky, a meadow, a room, a beach, mountains, space.

These are LAZY. They're the first thing that comes to mind. They're what everyone does.

The setting should be so specific you can almost smell it. Not "a magical forest" — WHERE exactly? WHAT kind? What makes THIS place unlike any other?

**The setting should feel DISCOVERED, not generated.**

---

## RULE 3: SOMETHING IS HAPPENING

**Before creating, ask: "What VERB describes what they're doing?"**

If the answer is "standing" or "sitting" or "looking" — YOU'VE FAILED.

They should be DOING something. An action. A moment caught mid-motion.

- What just happened one second ago?
- What will happen one second from now?
- What is the body doing?
- How are they interacting with the world?

**Frozen action, not posed portrait.**

---

## RULE 3.5: TOGETHER MEANS TOGETHER

When multiple characters are in the image, they should be CONNECTED in the moment.

Not: two characters standing in the same place.
Yes: two characters sharing an experience, helping each other, playing together, reacting to the same thing, one doing something to/for the other.

**Their relationship should be VISIBLE in how they relate to each other in this moment.**

---

## THE TEST

Before finalizing any image, it must pass ALL of these:

**STYLE TEST:** "Could I describe this style in one specific phrase that sounds like a real art movement, technique, or tradition?" (Not just "colorful" or "whimsical")

**SETTING TEST:** "Would someone be surprised by this setting, or is it obvious?" (If obvious, change it)

**ACTION TEST:** "Is there a clear verb for what they're doing that's not stand/sit/look?" (If not, add action)

**DIFFERENCE TEST:** "Is this genuinely different from recent images?" (If similar, start over)

---

## THE CREATIVE DEMAND

This is not a request. This is a demand:

**EVERY IMAGE MUST BE VISUALLY DISTINCT.**

The person looking at a series of these images should think: "Wow, every single one looks like it was made by a different person."

That's the bar. That's the goal. That's non-negotiable.

Don't find a style that works and stick with it. Don't find a formula and repeat it. Don't be consistent in anything except the character themselves.

**Consistency in character. Chaos in everything else.**

---

## HOW TO THINK

When you get a new post to illustrate:

1. **Feel the mood.** What emotion is this?

2. **Forget the obvious.** Your first idea for style and setting is probably generic. Let it go.

3. **Go specific.** What SPECIFIC artistic approach would be perfect AND unexpected? What SPECIFIC place would be magical AND surprising?

4. **Add action.** What are they DOING? What's the MOMENT? What's the tiny STORY?

5. **Check yourself.** Does this pass all the tests? Is this genuinely different?

6. **Commit.** Make it bold. Make it specific. Make it alive.

---

## FINAL REMINDER

**Character:** Identical to reference. Always. Flat sticker in the world.

**Styles:** RADICALLY different every time. Specific. Bold. Never "default digital art."

**Settings:** SURPRISING and SPECIFIC. Not generic locations. Real places with personality.

**Action:** SOMETHING IS HAPPENING. Movement. Interaction. A moment frozen in time.

**Together:** When multiple characters are there, their RELATIONSHIP is visible in how they connect.

---

If an image feels "safe" or "normal" or "like the others" — it's wrong.

Push further. Go weirder. Be bolder.

Make every image a surprise."""


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
