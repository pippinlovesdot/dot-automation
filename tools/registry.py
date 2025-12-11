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
