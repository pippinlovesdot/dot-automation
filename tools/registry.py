"""
Tool registry for LLM function calling.

Contains all available tools and their JSON schemas for OpenAI-style function calling.
Add your custom tools here to extend the bot's capabilities.
"""

from tools.web_search import web_search
from tools.image_generation import generate_image

# Registry of available tools (function references)
TOOLS = {
    "web_search": web_search,
    "generate_image": generate_image
}

# JSON Schema definitions for tools (OpenAI function calling format)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use this when you need to find recent news, events, prices, facts, or any information that might not be in your training data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results (1-10, default 5)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on a text description. Uses reference images from assets folder for consistent character appearance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the image to generate"
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]


def get_tools_description() -> str:
    """
    Generate human-readable tools description from TOOLS_SCHEMA.

    Used in agent prompts so LLM knows what tools are available.
    When you add a new tool to TOOLS_SCHEMA, it automatically appears in agent prompts.
    """
    lines = ["### Available Tools:"]

    for i, tool_def in enumerate(TOOLS_SCHEMA, 1):
        func = tool_def["function"]
        name = func["name"]
        desc = func["description"]
        params = func["parameters"]["properties"]
        required = func["parameters"].get("required", [])

        lines.append(f"\n**{i}. {name}**")
        lines.append(f"   {desc}")
        lines.append(f"   Parameters:")

        for param_name, param_info in params.items():
            req = "(required)" if param_name in required else "(optional)"
            lines.append(f"   - {param_name}: {param_info['description']} {req}")

    return "\n".join(lines)
