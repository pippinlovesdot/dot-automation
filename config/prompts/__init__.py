"""
Prompts module - LLM prompts for different services.

Contains prompt templates for:
- agent_autopost.py: Autoposting agent prompts
- mention_selector.py: Legacy mention selector (v1.2)
- mention_selector_agent.py: Agent-based mention selection (v1.3)
- mention_reply_agent.py: Agent-based mention reply planning (v1.3)
"""

from config.prompts.agent_autopost import AUTOPOST_AGENT_PROMPT
from config.prompts.mention_selector import MENTION_SELECTOR_PROMPT
from config.prompts.mention_selector_agent import MENTION_SELECTOR_AGENT_PROMPT
from config.prompts.mention_reply_agent import MENTION_REPLY_AGENT_PROMPT

__all__ = [
    "AUTOPOST_AGENT_PROMPT",
    "MENTION_SELECTOR_PROMPT",
    "MENTION_SELECTOR_AGENT_PROMPT",
    "MENTION_REPLY_AGENT_PROMPT",
]
