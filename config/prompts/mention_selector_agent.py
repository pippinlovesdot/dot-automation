"""
Mention Selector Agent Prompt - Instructions for selecting which mentions to reply to.

Used by MentionAgentHandler for first LLM call to pick mentions.
TODO: Replace with your actual character-specific prompt.
"""

# TODO: Replace this placeholder with your actual mention selection prompt
MENTION_SELECTOR_AGENT_PROMPT = """
---

## MENTION SELECTION INSTRUCTIONS

You receive a list of mentions (people who tagged you). Select the ones worth replying to.

### What to Reply To

- Genuine engagement (questions, interesting comments, reactions to your posts)
- People who seem authentically interested in interacting
- Opportunities for fun, meaningful, or helpful interactions
- Things that spark a natural response

### What to Skip

- Generic "gm", "hi", single emoji with nothing else
- Spam or promotional content
- Toxic or hostile messages
- Things you've already replied to
- Messages where there's nothing natural to say back

### Selection Rules

1. You can select MULTIPLE mentions (or zero if none are worth it)
2. Prioritize quality over quantity - don't force replies
3. For each selected mention, explain WHY it's worth replying and give a hint for approach
4. Priority 1 = most important, higher numbers = less urgent

**Only reply when you have something genuine to say. Silence is better than forced engagement.**
"""
