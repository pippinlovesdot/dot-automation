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
  models.py                 # Model configuration (LLM_MODEL, IMAGE_MODEL)
  schemas.py                # JSON schemas for LLM responses
  personality/              # Modular character definition
    __init__.py             # Combines parts into SYSTEM_PROMPT
    backstory.py            # Origin story
    beliefs.py              # Values and priorities
    instructions.py         # Communication style
  prompts/                  # LLM prompts
    agent_autopost.py       # Agent planning prompt
    mention_selector.py     # Mention handling prompt
utils/
  __init__.py
  api.py                    # OpenRouter API configuration
services/
  __init__.py
  autopost.py               # Autoposting service (uses LLMClient)
  mentions.py               # Mention handling service
  tier_manager.py           # Twitter API tier detection and limits
  llm.py                    # LLM client (generate, generate_structured, chat)
  twitter.py                # Twitter API client
  database.py               # Database operations + metrics
tools/
  __init__.py
  registry.py               # Tool registry for function calling
  web_search.py             # Web search via OpenRouter plugins
  image_generation.py       # Image generation tool
assets/                     # Reference images for generation
.env.example                # Environment template
requirements.txt            # Python dependencies
```

---

## Detailed File Descriptions

### main.py
FastAPI application with lifespan management. On startup:
1. Connects to PostgreSQL database
2. Initializes TierManager, AutoPostService, and MentionHandler
3. Logs connected Twitter account info
4. Schedules hourly tier refresh via APScheduler
5. Starts the scheduler

HTTP endpoints:
- `GET /health` — health check with database, scheduler, tier status
- `GET /metrics` — bot statistics (posts/mentions counts, timestamps)
- `GET /callback` — OAuth callback for Twitter authentication
- `POST /trigger-post` — manually trigger agent-based autopost
- `GET /check-mentions` — fetch mentions without processing (dry run)
- `POST /process-mentions` — fetch and process mentions
- `GET /tier-status` — get current tier and usage stats
- `POST /tier-refresh` — force tier re-detection
- `POST /webhook/mentions` — Twitter webhook endpoint
- `GET /webhook/mentions` — Twitter CRC challenge verification

### utils/api.py
Centralized OpenRouter API configuration.

**Contents:**
- `OPENROUTER_URL` — API endpoint constant
- `get_openrouter_headers()` — Returns headers with authorization, content-type, referer

**Used by:** services/llm.py, tools/web_search.py, tools/image_generation.py

### config/models.py
Centralized model configuration.

```python
LLM_MODEL = "anthropic/claude-sonnet-4.5"
IMAGE_MODEL = "google/gemini-3-pro-image-preview"
```

**Used by:** services/llm.py, tools/web_search.py, tools/image_generation.py

### config/settings.py
Pydantic Settings class that loads configuration from environment variables and `.env` file. All settings are typed and validated on startup.

Key settings:
- `openrouter_api_key` — API key for OpenRouter (LLM + image gen)
- `twitter_*` — Twitter API credentials (5 values)
- `database_url` — PostgreSQL connection string
- `post_interval_minutes` — autopost frequency (default: 30)
- `mentions_interval_minutes` — mention check frequency (default: 20)
- `enable_image_generation` — toggle for image generation (default: true)

### config/personality/
Modular character definition split into three files:

**`backstory.py`** — `BACKSTORY` constant
- Origin story and background
- Who the character is

**`beliefs.py`** — `BELIEFS` constant
- Personality traits
- Topics of interest
- Values and worldview

**`instructions.py`** — `INSTRUCTIONS` constant
- Communication style (tone, grammar, punctuation)
- What NOT to do
- Example tweets

**`__init__.py`** — Combines all parts into `SYSTEM_PROMPT`:
```python
SYSTEM_PROMPT = BACKSTORY + BELIEFS + INSTRUCTIONS
```

**To change the bot's personality, edit the individual files.**

### config/prompts/
LLM prompts for specific services:

**`agent_autopost.py`** — `AGENT_PROMPT_TEMPLATE`
- Instructions for autonomous posting agent
- Contains `{tools_desc}` placeholder for dynamic tool injection

**`mention_selector.py`** — `MENTION_SELECTOR_PROMPT`
- Legacy mention selector (v1.2)
- Criteria for what to reply to and what to ignore

**`mention_selector_agent.py`** — `MENTION_SELECTOR_AGENT_PROMPT` (v1.3)
- Instructions for selecting multiple mentions worth replying to
- Returns array of selected mentions with priority

**`mention_reply_agent.py`** — `MENTION_REPLY_AGENT_PROMPT` (v1.3)
- Instructions for planning and generating individual replies
- Contains `{tools_desc}` placeholder for dynamic tool injection

### config/schemas.py
JSON schemas for structured LLM output:

**Autopost schemas:**
- **`PLAN_SCHEMA`** — Agent plan format `{reasoning, plan: [{tool, params}]}`
- **`POST_TEXT_SCHEMA`** — Final tweet format `{post_text}`

**Legacy mention schema (v1.2):**
- **`MENTION_SELECTOR_SCHEMA`** — Single mention response `{selected_tweet_id, text, include_picture, reasoning}`

**Agent-based mention schemas (v1.3):**
- **`MENTION_SELECTION_SCHEMA`** — Array of selected mentions `{selected_mentions: [{tweet_id, priority, reasoning, suggested_approach}]}`
- **`MENTION_PLAN_SCHEMA`** — Reply plan format `{reasoning, plan: [{tool, params}]}`
- **`REPLY_TEXT_SCHEMA`** — Final reply format `{reply_text}`

### services/autopost.py
`AutoPostService` class — agent-based autoposting with tool execution.

**Agent Architecture:**
The agent operates in a continuous conversation, creating a plan and executing tools step by step.

**Flow:**
1. Fetches last 50 posts from database for context
2. Builds system prompt: personality + agent instructions + dynamic tools list
3. **LLM Call #1:** Agent creates a plan `{reasoning, plan: [{tool, params}]}`
4. Validates plan (max 3 tools, generate_image must be last)
5. Executes each tool, adding results back to conversation as user messages
6. **LLM Call #2:** Agent generates final tweet text based on all context
7. Uploads image if generated
8. Posts tweet to Twitter
9. Saves to database

**Plan Schema:**
```json
{
  "reasoning": "Why this approach (1-2 sentences)",
  "plan": [
    {"tool": "web_search", "params": {"query": "..."}},
    {"tool": "generate_image", "params": {"prompt": "..."}}
  ]
}
```

**Key design decisions:**
- Agent can choose to use no tools (empty plan `[]`) if it has a good idea already
- Tool results become part of the conversation, informing the final tweet
- `generate_image` must always be the last tool (image is based on gathered info)
- Dynamic tool discovery via `get_tools_description()` from registry

### services/mentions.py
`MentionAgentHandler` class — agent-based mention processing (v1.3).

**Agent Architecture (3 LLM calls per mention):**

**Flow:**
1. Fetches recent mentions from Twitter API
2. Filters out already-processed mentions using database
3. Optional: Filters by whitelist (for testing)
4. **LLM Call #1:** Select mentions worth replying to (returns array)
5. For EACH selected mention:
   a. Get user conversation history from database
   b. **LLM Call #2:** Create plan `{reasoning, plan: [{tool, params}]}`
   c. Execute tools (web_search, generate_image)
   d. **LLM Call #3:** Generate final reply text
   e. Upload image if generated
   f. Post reply to Twitter
   g. Save to database with tools_used tracking
6. Return batch summary

**Selection Schema (LLM #1):**
```json
{
  "selected_mentions": [
    {
      "tweet_id": "123456",
      "priority": 1,
      "reasoning": "Why this mention is worth replying to",
      "suggested_approach": "Brief hint for how to reply"
    }
  ]
}
```

**Plan Schema (LLM #2):**
```json
{
  "reasoning": "How to approach this reply",
  "plan": [
    {"tool": "web_search", "params": {"query": "..."}},
    {"tool": "generate_image", "params": {"prompt": "..."}}
  ]
}
```

**Design decisions:**
- LLM selects MULTIPLE mentions (with priority) instead of just one
- Each mention gets individual planning and tool execution
- User conversation history provides context for personalized replies
- Empty plan `[]` is valid — most replies don't need tools
- Tracks which tools were used for analytics
- Plan validation (v1.3.2): max 3 tools, generate_image must be last

### services/llm.py
`LLMClient` class — async client for OpenRouter API.

Methods:
- `generate(system, user)` — simple text completion
- `generate_structured(system, user, response_format)` — JSON structured output
- `chat(messages, response_format)` — multi-turn chat with optional structured output

Uses model from `config/models.py` (`LLM_MODEL`). The `chat()` method is used by `AutoPostService` for agent conversations.

### services/twitter.py
`TwitterClient` class — Twitter API integration using tweepy.

Methods:
- `post(text, media_ids)` — post new tweet (API v2)
- `reply(text, reply_to_tweet_id, media_ids)` — reply to tweet (API v2)
- `upload_media(image_bytes)` — upload image (API v1.1, required for media)
- `get_me()` — get authenticated user info
- `get_mentions(since_id)` — fetch mentions (API v2)

Note: Media upload uses API v1.1 because v2 doesn't support it yet.

### services/database.py
`Database` class — async PostgreSQL client using asyncpg.

Tables (auto-created on startup):
- `posts` — stores all posted tweets
- `mentions` — stores mention interactions
- `bot_state` — key-value store for state (e.g., last_mention_id)

**Key methods:**
- `get_recent_posts_formatted(limit)` — posts as formatted string for LLM context
- `save_post(text, tweet_id, include_picture)` — save new post
- `save_mention(...)` — save mention interaction
- `mention_exists(tweet_id)` — check if mention already processed
- `get_state(key)` / `set_state(key, value)` — state management
- `get_user_mention_history(author_handle)` — conversation history with user

**Metrics methods (v1.2.2):**
- `ping()` — health check (returns bool)
- `count_posts()` / `count_posts_today()` — post counts
- `count_mentions()` / `count_mentions_today()` — mention counts
- `get_last_post_time()` / `get_last_mention_time()` — timestamps

### services/tier_manager.py
`TierManager` class — automatic Twitter API tier detection and limit management.

**Initialization:**
- Called on application startup
- Queries Twitter Usage API (`GET /2/usage/tweets`)
- Determines tier from `project_cap` value
- Schedules hourly refresh to detect subscription upgrades

**Key methods:**
- `initialize()` — detect tier on startup
- `detect_tier()` — query Usage API and determine tier
- `maybe_refresh_tier()` — refresh if interval passed (called hourly by scheduler)
- `can_post()` — returns `(bool, reason)` - checks if posting allowed
- `can_use_mentions()` — returns `(bool, reason)` - checks if mentions available on tier
- `get_status()` — returns full status dict for `/tier-status` endpoint

**Tier detection logic:**
```python
if project_cap >= 10_000_000: tier = "enterprise"
elif project_cap >= 1_000_000: tier = "pro"
elif project_cap >= 10_000: tier = "basic"
elif project_cap <= 500: tier = "free"
```

**Feature matrix:**
```python
TIER_FEATURES = {
    "free": {"mentions": False, "post_limit": 500, "read_limit": 100},
    "basic": {"mentions": True, "post_limit": 3000, "read_limit": 10000},
    "pro": {"mentions": True, "post_limit": 300000, "read_limit": 1000000},
}
```

**Integration:**
- `AutoPostService.run()` calls `tier_manager.can_post()` before posting
- `MentionHandler.process_mentions_batch()` calls `tier_manager.can_use_mentions()` before processing
- Both services receive `tier_manager` instance via constructor

### tools/registry.py
Tool registry with **auto-discovery** (v1.3).

**How it works:**
- Uses `pkgutil.iter_modules()` to scan all Python files in `tools/` directory
- Each tool file that exports `TOOL_SCHEMA` is automatically registered
- Tool function must have the same name as `schema["function"]["name"]`

**Exports:**
- `TOOLS` — dict mapping tool names to async functions (auto-populated)
- `TOOLS_SCHEMA` — list of JSON schemas in OpenAI function calling format (auto-populated)
- `get_tools_description()` — generates human-readable tool descriptions for agent prompts
- `refresh_tools()` — re-scan tools at runtime

**Available tools:**
- `web_search` — real-time web search via OpenRouter plugins
- `generate_image` — image generation using Gemini 3 Pro

**To add a new tool (zero registry changes needed):**
1. Create `tools/my_tool.py`
2. Add `TOOL_SCHEMA` constant with OpenAI function calling format
3. Create async function with matching name
4. Done! Tool is auto-discovered on startup

Example:
```python
# tools/my_tool.py
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "..."}},
            "required": ["query"]
        }
    }
}

async def my_tool(query: str) -> dict:
    # Implementation
    return {"result": "..."}
```

### tools/web_search.py
Web search using OpenRouter's native web search plugin.

**Auto-discovery:** Exports `TOOL_SCHEMA` for automatic registration.

**How it works:**
- Uses `plugins: [{id: "web"}]` parameter in OpenRouter API
- Returns search results with source citations (URLs, titles, snippets)
- Configurable `max_results` (1-10, default 5)

**Function signature:**
```python
async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    # Returns {"content": "...", "sources": [...]}
    # On error: {"content": "error message", "sources": [], "error": True}
```

**Error handling (v1.3.2):**
- Returns `{"error": True}` on timeout, HTTP errors, or unexpected exceptions
- Agent receives error message and can continue with degraded results

### tools/image_generation.py
Image generation using Gemini 3 Pro via OpenRouter.

**Auto-discovery:** Exports `TOOL_SCHEMA` for automatic registration.

**How it works (v1.3):**
- Loads ALL reference images from `assets/` folder (not random selection)
- Supports `.png`, `.jpg`, `.jpeg`, `.jfif`, `.gif`, `.webp` formats
- Sends reference images + prompt to model for consistent character appearance
- Returns raw image bytes (PNG format) or `None` on error (v1.3.2)

**Function signature:**
```python
async def generate_image(prompt: str) -> bytes | None:
    # Returns image bytes, or None on error
```

**Error handling (v1.3.2):**
- Returns `None` on timeout, HTTP errors, or missing image data
- Caller (autopost/mentions) continues without image if generation fails

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

### Autoposting (Agent Architecture)
```
[Scheduler]
    → AutoPostService.run()
    → Database.get_recent_posts_formatted(50)
    → Build system prompt (personality + agent instructions + tools)
    → LLM Call #1: Get plan
        → returns {reasoning, plan: [{tool, params}]}
    → Validate plan
    → For each tool in plan:
        → Execute tool (web_search or generate_image)
        → Add result to conversation
    → LLM Call #2: Get final tweet text
        → returns {post_text}
    → [if image_bytes] TwitterClient.upload_media()
    → TwitterClient.post()
    → Database.save_post()
```

### Mention Handling (Agent Architecture v1.3)
```
[Scheduler]
    → MentionAgentHandler.process_mentions_batch()
    → TwitterClient.get_mentions()
    → Database.mention_exists() [filter processed]
    → [optional] Filter by MENTIONS_WHITELIST
    → LLM Call #1: Select mentions
        → returns {selected_mentions: [{tweet_id, priority, reasoning, suggested_approach}]}
    → For EACH selected mention:
        → Database.get_user_mention_history()
        → LLM Call #2: Create plan
            → returns {reasoning, plan: [{tool, params}]}
        → For each tool in plan:
            → Execute tool (web_search or generate_image)
            → Add result to conversation
        → LLM Call #3: Generate reply
            → returns {reply_text}
        → [if image_bytes] TwitterClient.upload_media()
        → TwitterClient.reply()
        → Database.save_mention(tools_used=...)
```

---

## Extension Points

### Adding a new tool (Auto-discovery v1.3)
Create `tools/my_tool.py` with `TOOL_SCHEMA` — no registry changes needed:

```python
# tools/my_tool.py

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
}

async def my_tool(query: str) -> dict:
    # Implementation
    return {"result": "..."}
```

The tool is automatically discovered and available to agents on restart.

**Note:** To handle new tools in mentions, add execution logic to `services/mentions.py` `_process_single_mention()` method.

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
