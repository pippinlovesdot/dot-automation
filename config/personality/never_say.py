"""
Topics or things the bot should never say.

These are injected into the prompt to prevent certain content.
In a platform context, this would come from the database.
"""

# Forbidden topics/content (can be populated from database or config)
NEVER_SAY_CONTENT: str = ""

# Format for prompt
if NEVER_SAY_CONTENT:
    NEVER_SAY = f"""
## NEVER SAY THESE TOPICS OR THINGS

{NEVER_SAY_CONTENT}
"""
else:
    NEVER_SAY = ""
