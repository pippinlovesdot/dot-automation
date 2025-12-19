"""
Agent-based mention handler service.

Processes Twitter mentions using autonomous agent architecture:
1. Select mentions worth replying to
2. For each selected mention:
   - Create a plan (tools to use)
   - Execute tools
   - Generate reply
   - Post reply
"""

import json
import logging
import time
from typing import Any

from services.database import Database
from services.llm import LLMClient
from services.twitter import TwitterClient
from tools.registry import TOOLS, get_tools_description
from config.personality import SYSTEM_PROMPT
from config.prompts.mention_selector_agent import MENTION_SELECTOR_AGENT_PROMPT
from config.prompts.mention_reply_agent import MENTION_REPLY_AGENT_PROMPT
from config.schemas import (
    MENTION_SELECTION_SCHEMA,
    MENTION_PLAN_SCHEMA,
    REPLY_TEXT_SCHEMA,
    TOOL_REACTION_SCHEMA
)

logger = logging.getLogger(__name__)

# Whitelist for testing - only these users can trigger mentions
# Set to empty list [] to allow all users (production mode)
MENTIONS_WHITELIST = []


class MentionAgentHandler:
    """Agent-based handler for processing Twitter mentions."""

    def __init__(self, db: Database, tier_manager=None):
        """Initialize mention agent handler."""
        self.db = db
        self.llm = LLMClient()
        self.twitter = TwitterClient()
        self.tier_manager = tier_manager

    def _validate_plan(self, plan: list[dict]) -> None:
        """
        Validate the agent's plan.

        Rules:
        - generate_image must be last if present
        - Only known tools allowed
        - Max 3 steps
        """
        if len(plan) > 3:
            raise ValueError(f"Plan too long: {len(plan)} steps (max 3)")

        has_image = False
        for i, step in enumerate(plan):
            tool_name = step.get("tool")

            if tool_name not in TOOLS:
                raise ValueError(f"Unknown tool: {tool_name}")

            if tool_name == "generate_image":
                if has_image:
                    raise ValueError("Multiple generate_image calls not allowed")
                if i != len(plan) - 1:
                    raise ValueError("generate_image must be the last step in plan")
                has_image = True

        logger.info(f"[MENTIONS] Plan validated: {len(plan)} steps")

    async def process_mentions_batch(self) -> dict:
        """
        Process mentions using agent architecture.

        Flow:
        1. Tier check (Free=blocked)
        2. Fetch unprocessed mentions
        3. LLM #1: Select mentions worth replying to (array)
        4. For EACH selected mention:
           a. LLM #2: Create plan (tools to use)
           b. Execute tools
           c. LLM #3: Generate reply text
           d. Post reply
           e. Save to database
        5. Return batch summary

        Returns:
            Summary of what happened.
        """
        start_time = time.time()
        logger.info("[MENTIONS] === Starting batch processing ===")

        # Step 1: Tier check
        if self.tier_manager:
            can_use, reason = self.tier_manager.can_use_mentions()
            if not can_use:
                logger.warning(f"[MENTIONS] Blocked: {reason}")
                return {
                    "success": False,
                    "error": f"mentions_blocked: {reason}",
                    "tier": self.tier_manager.tier
                }

        # Step 2: Fetch mentions
        logger.info("[MENTIONS] [1/4] Fetching mentions from Twitter...")
        try:
            mentions = self.twitter.get_mentions(since_id=None)
        except Exception as e:
            logger.error(f"[MENTIONS] [1/4] Fetch FAILED: {e}")
            return {"success": False, "error": str(e)}

        if not mentions:
            logger.info("[MENTIONS] [1/4] No mentions found")
            return {"success": True, "found": 0, "processed": 0}

        logger.info(f"[MENTIONS] [1/4] Found {len(mentions)} mentions")

        # Filter out already processed
        unprocessed = []
        for mention in mentions:
            tweet_id = mention["id_str"]
            if not await self.db.mention_exists(tweet_id):
                unprocessed.append(mention)

        if not unprocessed:
            logger.info("[MENTIONS] [1/4] All mentions already processed")
            return {"success": True, "found": len(mentions), "processed": 0}

        logger.info(f"[MENTIONS] [1/4] Unprocessed: {len(unprocessed)}")

        # Filter by whitelist (for testing on main account)
        if MENTIONS_WHITELIST:
            whitelist_lower = [w.lower() for w in MENTIONS_WHITELIST]
            unprocessed = [
                m for m in unprocessed
                if m.get("user", {}).get("screen_name", "").lower() in whitelist_lower
            ]
            logger.info(f"[MENTIONS] [1/4] After whitelist: {len(unprocessed)} (whitelist: {MENTIONS_WHITELIST})")

            if not unprocessed:
                return {
                    "success": True,
                    "found": len(mentions),
                    "filtered_out": "not_in_whitelist",
                    "whitelist": MENTIONS_WHITELIST,
                    "processed": 0
                }

        # Step 3: LLM #1 - Select mentions worth replying to
        logger.info("[MENTIONS] [2/4] Selecting mentions - calling LLM...")
        selected = await self._select_mentions(unprocessed)

        if not selected:
            logger.info("[MENTIONS] [2/4] No mentions selected for reply")
            return {
                "success": True,
                "found": len(mentions),
                "unprocessed": len(unprocessed),
                "selected": 0,
                "processed": 0
            }

        logger.info(f"[MENTIONS] [2/4] Selected {len(selected)} mentions for reply")

        # Step 4: Process each selected mention
        logger.info("[MENTIONS] [3/4] Processing selected mentions...")
        results = []
        for i, selection in enumerate(selected):
            tweet_id = selection["tweet_id"]
            mention = self._find_mention_by_id(unprocessed, tweet_id)

            if not mention:
                logger.warning(f"[MENTIONS] Could not find mention {tweet_id}")
                continue

            author = mention["user"]["screen_name"]
            logger.info(f"[MENTIONS] [3/4] [{i+1}/{len(selected)}] Processing @{author}...")

            result = await self._process_single_mention(mention, selection)
            results.append(result)

            if result.get("success"):
                logger.info(f"[MENTIONS] [3/4] [{i+1}/{len(selected)}] @{author}: OK")
            else:
                logger.warning(f"[MENTIONS] [3/4] [{i+1}/{len(selected)}] @{author}: FAILED - {result.get('error')}")

        successful = sum(1 for r in results if r.get("success"))

        # Summary
        duration = round(time.time() - start_time, 1)
        logger.info(f"[MENTIONS] === Completed in {duration}s ===")
        logger.info(f"[MENTIONS] Summary: found={len(mentions)} | selected={len(selected)} | replied={successful}")

        return {
            "success": True,
            "found": len(mentions),
            "unprocessed": len(unprocessed),
            "selected": len(selected),
            "processed": successful,
            "results": results,
            "duration_seconds": duration
        }

    async def _select_mentions(self, mentions: list[dict]) -> list[dict]:
        """
        LLM #1: Select mentions worth replying to.

        Args:
            mentions: List of unprocessed mentions.

        Returns:
            List of selected mentions with priority and reasoning.
        """
        logger.info("[MENTIONS] Step 1: Selecting mentions worth replying to")

        # Format mentions for LLM
        mentions_text = self._format_mentions_for_llm(mentions)
        recent_replies = await self.db.get_recent_mentions_formatted(limit=10)

        system_prompt = SYSTEM_PROMPT + MENTION_SELECTOR_AGENT_PROMPT

        user_prompt = f"""Here are the mentions waiting for your response:

{mentions_text}

## Your recent replies (don't repeat yourself):
{recent_replies}

Select which mentions to reply to. You can select multiple, one, or none."""

        result = await self.llm.generate_structured(
            system_prompt,
            user_prompt,
            MENTION_SELECTION_SCHEMA
        )

        selected = result.get("selected_mentions", [])

        # Sort by priority
        selected.sort(key=lambda x: x.get("priority", 999))

        for s in selected:
            logger.info(f"[MENTIONS]   Selected: {s['tweet_id']} (priority {s['priority']})")
            logger.info(f"[MENTIONS]     Reason: {s['reasoning']}")

        return selected

    async def _process_single_mention(
        self,
        mention: dict,
        selection: dict
    ) -> dict:
        """
        Process a single mention with full agent flow.

        Args:
            mention: The mention data.
            selection: Selection info (reasoning, suggested_approach).

        Returns:
            Result dict with success status.
        """
        tweet_id = mention["id_str"]
        author_handle = mention["user"]["screen_name"]
        author_text = mention["text"]

        try:
            # Get conversation history with this user
            user_history = await self.db.get_user_mention_history(author_handle, limit=5)

            # LLM #2: Create plan
            logger.info(f"[MENTIONS] @{author_handle}: Creating plan...")
            plan_result = await self._create_plan(
                mention, selection, user_history
            )

            plan = plan_result.get("plan", [])
            tools_list = " -> ".join([s["tool"] for s in plan]) if plan else "none"
            logger.info(f"[MENTIONS] @{author_handle}: Plan: {len(plan)} tools ({tools_list})")

            # Validate plan
            if plan:
                try:
                    self._validate_plan(plan)
                except ValueError as e:
                    logger.error(f"[MENTIONS] @{author_handle}: Invalid plan: {e}")
                    return {"success": False, "error": f"invalid_plan: {e}", "tweet_id": tweet_id}

            # Execute tools
            image_bytes = None
            tools_used = []
            messages = self._build_initial_messages(mention, selection, user_history)
            messages.append({"role": "assistant", "content": json.dumps(plan_result)})

            for i, step in enumerate(plan):
                tool_name = step["tool"]
                params = step["params"]
                tools_used.append(tool_name)

                if tool_name not in TOOLS:
                    logger.warning(f"[MENTIONS] @{author_handle}: Unknown tool: {tool_name}")
                    continue

                if tool_name == "web_search":
                    query = params.get("query", "")
                    logger.info(f"[MENTIONS] @{author_handle}: [{i+1}/{len(plan)}] web_search - query: {query[:40]}...")

                    result = await TOOLS[tool_name](query)

                    if result.get("error"):
                        logger.warning(f"[MENTIONS] @{author_handle}: web_search: FAILED")
                        messages.append({"role": "user", "content": f"Tool result (web_search): {result['content']}"})
                    else:
                        logger.info(f"[MENTIONS] @{author_handle}: web_search: OK ({len(result['sources'])} sources)")
                        messages.append({"role": "user", "content": f"Tool result (web_search):\n{result['content']}"})

                elif tool_name == "generate_image":
                    prompt = params.get("prompt", "")
                    logger.info(f"[MENTIONS] @{author_handle}: [{i+1}/{len(plan)}] generate_image - prompt: {prompt[:40]}...")

                    image_bytes = await TOOLS[tool_name](prompt)

                    if image_bytes:
                        logger.info(f"[MENTIONS] @{author_handle}: generate_image: OK ({len(image_bytes)} bytes)")
                        messages.append({"role": "user", "content": "Tool result (generate_image): Image generated successfully."})
                    else:
                        logger.warning(f"[MENTIONS] @{author_handle}: generate_image: FAILED - continuing without image")
                        messages.append({"role": "user", "content": "Tool result (generate_image): Failed. Continue without image."})

                # Step-by-step: LLM reacts to tool result
                logger.info(f"[MENTIONS] @{author_handle}: [{i+1}/{len(plan)}] Getting LLM reaction...")
                reaction = await self.llm.chat(messages, TOOL_REACTION_SCHEMA)
                thinking = reaction.get("thinking", "")
                logger.info(f"[MENTIONS] @{author_handle}: [{i+1}/{len(plan)}] Thinking: {thinking[:80]}...")
                messages.append({"role": "assistant", "content": thinking})

            # LLM #3: Generate reply
            logger.info(f"[MENTIONS] @{author_handle}: Generating reply...")
            messages.append({
                "role": "user",
                "content": "Now write your final reply (max 280 characters)."
            })

            reply_result = await self.llm.chat(messages, REPLY_TEXT_SCHEMA)
            reply_text = reply_result.get("reply_text", "").strip()

            if not reply_text:
                logger.warning(f"[MENTIONS] @{author_handle}: Empty reply generated")
                return {"success": False, "error": "empty_reply", "tweet_id": tweet_id}

            # Truncate if needed
            if len(reply_text) > 280:
                reply_text = reply_text[:277] + "..."

            logger.info(f"[MENTIONS] @{author_handle}: Reply: {reply_text[:50]}... ({len(reply_text)} chars)")

            # Upload image if generated
            media_ids = None
            if image_bytes:
                try:
                    media_id = await self.twitter.upload_media(image_bytes)
                    media_ids = [media_id]
                    logger.info(f"[MENTIONS] @{author_handle}: Image uploaded")
                except Exception as e:
                    logger.error(f"[MENTIONS] @{author_handle}: Image upload FAILED: {e}")
                    image_bytes = None

            # Post reply
            await self.twitter.reply(reply_text, tweet_id, media_ids=media_ids)
            logger.info(f"[MENTIONS] @{author_handle}: Reply posted!")

            # Save to database
            tools_used_str = ",".join(tools_used) if tools_used else None
            await self.db.save_mention(
                tweet_id=tweet_id,
                author_handle=author_handle,
                author_text=author_text,
                our_reply=reply_text,
                action="agent_replied",
                tools_used=tools_used_str
            )

            return {
                "success": True,
                "tweet_id": tweet_id,
                "author": author_handle,
                "reply": reply_text,
                "tools_used": tools_used_str,
                "has_image": image_bytes is not None
            }

        except Exception as e:
            logger.error(f"[MENTIONS] @{author_handle}: Error: {e}")
            logger.exception(e)
            return {"success": False, "error": str(e), "tweet_id": tweet_id}

    async def _create_plan(
        self,
        mention: dict,
        selection: dict,
        user_history: str
    ) -> dict:
        """
        LLM #2: Create plan for replying to mention.

        Args:
            mention: The mention data.
            selection: Selection info with suggested_approach.
            user_history: Conversation history with user.

        Returns:
            Plan dict with reasoning and tools.
        """
        author_handle = mention["user"]["screen_name"]
        author_text = mention["text"]

        tools_desc = get_tools_description()
        system_prompt = SYSTEM_PROMPT + MENTION_REPLY_AGENT_PROMPT + f"\n\n{tools_desc}"

        user_prompt = f"""@{author_handle} mentioned you: {author_text}

## Why this mention was selected:
{selection.get('reasoning', 'Interesting mention')}

## Suggested approach:
{selection.get('suggested_approach', 'Reply authentically')}

## Your conversation history with @{author_handle}:
{user_history}

Create your plan. What tools do you need (if any)?"""

        result = await self.llm.generate_structured(
            system_prompt,
            user_prompt,
            MENTION_PLAN_SCHEMA
        )

        logger.info(f"[MENTIONS]   Plan reasoning: {result.get('reasoning', 'N/A')}")

        return result

    def _build_initial_messages(
        self,
        mention: dict,
        selection: dict,
        user_history: str
    ) -> list[dict]:
        """Build initial messages for the conversation."""
        author_handle = mention["user"]["screen_name"]
        author_text = mention["text"]

        tools_desc = get_tools_description()
        system_prompt = SYSTEM_PROMPT + MENTION_REPLY_AGENT_PROMPT + f"\n\n{tools_desc}"

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""@{author_handle} mentioned you: {author_text}

## Why this mention was selected:
{selection.get('reasoning', 'Interesting mention')}

## Your conversation history with @{author_handle}:
{user_history}

Create your plan."""
            }
        ]

    def _format_mentions_for_llm(self, mentions: list[dict]) -> str:
        """Format mentions list for LLM prompt."""
        lines = []
        for m in mentions:
            tweet_id = m["id_str"]
            author = m["user"]["screen_name"]
            text = m["text"]
            lines.append(f"- tweet_id: {tweet_id}\n  from: @{author}\n  text: {text}")
        return "\n\n".join(lines)

    def _find_mention_by_id(
        self,
        mentions: list[dict],
        tweet_id: str
    ) -> dict | None:
        """Find mention by tweet_id."""
        for m in mentions:
            if m["id_str"] == tweet_id:
                return m
        return None

    async def check_mentions(self, dry_run: bool = True) -> dict:
        """
        Poll Twitter for new mentions.

        Args:
            dry_run: If True, only fetch and return mentions without processing.

        Returns:
            Summary of mentions found.
        """
        logger.info(f"[MENTIONS] Checking mentions (dry_run={dry_run})")

        last_mention_id = await self.db.get_state("last_mention_id")

        try:
            mentions = self.twitter.get_mentions(since_id=last_mention_id)
        except Exception as e:
            logger.error(f"[MENTIONS] Failed to fetch mentions: {e}")
            return {"error": str(e), "found": 0}

        if not mentions:
            return {"found": 0, "mentions": [], "dry_run": dry_run}

        found = []
        for mention in mentions:
            found.append({
                "tweet_id": mention["id_str"],
                "author": mention["user"]["screen_name"],
                "text": mention["text"][:100]
            })

        if dry_run:
            logger.info(f"[MENTIONS] DRY RUN: Found {len(found)} mentions")
            return {"found": len(found), "mentions": found, "dry_run": True}

        # Real run - process mentions
        result = await self.process_mentions_batch()
        result["mentions"] = found
        result["dry_run"] = False
        return result


# Alias for backwards compatibility
MentionHandler = MentionAgentHandler
