"""
Agent-based autoposting service.

The agent creates a plan, executes tools step by step,
and generates the final post text.

All in one continuous conversation (user-assistant-user-assistant...).
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
from config.prompts.agent_autopost import AUTOPOST_AGENT_PROMPT
from config.schemas import PLAN_SCHEMA, POST_TEXT_SCHEMA, TOOL_REACTION_SCHEMA

logger = logging.getLogger(__name__)


def get_agent_system_prompt() -> str:
    """
    Build agent system prompt with dynamic tools list.

    Tools are loaded from registry, so adding a new tool to TOOLS_SCHEMA
    automatically makes it available to the agent.
    """
    tools_desc = get_tools_description()
    return AUTOPOST_AGENT_PROMPT.format(tools_desc=tools_desc)


class AutoPostService:
    """Agent-based autoposting service with continuous conversation."""

    def __init__(self, db: Database, tier_manager=None):
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

        logger.info(f"[AUTOPOST] Plan validated: {len(plan)} steps")

    async def run(self) -> dict[str, Any]:
        """
        Execute the agent autopost flow.

        Single continuous conversation:
        1. User: context + request for plan
        2. Assistant: plan
        3. User: tool result
        4. ... repeat for each tool ...
        5. User: request for final text
        6. Assistant: post text

        Returns:
            Summary of what happened.
        """
        start_time = time.time()
        logger.info("[AUTOPOST] === Starting ===")

        try:
            # Step 0: Check if posting is allowed (tier limits)
            if self.tier_manager:
                can_post, reason = self.tier_manager.can_post()
                if not can_post:
                    logger.warning(f"[AUTOPOST] Blocked: {reason}")
                    return {
                        "success": False,
                        "error": f"posting_blocked: {reason}",
                        "tier": self.tier_manager.tier,
                        "usage_percent": self.tier_manager.get_usage_percent()
                    }

            # Step 1: Get context
            logger.info("[AUTOPOST] [1/5] Loading context...")
            previous_posts = await self.db.get_recent_posts_formatted(limit=50)
            logger.info(f"[AUTOPOST] [1/5] Loaded {len(previous_posts)} chars of previous posts")

            # Step 2: Build initial messages
            system_prompt = SYSTEM_PROMPT + get_agent_system_prompt()

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""Create a Twitter post. Here are your previous posts (don't repeat):

{previous_posts}

Now create your plan. What tools do you need (if any)?"""}
            ]

            # Step 3: Get plan from LLM
            logger.info("[AUTOPOST] [2/5] Creating plan - calling LLM...")
            plan_result = await self.llm.chat(messages, PLAN_SCHEMA)

            plan = plan_result["plan"]
            tools_list = " -> ".join([s["tool"] for s in plan]) if plan else "none"
            logger.info(f"[AUTOPOST] [2/5] Plan: {len(plan)} tools ({tools_list})")
            logger.info(f"[AUTOPOST] [2/5] Reasoning: {plan_result['reasoning'][:100]}...")

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": json.dumps(plan_result)})

            # Step 4: Validate plan
            self._validate_plan(plan)

            # Step 5: Execute plan with step-by-step LLM reactions
            logger.info("[AUTOPOST] [3/5] Executing tools (step-by-step)...")
            image_bytes = None
            tools_used = []

            for i, step in enumerate(plan):
                tool_name = step["tool"]
                params = step["params"]
                tools_used.append(tool_name)

                if tool_name == "web_search":
                    query = params.get("query", "")
                    logger.info(f"[AUTOPOST] [3/5] [{i+1}/{len(plan)}] web_search - query: {query[:50]}...")

                    result = await TOOLS[tool_name](query)

                    if result.get("error"):
                        logger.warning(f"[AUTOPOST] [3/5] web_search: FAILED - {result['content']}")
                        messages.append({"role": "user", "content": f"Tool result (web_search): {result['content']}"})
                    else:
                        logger.info(f"[AUTOPOST] [3/5] web_search: OK ({len(result['sources'])} sources)")
                        tool_result_msg = f"""Tool result (web_search):
Content: {result['content']}
Sources found: {len(result['sources'])}"""
                        messages.append({"role": "user", "content": tool_result_msg})

                elif tool_name == "generate_image":
                    prompt = params.get("prompt", "")
                    logger.info(f"[AUTOPOST] [3/5] [{i+1}/{len(plan)}] generate_image - prompt: {prompt[:50]}...")

                    image_bytes = await TOOLS[tool_name](prompt)

                    if image_bytes:
                        logger.info(f"[AUTOPOST] [3/5] generate_image: OK ({len(image_bytes)} bytes)")
                        messages.append({"role": "user", "content": "Tool result (generate_image): Image generated successfully. It will be attached to your post."})
                    else:
                        logger.warning(f"[AUTOPOST] [3/5] generate_image: FAILED - continuing without image")
                        messages.append({"role": "user", "content": "Tool result (generate_image): Failed to generate image. Continue without it."})

                # Step-by-step: LLM reacts to tool result
                logger.info(f"[AUTOPOST] [3/5] [{i+1}/{len(plan)}] Getting LLM reaction...")
                reaction = await self.llm.chat(messages, TOOL_REACTION_SCHEMA)
                thinking = reaction.get("thinking", "")
                logger.info(f"[AUTOPOST] [3/5] [{i+1}/{len(plan)}] Thinking: {thinking[:80]}...")
                messages.append({"role": "assistant", "content": thinking})

            # Step 6: Get final post text
            logger.info("[AUTOPOST] [4/5] Generating tweet - calling LLM...")

            messages.append({"role": "user", "content": "Now write your final tweet text (max 280 characters). Just the tweet, nothing else."})

            post_result = await self.llm.chat(messages, POST_TEXT_SCHEMA)
            post_text = post_result["post_text"].strip()

            # Ensure within limit
            if len(post_text) > 280:
                post_text = post_text[:277] + "..."

            logger.info(f"[AUTOPOST] [4/5] Tweet: {post_text[:50]}... ({len(post_text)} chars)")

            # Step 7: Upload image if generated
            media_ids = None
            if image_bytes:
                logger.info("[AUTOPOST] [5/5] Uploading image...")
                try:
                    media_id = await self.twitter.upload_media(image_bytes)
                    media_ids = [media_id]
                    logger.info(f"[AUTOPOST] [5/5] Image uploaded: {media_id}")
                except Exception as e:
                    logger.error(f"[AUTOPOST] [5/5] Image upload FAILED: {e}")
                    image_bytes = None  # Mark as no image for summary

            # Step 8: Post to Twitter
            logger.info("[AUTOPOST] [5/5] Posting to Twitter...")
            tweet_data = await self.twitter.post(post_text, media_ids=media_ids)

            # Step 9: Save to database
            include_picture = image_bytes is not None
            await self.db.save_post(post_text, tweet_data["id"], include_picture)

            # Summary
            duration = round(time.time() - start_time, 1)
            tools_str = ",".join(tools_used) if tools_used else "none"
            logger.info(f"[AUTOPOST] === Completed in {duration}s ===")
            logger.info(f"[AUTOPOST] Summary: tweet_id={tweet_data['id']} | tools={tools_str} | image={'yes' if include_picture else 'no'} | chars={len(post_text)}")

            return {
                "success": True,
                "tweet_id": tweet_data["id"],
                "text": post_text,
                "plan": plan_result["plan"],
                "reasoning": plan_result["reasoning"],
                "tools_used": tools_used,
                "has_image": include_picture,
                "duration_seconds": duration
            }

        except Exception as e:
            duration = round(time.time() - start_time, 1)
            logger.error(f"[AUTOPOST] === FAILED after {duration}s ===")
            logger.error(f"[AUTOPOST] Error: {e}")
            logger.exception(e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": duration
            }
