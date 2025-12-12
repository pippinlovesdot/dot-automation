"""
Mention handler service with LLM-based selection.

Processes Twitter mentions: LLM chooses which mention to reply to,
generates response text, and decides whether to include an image.
"""

import logging
from typing import Any

from services.database import Database
from services.llm import LLMClient
from services.twitter import TwitterClient
from services.image_gen import ImageGenerator
from config.personality import SYSTEM_PROMPT
from config.prompts.mention_selector import MENTION_SELECTOR_PROMPT
from config.schemas import MENTION_SELECTOR_SCHEMA
from config.settings import settings

logger = logging.getLogger(__name__)


class MentionHandler:
    """Handler for processing Twitter mentions with LLM selection."""

    def __init__(self, db: Database, tier_manager=None):
        """Initialize mention handler."""
        self.db = db
        self.llm = LLMClient()
        self.twitter = TwitterClient()
        self.image_gen = ImageGenerator()
        self.tier_manager = tier_manager

    async def process_mentions_batch(self) -> dict:
        """
        Fetch mentions and let LLM choose one to reply to.

        Flow:
        1. Fetch recent mentions from Twitter
        2. Filter out already processed
        3. Send all to LLM - it picks one and generates reply
        4. Post reply (with picture if LLM decided)
        5. Save to database

        Returns:
            Summary of what happened.
        """
        # Check if mentions are available on current tier
        if self.tier_manager:
            can_use, reason = self.tier_manager.can_use_mentions()
            if not can_use:
                logger.warning(f"[MENTIONS] Mentions blocked: {reason}")
                return {"error": reason, "replied": False}

        logger.info("Processing mentions batch...")

        # Step 1: Fetch mentions from Twitter
        try:
            mentions = self.twitter.get_mentions(since_id=None)
        except Exception as e:
            logger.error(f"Failed to fetch mentions: {e}")
            return {"error": str(e), "replied": False}

        if not mentions:
            logger.info("No mentions found")
            return {"found": 0, "replied": False}

        # Step 2: Filter out already processed mentions
        unprocessed = []
        for mention in mentions:
            tweet_id = mention["id_str"]
            if not await self.db.mention_exists(tweet_id):
                unprocessed.append(mention)

        if not unprocessed:
            logger.info("All mentions already processed")
            return {"found": len(mentions), "unprocessed": 0, "replied": False}

        logger.info(f"Found {len(unprocessed)} unprocessed mentions")

        # Step 3: Build prompt with all unprocessed mentions
        mentions_text = self._format_mentions_for_llm(unprocessed)
        recent_replies = await self.db.get_recent_mentions_formatted(limit=10)

        system_prompt = SYSTEM_PROMPT + MENTION_SELECTOR_PROMPT

        user_prompt = f"""Here are the mentions waiting for your response:

{mentions_text}

## Your recent replies (don't repeat yourself):
{recent_replies}

Choose ONE mention to reply to (or none if all are low quality). Provide the tweet_id, your reply text, and whether to include a picture."""

        # Step 4: LLM chooses and generates reply
        result = await self.llm.generate_structured(
            system_prompt,
            user_prompt,
            MENTION_SELECTOR_SCHEMA
        )

        logger.info(f"LLM decision: {result}")

        selected_id = result["selected_tweet_id"].strip()
        reply_text = result["text"].strip()
        include_picture = result["include_picture"]
        reasoning = result["reasoning"]

        # If LLM chose not to reply
        if not selected_id or not reply_text:
            logger.info(f"LLM chose not to reply. Reason: {reasoning}")
            return {
                "found": len(mentions),
                "unprocessed": len(unprocessed),
                "replied": False,
                "reason": reasoning
            }

        # Find the selected mention
        selected_mention = None
        for m in unprocessed:
            if m["id_str"] == selected_id:
                selected_mention = m
                break

        if not selected_mention:
            logger.error(f"LLM selected invalid tweet_id: {selected_id}")
            return {"error": "Invalid tweet_id selected", "replied": False}

        author_handle = selected_mention["user"]["screen_name"]
        author_text = selected_mention["text"]

        # Ensure reply is within Twitter limit
        if len(reply_text) > 280:
            reply_text = reply_text[:277] + "..."

        # Step 5: Generate image if requested
        media_ids = None
        if include_picture and settings.enable_image_generation:
            image_prompt = f"Create an image related to this reply: {reply_text}"
            try:
                image_bytes = await self.image_gen.generate(image_prompt)
                media_id = await self.twitter.upload_media(image_bytes)
                media_ids = [media_id]
                logger.info("Image generated and uploaded for reply")
            except Exception as e:
                logger.warning(f"Image generation failed: {e}")
                include_picture = False

        # Step 6: Post reply
        try:
            await self.twitter.reply(reply_text, selected_id, media_ids=media_ids)
            logger.info(f"Replied to @{author_handle}: {reply_text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to post reply: {e}")
            return {"error": str(e), "replied": False}

        # Step 7: Save to database
        await self.db.save_mention(
            tweet_id=selected_id,
            author_handle=author_handle,
            author_text=author_text,
            our_reply=reply_text,
            action="replied"
        )

        return {
            "found": len(mentions),
            "unprocessed": len(unprocessed),
            "replied": True,
            "replied_to": {
                "tweet_id": selected_id,
                "author": author_handle,
                "text": author_text[:50],
                "our_reply": reply_text[:50],
                "include_picture": include_picture
            },
            "reasoning": reasoning
        }

    def _format_mentions_for_llm(self, mentions: list[dict]) -> str:
        """Format mentions list for LLM prompt."""
        lines = []
        for m in mentions:
            tweet_id = m["id_str"]
            author = m["user"]["screen_name"]
            text = m["text"]
            lines.append(f"- tweet_id: {tweet_id}\n  from: @{author}\n  text: {text}")
        return "\n\n".join(lines)
