"""
Auto-posting service for scheduled Twitter posts.

Generates and posts content at regular intervals.
"""

import logging

from services.database import Database
from services.llm import LLMClient
from services.twitter import TwitterClient
from services.image_gen import ImageGenerator
from config.personality import SYSTEM_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)

# JSON Schema for structured output
POST_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "twitter_post",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The tweet text, max 280 characters"
                },
                "include_picture": {
                    "type": "boolean",
                    "description": "Whether to include a generated picture with this post"
                }
            },
            "required": ["text", "include_picture"],
            "additionalProperties": False
        }
    }
}


class AutoPostService:
    """Service for automated Twitter posting."""

    def __init__(self, db: Database):
        """
        Initialize autopost service.

        Args:
            db: Database instance for storing posts.
        """
        self.db = db
        self.llm = LLMClient()
        self.twitter = TwitterClient()
        self.image_gen = ImageGenerator()

    async def run(self) -> None:
        """
        Execute autopost workflow.

        1. Get recent posts from DB for context
        2. Generate new post text via LLM with structured output
        3. If include_picture=True, generate and upload image
        4. Post to Twitter
        5. Save to database with include_picture flag
        """
        try:
            logger.info("Starting autopost...")

            # Get recent posts for context (formatted)
            previous_posts = await self.db.get_recent_posts_formatted(limit=50)

            # Generate post with structured output
            user_prompt = f"""Create a tweet that's different in structure and topic from your previous tweets.

Previous posts for context (don't repeat these):
{previous_posts}

Requirements:
- Maximum 280 characters
- Be authentic to your personality
- Decide if this post needs a picture or not (variety is good)"""

            result = await self.llm.generate_structured(
                SYSTEM_PROMPT,
                user_prompt,
                POST_RESPONSE_FORMAT
            )

            post_text = result["text"].strip()
            include_picture = result["include_picture"]

            # Ensure it's within Twitter limit
            if len(post_text) > 280:
                post_text = post_text[:277] + "..."

            logger.info(f"Generated post: {post_text[:50]}... (include_picture={include_picture})")

            # Generate image only if include_picture is True AND image generation is enabled
            media_ids = None
            if include_picture and settings.enable_image_generation:
                image_prompt = ""  # Customize for your bot's image style
                try:
                    image_bytes = await self.image_gen.generate(image_prompt)
                    media_id = await self.twitter.upload_media(image_bytes)
                    media_ids = [media_id]
                    logger.info("Image generated and uploaded")
                except Exception as e:
                    logger.warning(f"Image generation failed, posting without image: {e}")
                    include_picture = False

            # Post to Twitter
            tweet_data = await self.twitter.post(post_text, media_ids=media_ids)

            # Save to database with include_picture flag
            await self.db.save_post(post_text, tweet_data["id"], include_picture)

            logger.info(f"Autopost complete: {post_text[:50]}...")

        except Exception as e:
            logger.error(f"Autopost failed: {e}")
            raise
