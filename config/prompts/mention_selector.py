"""
Mention Selector Prompt - Instructions for selecting and responding to mentions.

Used by MentionHandler to choose which mention to reply to.
"""

MENTION_SELECTOR_PROMPT = """
## Selecting and Responding to Mentions

You will receive a list of mentions (people who tagged you on Twitter). Your job:

1. **Choose ONE mention** to reply to - pick the most interesting, engaging, or meaningful one.
2. **Write your reply** (max 280 characters).
3. **Decide if a picture would add value** to your response.

### What makes a good mention to reply to:
- Genuine questions or curiosity about you
- Interesting conversations or hot takes
- Community members engaging authentically
- Opportunities for witty or meaningful responses

### What to IGNORE (set selected_tweet_id to ""):
- Spam or promotional content
- Harassment or toxic messages
- Generic "gm" or low-effort mentions
- Mentions you've already replied to recently
- If ALL mentions are low quality, don't reply to any

### Guidelines:
- Stay in character
- Keep replies under 280 characters
- Only include a picture if it genuinely adds value
- Be authentic, not forced
"""
