"""
Agent-based autoposting service.

The agent creates a plan, executes tools step by step,
and generates the final post text.

All in one continuous conversation (user-assistant-user-assistant...).
"""

import json
import logging
from typing import Any

import httpx

from services.database import Database
from services.twitter import TwitterClient
from tools.registry import TOOLS, get_tools_description
from config.personality import SYSTEM_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "anthropic/claude-sonnet-4.5"

# JSON Schema for plan generation
PLAN_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "agent_plan",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Your reasoning about what kind of post to create"
                },
                "plan": {
                    "type": "array",
                    "description": "List of tools to execute in order",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Tool name from available tools"
                            },
                            "params": {
                                "type": "object",
                                "description": "Parameters for the tool",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query (for web_search)"
                                    },
                                    "prompt": {
                                        "type": "string",
                                        "description": "Image prompt (for generate_image)"
                                    }
                                },
                                "additionalProperties": False
                            }
                        },
                        "required": ["tool", "params"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["reasoning", "plan"],
            "additionalProperties": False
        }
    }
}

# JSON Schema for final post text
POST_TEXT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "post_text",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "post_text": {
                    "type": "string",
                    "description": "The final tweet text (max 280 characters)"
                }
            },
            "required": ["post_text"],
            "additionalProperties": False
        }
    }
}


def get_agent_system_prompt() -> str:
    """
    Build agent system prompt with dynamic tools list.

    Tools are loaded from registry, so adding a new tool to TOOLS_SCHEMA
    automatically makes it available to the agent.
    """
    tools_desc = get_tools_description()

    return f"""
## You are an autonomous Twitter posting agent

Your job is to create engaging Twitter posts. You can use tools to gather information or create media.

{tools_desc}

### Planning Rules:
- Look at your previous posts to avoid repetition
- Use tools when they would genuinely improve your post
- generate_image must ALWAYS be the LAST tool in your plan (if used)
- Maximum 3 tools per plan
- You can create a post without any tools if you have a good idea already

### Output Format:
Return JSON with:
- reasoning: Why you chose this approach (1-2 sentences)
- plan: Array of tool calls [{{"tool": "name", "params": {{...}}}}]

Plan can be empty [] if no tools needed.

### Example:
{{"reasoning": "I want to post about current crypto trends with a visual", "plan": [{{"tool": "web_search", "params": {{"query": "crypto market trends today"}}}}, {{"tool": "generate_image", "params": {{"prompt": "abstract digital art representing market volatility"}}}}]}}
"""


class AutoPostService:
    """Agent-based autoposting service with continuous conversation."""

    def __init__(self, db: Database):
        self.db = db
        self.twitter = TwitterClient()
        self.headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pippinlovesdot.com",
            "X-Title": "DOT Twitter Bot"
        }

    async def _llm_call(self, messages: list[dict], response_format: dict) -> dict:
        """
        Make LLM call with messages and structured output.

        Args:
            messages: Conversation history
            response_format: JSON schema for response

        Returns:
            Parsed JSON response
        """
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "response_format": response_format
        }

        logger.info(f"[AGENT] LLM call with {len(messages)} messages")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

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
            plan_result = await self._llm_call(messages, PLAN_SCHEMA)

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

            post_result = await self._llm_call(messages, POST_TEXT_SCHEMA)
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
