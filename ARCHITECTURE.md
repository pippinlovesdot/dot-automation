# Architecture Guide for AI Assistants

This file is designed for AI tools (ChatGPT, Claude, Cursor, Copilot, etc.) to quickly understand the codebase and help users modify or extend the bot.

---

## Project Overview

**Purpose:** Autonomous Twitter bot that generates original content and responds to mentions using LLM.

**Core behavior:**
- Posts original tweets on a schedule (autoposting)
- Monitors mentions and replies to selected ones (mention handling)
- Optionally generates images for posts and replies
- All content generation is powered by LLM with structured JSON output

**Tech stack:**
- Python 3.10+ with async/await
- FastAPI for HTTP server
- APScheduler for cron-like job scheduling
- PostgreSQL for persistence (asyncpg driver)
- OpenRouter API for LLM inference (Claude Sonnet 4.5)
- OpenRouter API for image generation (Gemini 3 Pro)
- Twitter API v2 via tweepy

---

## File Structure

```
main.py                     # Application entry point
config/
  __init__.py
  settings.py               # Environment configuration
  personality.py            # Bot personality definition
services/
  __init__.py
  autopost.py               # Autoposting service
  mentions.py               # Mention handling service
  llm.py                    # LLM client
  twitter.py                # Twitter API client
  image_gen.py              # Image generation service
  database.py               # Database operations
tools/
  __init__.py
  registry.py               # Tool registry for function calling
assets/                     # Reference images for generation
.env.example                # Environment template
requirements.txt            # Python dependencies
```

---

## Detailed File Descriptions

### main.py
FastAPI application with lifespan management. On startup:
1. Connects to PostgreSQL database
2. Initializes AutoPostService and MentionHandler
3. Schedules two recurring jobs via APScheduler:
   - `autopost_job` — runs every POST_INTERVAL_MINUTES
   - `mentions_job` — runs every MENTIONS_INTERVAL_MINUTES
4. Starts the scheduler

HTTP endpoints:
- `GET /health` — health check with scheduler status
- `GET /callback` — OAuth callback for Twitter authentication
- `POST /trigger-post` — manually trigger autopost
- `POST /trigger-mentions` — manually trigger mention processing

### config/settings.py
Pydantic Settings class that loads configuration from environment variables and `.env` file. All settings are typed and validated on startup.

Key settings:
- `openrouter_api_key` — API key for OpenRouter (LLM + image gen)
- `twitter_*` — Twitter API credentials (5 values)
- `database_url` — PostgreSQL connection string
- `post_interval_minutes` — autopost frequency (default: 30)
- `mentions_interval_minutes` — mention check frequency (default: 20)
- `enable_image_generation` — toggle for image generation (default: true)

### config/personality.py
Contains `SYSTEM_PROMPT` constant — the complete personality definition for the bot. This prompt is prepended to all LLM calls and defines:
- Personality traits and character
- Communication style (tone, grammar, punctuation)
- Topics to discuss and avoid
- Behavioral rules (no hashtags, no engagement bait, etc.)
- Example tweets that capture the vibe

**To change the bot's personality, edit this file.**

### services/autopost.py
`AutoPostService` class handles scheduled tweet generation.

Flow:
1. Fetches last 50 posts from database for context
2. Calls LLM with structured output format requesting `{text, include_picture}`
3. If `include_picture=true` and image generation enabled, generates image
4. Posts tweet to Twitter (with optional media)
5. Saves post to database

Structured output schema:
```json
{
  "text": "string (max 280 chars)",
  "include_picture": "boolean"
}
```

### services/mentions.py
`MentionHandler` class processes Twitter mentions.

Flow:
1. Fetches recent mentions from Twitter API
2. Filters out already-processed mentions using database
3. Sends all unprocessed mentions to LLM in single request
4. LLM selects ONE mention to reply to (or none if all low quality)
5. LLM returns selection + reply text + image decision
6. If mention selected, optionally generates image
7. Posts reply to Twitter
8. Saves interaction to database

Structured output schema:
```json
{
  "selected_tweet_id": "string (tweet ID to reply to, empty if none)",
  "text": "string (reply text, max 280 chars)",
  "include_picture": "boolean",
  "reasoning": "string (why this mention was selected)"
}
```

**Design decision:** LLM evaluates ALL pending mentions and picks the best one, rather than replying to every mention. This creates more authentic engagement.

### services/llm.py
`LLMClient` class — async client for OpenRouter API.

Methods:
- `generate(system, user)` — simple text completion
- `generate_structured(system, user, response_format)` — JSON structured output
- `chat(messages, tools)` — chat completion with optional tool calling

Uses `anthropic/claude-sonnet-4.5` model by default (configurable via TEXT_MODEL constant).

### services/twitter.py
`TwitterClient` class — Twitter API integration using tweepy.

Methods:
- `post(text, media_ids)` — post new tweet (API v2)
- `reply(text, reply_to_tweet_id, media_ids)` — reply to tweet (API v2)
- `upload_media(image_bytes)` — upload image (API v1.1, required for media)
- `get_me()` — get authenticated user info
- `get_mentions(since_id)` — fetch mentions (API v2)

Note: Media upload uses API v1.1 because v2 doesn't support it yet.

### services/image_gen.py
`ImageGenerator` class — image generation via OpenRouter.

Uses `google/gemini-3-pro-image-preview` model. Supports reference images from `assets/` folder for consistent character appearance.

Flow:
1. Loads reference images from `assets/` folder (up to 2 randomly selected)
2. Sends reference images + text prompt to model
3. Receives base64-encoded image in response
4. Returns raw image bytes

### services/database.py
`Database` class — async PostgreSQL client using asyncpg.

Tables (auto-created on startup):
- `posts` — stores all posted tweets
- `mentions` — stores mention interactions
- `bot_state` — key-value store for state (e.g., last_mention_id)

Key methods:
- `get_recent_posts_formatted(limit)` — posts as formatted string for LLM context
- `save_post(text, tweet_id, include_picture)` — save new post
- `save_mention(...)` — save mention interaction
- `mention_exists(tweet_id)` — check if mention already processed
- `get_state(key)` / `set_state(key, value)` — state management

### tools/registry.py
Tool registry for LLM function calling. Contains:
- `TOOLS` — dict mapping tool names to async functions
- `TOOLS_SCHEMA` — list of JSON schemas in OpenAI function calling format

Currently empty, ready for extension. To add a tool:
1. Create tool function in `tools/` directory
2. Import and add to `TOOLS` dict
3. Add JSON schema to `TOOLS_SCHEMA` list

---

## Database Schema

```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    tweet_id VARCHAR(50),
    include_picture BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mentions (
    id SERIAL PRIMARY KEY,
    tweet_id VARCHAR(50) UNIQUE,
    author_handle VARCHAR(50),
    author_text TEXT,
    our_reply TEXT,
    action VARCHAR(20),  -- 'replied', 'ignored', 'tool_used'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bot_state (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Data Flow Diagrams

### Autoposting
```
[Scheduler]
    → AutoPostService.run()
    → Database.get_recent_posts_formatted(50)
    → LLMClient.generate_structured()
        → returns {text, include_picture}
    → [if include_picture] ImageGenerator.generate()
    → [if include_picture] TwitterClient.upload_media()
    → TwitterClient.post()
    → Database.save_post()
```

### Mention Handling
```
[Scheduler]
    → MentionHandler.process_mentions_batch()
    → TwitterClient.get_mentions()
    → Database.mention_exists() [filter processed]
    → LLMClient.generate_structured()
        → returns {selected_tweet_id, text, include_picture, reasoning}
    → [if selected] ImageGenerator.generate() [optional]
    → [if selected] TwitterClient.upload_media() [optional]
    → [if selected] TwitterClient.reply()
    → Database.save_mention()
```

---

## Extension Points

### Adding a new tool
1. Create `tools/my_tool.py`:
```python
async def my_tool(query: str) -> str:
    # Implementation
    return result
```

2. Update `tools/registry.py`:
```python
from tools.my_tool import my_tool

TOOLS = {
    "my_tool": my_tool
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "my_tool",
            "description": "What this tool does",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "..."}
                },
                "required": ["query"]
            }
        }
    }
]
```

3. Update `services/mentions.py` to handle tool execution in the response flow.

### Changing LLM model
Edit `services/llm.py`, change `TEXT_MODEL` constant to any OpenRouter model ID.

### Changing image model
Edit `services/image_gen.py`, change `IMAGE_MODEL` constant.

### Adding new scheduled job
In `main.py` lifespan function:
```python
scheduler.add_job(
    my_function,
    "interval",
    minutes=N,
    id="my_job",
    replace_existing=True
)
```

---

## API Reference

### OpenRouter
- Base URL: `https://openrouter.ai/api/v1/chat/completions`
- Auth: Bearer token in Authorization header
- Models used:
  - `anthropic/claude-sonnet-4.5` — text generation
  - `google/gemini-3-pro-image-preview` — image generation

### Twitter API
- API v2 for tweets, mentions, user info
- API v1.1 for media uploads only
- Auth: OAuth 1.0a (consumer key/secret + access token/secret)
- Bearer token for read-only operations

### PostgreSQL
- Connection via asyncpg
- Connection pooling enabled
- Tables auto-created on startup if not exist
