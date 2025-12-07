"""
Tool registry for LLM function calling.

Contains all available tools and their JSON schemas for OpenAI-style function calling.
Add your custom tools here to extend the bot's capabilities.
"""

# Registry of available tools (function references)
# Example: TOOLS = {"web_search": web_search}
TOOLS = {}

# JSON Schema definitions for tools (OpenAI function calling format)
# Example schema:
# {
#     "type": "function",
#     "function": {
#         "name": "tool_name",
#         "description": "What this tool does",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "param_name": {
#                     "type": "string",
#                     "description": "Parameter description"
#                 }
#             },
#             "required": ["param_name"]
#         }
#     }
# }
TOOLS_SCHEMA = []
