"""
Finish the agent cycle.

Control flow tool to signal the end of the current agent cycle.
"""

import logging

logger = logging.getLogger(__name__)

# Tool configuration for auto-discovery
TOOL_CONFIG = {
    "name": "finish_cycle",
    "description": "End this agent cycle when you're done or have nothing more to do",
    "params": {
        "reasoning": {
            "type": "string",
            "description": "Why you're finishing the cycle",
            "required": True
        }
    }
}


async def finish_cycle(reasoning: str = "", **kwargs) -> str:
    """
    Signal the end of the agent cycle.

    Args:
        reasoning: Why the cycle is being finished.
        **kwargs: Additional context (not used).

    Returns:
        Special marker string that tells the agent loop to stop.
    """
    logger.info(f"[FINISH_CYCLE] reasoning: {reasoning}")
    return f"CYCLE_FINISHED: {reasoning}"
