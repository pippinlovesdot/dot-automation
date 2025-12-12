"""
JSON Schemas - Structured output formats for LLM responses.

All JSON schemas used for structured LLM output are defined here.
"""

# Schema for mention selection and response
MENTION_SELECTOR_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "mention_selector",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "selected_tweet_id": {
                    "type": "string",
                    "description": "The tweet_id of the mention you want to reply to. Empty string if none worth replying."
                },
                "text": {
                    "type": "string",
                    "description": "Your reply text (max 280 chars). Empty if not replying."
                },
                "include_picture": {
                    "type": "boolean",
                    "description": "Whether to include a generated picture with your reply."
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief reason why you chose this mention (or why you're not replying)."
                }
            },
            "required": ["selected_tweet_id", "text", "include_picture", "reasoning"],
            "additionalProperties": False
        }
    }
}

# Schema for agent plan generation
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

# Schema for final post text
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
