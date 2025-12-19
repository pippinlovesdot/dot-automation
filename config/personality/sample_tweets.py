"""
Sample tweets that the bot has already made.

These are injected into the prompt to help the LLM avoid repetition.
In a platform context, these would come from the database.
"""

# List of sample tweets (can be populated from database or config)
SAMPLE_TWEETS_LIST: list[str] = []

# Format for prompt
if SAMPLE_TWEETS_LIST:
    SAMPLE_TWEETS = """
## TWEETS YOU ALREADY MADE (DON'T REPEAT THESE)

""" + "\n".join(f"- {tweet}" for tweet in SAMPLE_TWEETS_LIST)
else:
    SAMPLE_TWEETS = ""
