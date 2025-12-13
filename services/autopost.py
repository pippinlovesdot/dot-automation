"""
Agent-based autoposting service.

The agent creates a plan, executes tools step by step,
and generates the final post text.

All in one continuous conversation (user-assistant-user-assistant...).
"""

import json
import logging
from typing import Any

from services.database import Database
from services.llm import LLMClient
from services.twitter import TwitterClient
from tools.registry import TOOLS, get_tools_description
from config.personality import SYSTEM_PROMPT
from config.prompts.agent_autopost import AGENT_PROMPT_TEMPLATE
from config.schemas import PLAN_SCHEMA, POST_TEXT_SCHEMA

logger = logging.getLogger(__name__)


def get_agent_system_prompt() -> str:
    """
    Build agent system prompt with dynamic tools list.

    Tools are loaded from registry, so adding a new tool to TOOLS_SCHEMA
    automatically makes it available to the agent.
    """
    tools_desc = get_tools_description()
    return AGENT_PROMPT_TEMPLATE.format(tools_desc=tools_desc)


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

        logger.info(f"[AGENT] Plan validated: {len(plan)} steps")

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
        logger.info("=" * 60)
        logger.info("[AGENT] Starting agent autopost")
        logger.info("=" * 60)

        try:
            # Step 0: Check if posting is allowed (tier limits)
            if self.tier_manager:
                can_post, reason = self.tier_manager.can_post()
                if not can_post:
                    logger.warning(f"[AGENT] Posting blocked: {reason}")
                    return {
                        "success": False,
                        "error": f"posting_blocked: {reason}",
                        "tier": self.tier_manager.tier,
                        "usage_percent": self.tier_manager.get_usage_percent()
                    }

            # Step 1: Get context
            logger.info("[AGENT] Step 1: Getting context from database")
            previous_posts = await self.db.get_recent_posts_formatted(limit=50)
            logger.info(f"[AGENT] Loaded {len(previous_posts)} chars of previous posts context")

            # Step 2: Build initial messages
            system_prompt = SYSTEM_PROMPT + get_agent_system_prompt()

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""Create a Twitter post. Here are your previous posts (don't repeat):

{previous_posts}

Now create your plan. What tools do you need (if any)?"""}
            ]

            # Step 3: Get plan from LLM
            logger.info("[AGENT] Step 2: Getting plan from LLM")
            plan_result = await self.llm.chat(messages, PLAN_SCHEMA)

            logger.info(f"[AGENT] Plan received:")
            logger.info(f"[AGENT]   Reasoning: {plan_result['reasoning']}")
            logger.info(f"[AGENT]   Plan: {json.dumps(plan_result['plan'], indent=2)}")

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": json.dumps(plan_result)})

            # Step 4: Validate plan
            logger.info("[AGENT] Step 3: Validating plan")
            plan = plan_result["plan"]
            self._validate_plan(plan)

            # Step 5: Execute plan (each tool result goes back as user message)
            logger.info("[AGENT] Step 4: Executing plan")
            image_bytes = None

            for i, step in enumerate(plan):
                tool_name = step["tool"]
                params = step["params"]

                logger.info(f"[AGENT] Executing step {i+1}/{len(plan)}: {tool_name}")
                logger.info(f"[AGENT]   Params: {params}")

                try:
                    if tool_name == "web_search":
                        result = await TOOLS[tool_name](params.get("query", ""))

                        # Add tool result as user message
                        tool_result_msg = f"""Tool result (web_search):
Content: {result['content']}
Sources found: {len(result['sources'])}"""

                        messages.append({"role": "user", "content": tool_result_msg})
                        logger.info(f"[AGENT]   web_search completed: {len(result['sources'])} sources")
                        logger.info(f"[AGENT]   Content preview: {result['content'][:200]}...")

                    elif tool_name == "generate_image":
                        image_bytes = await TOOLS[tool_name](params.get("prompt", ""))

                        # Add tool result as user message
                        messages.append({"role": "user", "content": "Tool result (generate_image): Image generated successfully. It will be attached to your post."})
                        logger.info(f"[AGENT]   generate_image completed: {len(image_bytes)} bytes")

                except Exception as e:
                    logger.error(f"[AGENT]   Tool {tool_name} failed: {e}")
                    messages.append({"role": "user", "content": f"Tool result ({tool_name}): Error - {e}"})

            # Step 6: Get final post text
            logger.info("[AGENT] Step 5: Getting final post text")

            messages.append({"role": "user", "content": "Now write your final tweet text (max 280 characters). Just the tweet, nothing else."})

            post_result = await self.llm.chat(messages, POST_TEXT_SCHEMA)
            post_text = post_result["post_text"].strip()

            # Ensure within limit
            if len(post_text) > 280:
                post_text = post_text[:277] + "..."

            logger.info(f"[AGENT] Final post text ({len(post_text)} chars): {post_text}")

            # Step 7: Upload image if generated
            media_ids = None
            if image_bytes:
                logger.info("[AGENT] Step 6: Uploading image to Twitter")
                try:
                    media_id = await self.twitter.upload_media(image_bytes)
                    media_ids = [media_id]
                    logger.info(f"[AGENT]   Image uploaded: media_id={media_id}")
                except Exception as e:
                    logger.error(f"[AGENT]   Image upload failed: {e}")

            # Step 8: Post to Twitter
            logger.info("[AGENT] Step 7: Posting to Twitter")
            tweet_data = await self.twitter.post(post_text, media_ids=media_ids)
            logger.info(f"[AGENT]   Posted! tweet_id={tweet_data['id']}")

            # Step 9: Save to database
            logger.info("[AGENT] Step 8: Saving to database")
            include_picture = image_bytes is not None
            await self.db.save_post(post_text, tweet_data["id"], include_picture)

            logger.info("=" * 60)
            logger.info("[AGENT] Agent autopost completed successfully!")
            logger.info("=" * 60)

            return {
                "success": True,
                "tweet_id": tweet_data["id"],
                "text": post_text,
                "plan": plan_result["plan"],
                "reasoning": plan_result["reasoning"],
                "conversation_length": len(messages)
            }

        except Exception as e:
            logger.error(f"[AGENT] Agent autopost failed: {e}")
            logger.exception(e)
            return {
                "success": False,
                "error": str(e)
            }
