"""
Unified Agent Service.

Single agent that handles both posting and replying using Structured Output.
Replaces separate autopost and mentions services.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from services.database import Database
from services.llm import LLMClient
from services.twitter import TwitterClient
from tools.registry import (
    get_tools_for_mode,
    get_tools_description_for_mode,
    get_tools_enum_for_mode,
    get_tools_params_schema,
    get_tool_func
)
from config.personality import SYSTEM_PROMPT
from config.prompts.unified_agent import AGENT_INSTRUCTIONS
from config.settings import settings

logger = logging.getLogger(__name__)


def build_step_decision_schema(tier: str) -> dict:
    """
    Build JSON schema for agent step decision dynamically from registry.

    Args:
        tier: "free" or "basic+"

    Returns:
        JSON schema for structured output.
    """
    tools_enum = get_tools_enum_for_mode("unified", tier)
    params_schema = get_tools_params_schema()

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "step_decision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "thinking": {
                        "type": "string",
                        "description": "Your reasoning about what to do next"
                    },
                    "tool": {
                        "type": "string",
                        "enum": tools_enum,
                        "description": "Which tool to use"
                    },
                    "params": {
                        "type": "object",
                        "description": "Parameters for the tool",
                        "properties": params_schema,
                        "additionalProperties": False
                    }
                },
                "required": ["thinking", "tool", "params"],
                "additionalProperties": False
            }
        }
    }


class UnifiedAgent:
    """
    Unified agent that handles posting and replying.

    Uses Structured Output to let the LLM decide what to do step by step.
    Tools are discovered from registry.
    """

    def __init__(self, db: Database, tier_manager=None):
        self.db = db
        self.llm = LLMClient()
        self.twitter = TwitterClient()
        self.tier_manager = tier_manager

        # Tracking for this cycle
        self.posts_this_cycle = 0
        self.replies_this_cycle = 0
        self.tools_used_for_current_action: list[str] = []

    def _get_tier(self) -> str:
        """Get current tier string."""
        if self.tier_manager:
            can_use_mentions, _ = self.tier_manager.can_use_mentions()
            return "free" if not can_use_mentions else "basic+"
        return "basic+"

    async def _build_context(self) -> str:
        """Build context string for the agent."""
        # Get recent actions
        recent_actions = await self.db.get_recent_actions_formatted(limit=20)

        # Get rate limits (tier-based)
        posts_today = await self.db.count_actions_today("post")
        replies_today = await self.db.count_actions_today("reply")

        daily_post_limit, daily_reply_limit = self.tier_manager.get_daily_limits()

        posts_remaining = max(0, daily_post_limit - posts_today)
        replies_remaining = max(0, daily_reply_limit - replies_today)

        # Current time
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Tier info
        tier = self._get_tier()
        tier_info = f"\nTier: {tier.upper()}"
        if tier == "free":
            tier_info += " (mentions/replies not available)"

        context = f"""## YOUR RECENT ACTIONS

{recent_actions}

## RATE LIMITS

- Posts today: {posts_today}/{daily_post_limit} ({posts_remaining} remaining)
- Replies today: {replies_today}/{daily_reply_limit} ({replies_remaining} remaining){tier_info}

## CURRENT TIME

{now}"""

        return context

    async def _execute_tool(self, tool_name: str, params: dict) -> str:
        """
        Execute a tool by name with given params.

        Passes context (twitter, db, tier_manager) to tool function.
        Tracks tools used for the current action (reply/post).
        """
        tool_func = get_tool_func(tool_name)

        if not tool_func:
            return f"Error: Unknown tool '{tool_name}'"

        # Track tool usage (except action tools and finish)
        if tool_name not in ["create_post", "create_reply", "finish_cycle"]:
            self.tools_used_for_current_action.append(tool_name)

        try:
            # Build kwargs with context
            kwargs = {
                "twitter": self.twitter,
                "db": self.db,
                "tier_manager": self.tier_manager,
                **params
            }

            # For create_reply/create_post, pass the tools_used list
            if tool_name in ["create_post", "create_reply"]:
                kwargs["tools_used"] = self.tools_used_for_current_action.copy()

            result = await tool_func(**kwargs)

            # Track posts/replies and reset tools_used
            if tool_name == "create_post" and "successfully" in result.lower():
                self.posts_this_cycle += 1
                self.tools_used_for_current_action = []  # Reset for next action
            elif tool_name == "create_reply" and "successfully" in result.lower():
                self.replies_this_cycle += 1
                self.tools_used_for_current_action = []  # Reset for next action

            return result

        except Exception as e:
            logger.error(f"[AGENT] Tool {tool_name} failed: {e}")
            return f"Error executing {tool_name}: {e}"

    async def run(self) -> dict[str, Any]:
        """
        Run the unified agent cycle.

        Returns:
            Summary of what happened.
        """
        start_time = time.time()
        logger.info("[AGENT] === Starting unified agent cycle ===")

        self.posts_this_cycle = 0
        self.replies_this_cycle = 0
        self.tools_used_for_current_action = []

        try:
            # Get tier and build schema
            tier = self._get_tier()
            schema = build_step_decision_schema(tier)
            tools_desc = get_tools_description_for_mode("unified", tier)

            logger.info(f"[AGENT] Tier: {tier.upper()}")

            # Build context
            context = await self._build_context()

            # Build system prompt
            system_prompt = f"""{SYSTEM_PROMPT}

---

{AGENT_INSTRUCTIONS}

---

{tools_desc}

---

{context}"""

            # Initialize conversation
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "It's time for your next cycle. Decide what to do and use a tool."}
            ]

            # Tool use loop
            max_iterations = 30
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Call LLM with structured output
                result = await self.llm.chat(messages, schema)

                thinking = result.get("thinking", "")
                tool_name = result.get("tool", "")
                params = result.get("params", {})

                logger.info(f"[AGENT] [{iteration}/{max_iterations}] Tool: {tool_name}")

                # Add assistant response to messages
                messages.append({"role": "assistant", "content": json.dumps(result)})

                # Execute tool
                tool_result = await self._execute_tool(tool_name, params)

                # Check if cycle finished
                if tool_name == "finish_cycle" or "CYCLE_FINISHED" in tool_result:
                    break

                # Add tool result to messages
                messages.append({"role": "user", "content": f"Tool result ({tool_name}):\n{tool_result}\n\nDecide what to do next."})

            # Summary
            duration = round(time.time() - start_time, 1)
            logger.info(f"[AGENT] === Completed in {duration}s ===")
            logger.info(f"[AGENT] Summary: posts={self.posts_this_cycle}, replies={self.replies_this_cycle}, iterations={iteration}")

            return {
                "success": True,
                "posts": self.posts_this_cycle,
                "replies": self.replies_this_cycle,
                "iterations": iteration,
                "duration_seconds": duration
            }

        except Exception as e:
            duration = round(time.time() - start_time, 1)
            logger.error(f"[AGENT] === FAILED after {duration}s ===")
            logger.error(f"[AGENT] Error: {e}")
            logger.exception(e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": duration
            }
