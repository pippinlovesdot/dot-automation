<div align="center">

# Twitter AI Agent Framework

**Create autonomous AI agents with deep personalities in minutes**

<br/>

[![Website](https://img.shields.io/badge/🌐_Website-pippinlovesdot.com-3b82f6?style=flat-square)](https://www.pippinlovesdot.com/)
[![Solana](https://img.shields.io/badge/Solana-$DOT-14F195?style=flat-square&logo=solana&logoColor=white)](https://dexscreener.com/solana/2kfvejgmcwk2uvyggdtqbgqe4tmaosw4tyen2shon4vf)
[![Twitter](https://img.shields.io/badge/Twitter-@pippinlovesdot-1DA1F2?style=flat-square&logo=twitter&logoColor=white)](https://x.com/pippinlovesdot)
[![Telegram](https://img.shields.io/badge/Telegram-Community-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/dotlovesyou)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

### Describe your agent. Get code in 5 minutes.

*Tell us about personality and vibe. We generate avatar, bio, complete personality system, and production-ready Python code.*

<br>

🚀 **Launching next week** — [Follow for updates](https://x.com/pippinlovesdot)

</div>

---

## About

A framework for building **fully autonomous AI agents** on Twitter. Not template bots that post generic content — real AI personalities with deep backstories, consistent belief systems, unique speech patterns, and authentic behavioral responses.

**The problem:** Creating a compelling AI agent takes weeks of prompt engineering, personality design, and infrastructure setup. Most end up feeling like obvious bots.

**Our solution:** Describe your character in plain language. Our engine synthesizes a complete cognitive architecture and packages it as production-ready Python code. Deploy in minutes, not weeks.

---

## Background

Built by the **$DOT team** — friends of [Pippin](https://x.com/pippinlovesyou), one of the most recognized AI agents in crypto (reached $300M market cap, currently at $200-220M).

We spent months researching what makes AI characters feel alive:
- How agents form and express beliefs consistently
- What creates personality coherence across thousands of interactions
- Why some AI characters build communities while others get ignored
- How to balance authenticity with engagement

This framework is that research, productized.

---

## How It Works

<table>
<tr>
<td width="60" align="center">
<h3>📝</h3>
</td>
<td>
<strong>DESCRIBE</strong><br/>
Tell us who your agent is. A sarcastic trading cat? A philosophical robot from 2847? A wholesome meme curator? Few sentences or detailed spec — the engine handles both.
</td>
</tr>
<tr><td align="center">▼</td><td></td></tr>
<tr>
<td align="center">
<h3>🧠</h3>
</td>
<td>
<strong>SYNTHESIZE</strong><br/>
Our cognitive engine generates a complete character model: origin story, belief systems, emotional responses, speech patterns, behavioral rules. Not a simple prompt — a full personality architecture.
</td>
</tr>
<tr><td align="center">▼</td><td></td></tr>
<tr>
<td align="center">
<h3>📦</h3>
</td>
<td>
<strong>PACKAGE</strong><br/>
Download a ready-to-run Python project with your agent's personality baked in. Modular, typed, documented — you own the code completely.
</td>
</tr>
<tr><td align="center">▼</td><td></td></tr>
<tr>
<td align="center">
<h3>🚀</h3>
</td>
<td>
<strong>DEPLOY</strong><br/>
Add your API keys, run the script. Your agent starts living on Twitter autonomously — posting, replying, generating images, building community.
</td>
</tr>
</table>

---

## What We Generate

This isn't a basic "you are a funny bot" prompt. We create deeply crafted characters with four interconnected layers:

**Identity** — Origin story, backstory, core motivations, formative experiences. Who is this character and where did they come from?

**Cognition** — Belief systems, values, opinions, worldview, emotional matrix. How do they think and what do they care about?

**Expression** — Voice, tone, vocabulary, humor style, topic preferences. How do they communicate?

**Behavior** — Posting patterns, engagement rules, response strategies. When and how do they act?

Each layer feeds into the next. Your agent behaves consistently across thousands of interactions — like a real character with depth, not a generic bot.

---

## Architecture

The system supports **two modes** of operation:

### Legacy Mode (Default)
Two separate autonomous agents running on different schedules:

| Scheduled Posts (Agent) | Mention Responses (Agent) |
|-------------------------|---------------------------|
| Cron-based (configurable interval) | Polling-based (configurable interval) |
| Agent creates plan → executes tools → generates post | Agent selects mentions → plans per mention → generates replies |
| Dynamic tool usage (web search, image generation) | 3 LLM calls per mention (select → plan → reply) |
| Posts to Twitter with optional media | Tracks tools used per reply |

### Unified Agent Mode (v1.4.0)
A single agent that handles both posting and replying in one cycle:

| Feature | Description |
|---------|-------------|
| Single cycle | Agent decides what to do (post, reply, or both) |
| Tool-based actions | Uses tools like `get_mentions`, `create_post`, `create_reply` |
| Step-by-step | LLM decides after each tool execution |
| Rate limiting | Self-imposed daily limits for posts and replies |

**Enable with:** `USE_UNIFIED_AGENT=true` in environment variables.

**Auto-Discovery Tools:** Tools are organized into folders (`shared/`, `legacy/`, `unified/`) and automatically discovered on startup. Each tool has a `TOOL_CONFIG` with description that's injected into prompts.

---

## Capabilities

🧠 **Deep Personality Generation** — Complete character profiles with backstory, beliefs, values, and speech patterns. Not templates — synthesized personalities.

🐦 **Autonomous Posting** — Schedule-based or trigger-based content generation. Your agent posts in its authentic voice without manual intervention.

💬 **Reply & Mention Handling** — Monitors conversations and responds contextually. LLM decides whether to reply, use tools, or ignore. Requires Twitter API Basic tier or higher for mention access.

📊 **Automatic Tier Detection** — Detects your Twitter API tier (Free/Basic/Pro/Enterprise) automatically on startup and every hour. Blocks unavailable features and warns when approaching limits.

🎨 **Image Generation** — Creates visuals matching agent's style and current context. Supports multiple providers.

🔧 **Extensible Tools** — Plug in web search, profile lookup, conversation history, and more. Add custom tools to the appropriate folder and they're auto-discovered.

📦 **Production-Ready** — Clean async Python with type hints. Add API keys and deploy — no additional setup required.

---

## Tech Stack

### Runtime

Python 3.10+ with async I/O, full type hints, and modular architecture. The codebase is designed to be readable and hackable — you own it completely.

**Core libraries:**
- `fastapi` — HTTP server for webhooks
- `uvicorn` — ASGI server
- `apscheduler` — Cron-based job scheduling
- `httpx` — Async HTTP client
- `tweepy` — Twitter API v2 integration
- `asyncpg` — Async PostgreSQL driver
- `pydantic` + `pydantic-settings` — Settings and validation

### LLM Inference

All language model calls go through **OpenRouter**, giving you access to multiple providers through a single API:

- **Claude Sonnet 4.5** — Primary model for personality synthesis and content generation
- **GPT-5** — Alternative provider with strong reasoning capabilities  
- **Gemini 3 Pro** — Fast inference, good for high-volume interactions

Model selection is configurable per-agent. OpenRouter handles routing, fallbacks, and load balancing automatically.

### Image Generation

Visual content generation supports two providers:

- **Nano Banana 2 Pro** (Gemini 3 Pro Image) — Our default. Fast, high quality, excellent prompt following
- **GPT-5 Image** — Native OpenAI generation with strong context awareness

### Web Search

Real-time web search capability powered by **OpenRouter's native plugins**:

- **OpenRouter Web Plugin** — Native web search using `plugins: [{id: "web"}]` API. Returns real search results with source citations (URLs, titles, snippets). Supports multiple search engines including native provider search and Exa.ai.

### Twitter Integration

Official Twitter API v2 for all operations: posting, timeline reading, media uploads, mention monitoring. We don't use unofficial endpoints or scraping.

### Deployment

Runs anywhere Python runs: VPS, Railway, Render, Docker, your laptop. Stateless design means easy horizontal scaling if needed.

---

## Architecture Principles

**Modular** — Swap LLM providers, image generators, or tools without touching core logic. Each component has clean interfaces.

**Local credentials** — Your API keys never leave your machine. We generate code, not hosted services.

**Stateless** — Agent state serializes to JSON. Easy to backup, migrate, or run multiple instances.

**Clean code** — Readable, typed, documented. This is your codebase now — you should be able to understand and modify it.

---

## Project Structure

When you generate an agent, you receive a complete Python project:

```
my-agent/
├── assets/                  # Reference images for generation
│
├── config/
│   ├── settings.py          # Environment & configuration
│   ├── models.py            # Model configuration (LLM, Image models)
│   ├── schemas.py           # JSON schemas for LLM responses
│   ├── personality/         # Character definition (modular)
│   │   ├── backstory.py     # Origin story
│   │   ├── beliefs.py       # Values and priorities
│   │   └── instructions.py  # Communication style
│   └── prompts/             # LLM prompts (modular)
│       ├── agent_autopost.py         # Agent planning prompt
│       ├── unified_agent.py          # Unified agent instructions (v1.4)
│       ├── mention_selector_agent.py # Agent mention selection (v1.3)
│       └── mention_reply_agent.py    # Agent reply planning (v1.3)
│
├── utils/
│   └── api.py               # OpenRouter API configuration
│
├── services/
│   ├── autopost.py          # Agent-based scheduled posting
│   ├── mentions.py          # Mention/reply handler
│   ├── unified_agent.py     # Unified agent (v1.4)
│   ├── tier_manager.py      # Twitter API tier detection
│   ├── llm.py               # OpenRouter client (generate, chat)
│   ├── twitter.py           # Twitter API v2 integration
│   └── database.py          # PostgreSQL for history + metrics
│
├── tools/
│   ├── registry.py          # Auto-discovery from subfolders
│   ├── shared/              # Tools for both modes
│   │   ├── web_search.py    # Web search via OpenRouter
│   │   ├── get_twitter_profile.py    # Get user profile info
│   │   └── get_conversation_history.py # Chat history with user
│   ├── legacy/              # Legacy mode only
│   │   └── image_generation.py  # Image gen with references
│   └── unified/             # Unified agent only
│       ├── create_post.py   # Post with optional image
│       ├── create_reply.py  # Reply to mention
│       ├── get_mentions.py  # Fetch unread mentions
│       └── finish_cycle.py  # End agent cycle
│
├── main.py                  # FastAPI + APScheduler entry point
├── requirements.txt         # Dependencies
├── .env.example             # API keys template
└── ARCHITECTURE.md          # AI-readable technical documentation
```

Everything is modular. Swap the LLM provider, add new tools, adjust posting schedules — the architecture supports it.

### AI-Friendly Documentation

The `ARCHITECTURE.md` file is specifically designed for AI assistants (ChatGPT, Claude, Cursor, Copilot). Feed it to your AI tool of choice and it will understand the entire codebase structure, data flows, and how to extend the bot. This enables AI-assisted development and customization.

---

## Services Documentation

### Auto-posting (`services/autopost.py`)

The bot uses an **autonomous agent architecture** to generate and post tweets at configurable intervals.

**How the agent works:**
1. Agent receives context (previous 50 posts to avoid repetition)
2. Agent creates a **plan** — decides which tools to use:
   - `web_search` — to find current information, news, prices
   - `generate_image` — to create a visual for the post
   - Or no tools at all if it has a good idea already
3. Agent executes tools step by step, with results feeding back into the conversation
4. Agent generates final tweet text based on all gathered information
5. Tweet is posted with optional image
6. Saved to database for future context

**Example agent flow:**
```
Agent thinks: "I want to post about crypto trends with a visual"
→ Plan: [web_search("crypto market today"), generate_image("abstract chart art")]
→ Executes web_search, gets current market info
→ Executes generate_image, creates matching visual
→ Generates tweet: "the market is just vibes at this point..."
→ Posts with image
```

**Key features:**
- **Dynamic tool selection** — Agent decides when tools are needed
- **Continuous conversation** — Tool results inform the final tweet
- **Modular tools** — Add new tools to `tools/registry.py` and agent automatically uses them

**Configuration:**
- `POST_INTERVAL_MINUTES` — Time between auto-posts (default: 30)
- `ENABLE_IMAGE_GENERATION` — Set to `false` to disable image generation (hides tool from agent)
- `ALLOW_MENTIONS` — Set to `false` to disable mentions (hides mention tools from agent)

### Unified Agent (`services/unified_agent.py`) — v1.4.0

A single agent that handles both posting and replying in one cycle.

**How it works:**
1. Agent loads context (recent actions, rate limits, tier info)
2. Agent decides what to do using available tools
3. Loop until `finish_cycle` is called:
   - LLM decides next action via Structured Output
   - Execute tool (get_mentions, create_post, create_reply, etc.)
   - Add result to conversation
4. Repeat next cycle after configured interval

**Available tools:**
- `get_mentions` — fetch unread Twitter mentions
- `create_post` — post with optional image
- `create_reply` — reply to mention with optional image
- `web_search` — search the web for current info
- `get_twitter_profile` — get user profile info
- `get_conversation_history` — get chat history with user
- `finish_cycle` — end the current cycle

**Configuration:**
- `USE_UNIFIED_AGENT` — Set to `true` to enable (default: true)
- `AGENT_INTERVAL_MINUTES` — Time between agent cycles (default: 30)
- Daily limits are tier-based (Free: 15/0, Basic: 50/50, Pro: 500/500)

### Mention Handler (`services/mentions.py`)

Agent-based mention processing with 3 LLM calls per mention (v1.3).

**How it works:**
1. Polls Twitter API for new mentions every 20 minutes (configurable)
2. Filters out already-processed mentions using database
3. **LLM #1: Selection** — Evaluates all mentions, returns array of worth replying to (with priority)
4. For EACH selected mention:
   - Gets user conversation history from database
   - **LLM #2: Planning** — Creates plan (which tools to use)
   - Executes tools (web_search, generate_image)
   - **LLM #3: Reply** — Generates final reply text
   - Uploads image if generated, posts reply
   - Saves interaction with tools_used tracking
5. Returns batch summary

**Why agent architecture:** Instead of a single LLM call for all mentions, each mention gets individual attention. The agent can use tools to research topics, generate custom images, and craft contextually appropriate replies. User conversation history enables personalized interactions.

**Configuration:**
- `MENTIONS_INTERVAL_MINUTES` — Time between mention checks (default: 20)
- `MENTIONS_WHITELIST` — Optional list of usernames for testing (empty = all users)
- Requires Twitter API Basic tier or higher for mention access

### Image Generation (`tools/image_generation.py`)

Generates images using Gemini 3 Pro via OpenRouter, with support for reference images.

**How `assets/` folder works (v1.3):**
- Place reference images in `assets/` folder (supports: png, jpg, jpeg, gif, webp, jfif)
- Bot uses **ALL** reference images (not random selection) for maximum consistency
- Reference images are sent to the model along with the generation prompt
- If `assets/` is empty, images are generated without reference (pure text-to-image)
- Use reference images to maintain consistent character appearance across posts

**Auto-discovery:** Tool exports `TOOL_SCHEMA` and is automatically available to agents.

**Example use case:** Place photos of your bot's character/avatar in `assets/`. The model will use all of them as reference when generating new images, keeping the visual style consistent.

### Personality (`config/personality/`)

Modular character definition split into three files for easier editing:

**`backstory.py`** — Origin story and background
- Who the character is
- Where they come from
- Core identity

**`beliefs.py`** — Values and priorities
- Personality traits
- Topics of interest
- Worldview

**`instructions.py`** — Communication style
- How to write (tone, grammar, punctuation)
- What NOT to do
- Example tweets

All parts are combined into `SYSTEM_PROMPT` automatically via `__init__.py`.

```python
from config.personality import SYSTEM_PROMPT  # Gets combined prompt
from config.personality import BACKSTORY      # Or individual parts
```

### Tier Manager (`services/tier_manager.py`)

Automatic Twitter API tier detection and limit management.

**How it works:**
1. On startup, calls Twitter Usage API (`GET /2/usage/tweets`)
2. Determines tier from `project_cap`: Free (100), Basic (10K), Pro (1M), Enterprise (10M+)
3. Checks tier every hour to detect subscription upgrades
4. Blocks unavailable features (e.g., mentions on Free tier)
5. Auto-pauses operations when monthly cap reached
6. Logs warnings at 80% and 90% usage

**Tier features:**
| Tier | Mentions | Post Limit | Read Limit |
|------|----------|------------|------------|
| Free | ❌ | 500/month | 100/month |
| Basic | ✅ | 3,000/month | 10,000/month |
| Pro | ✅ | 300,000/month | 1,000,000/month |

**Endpoints:**
- `GET /tier-status` — Current tier, usage stats, available features
- `POST /tier-refresh` — Force tier re-detection (after subscription change)

### Database (`services/database.py`)

PostgreSQL storage for post history and mention tracking, enabling context-aware generation.

**Tables:**
- `posts` — Stores all posted tweets (text, tweet_id, include_picture, created_at)
- `mentions` — Stores mention interactions (tweet_id, author_handle, author_text, our_reply, action)

**Why it matters:**
- Post history lets the bot reference previous tweets and avoid repetition. The LLM sees the last 50 posts as context.
- Mention history prevents double-replying and provides conversation context for future interactions.

### LLM Client (`services/llm.py`)

Async client for OpenRouter API with structured output support.

**Features:**
- Uses Claude Sonnet 4.5 by default (configurable)
- Supports structured JSON output for reliable parsing
- Handles both simple text generation and complex formatted responses

### Twitter Client (`services/twitter.py`)

Handles all Twitter API interactions using tweepy.

**Capabilities:**
- Post tweets (API v2)
- Upload media (API v1.1 — required for images)
- Reply to tweets
- Fetch mentions (polling-based)
- Get authenticated user info
- Automatic rate limit handling

---

## Getting Started

> 🚧 **Platform launching next week.** Workflow below describes the system.

1. **Access** — Visit [pippinlovesdot.com](https://www.pippinlovesdot.com/), describe your agent's personality and style
2. **Generate** — Engine creates personality profile + complete Python codebase
3. **Configure** — Download package, add your API credentials to `.env`
4. **Deploy** — Run `python main.py` on any Python 3.10+ environment
5. **Iterate** — Monitor performance, refine personality, expand tool integrations

### Requirements

- **OpenRouter API Key** — For LLM inference. Gives access to Claude, GPT, Gemini through one endpoint.
- **Twitter API v2** — For posting and reading. Free tier works for posting; Basic tier needed for mentions. Pro tier increases rate limits.
- **PostgreSQL** — For conversation history. Any provider works (Railway, Supabase, Neon, self-hosted).
- **Python 3.10+** — Runtime environment with async support.

---

## Roadmap

- [x] Core personality synthesis engine
- [x] Twitter automation pipeline  
- [x] Multi-model LLM support via OpenRouter
- [x] Image generation integration
- [x] Mention handling with tool calling
- [ ] **Web platform launch** ← today

---

## $DOT

<div align="center">

[![DexScreener](https://img.shields.io/badge/📊_Chart-DexScreener-00D18C?style=flat-square)](https://dexscreener.com/solana/2kfvejgmcwk2uvyggdtqbgqe4tmaosw4tyen2shon4vf)
[![Jupiter](https://img.shields.io/badge/🪐_Buy-Jupiter-9945FF?style=flat-square)](https://jup.ag/swap/SOL-2kfvejgmcwk2uvyggdtqbgqe4tmaosw4tyen2shon4vf)

**Network:** Solana · **Token:** $DOT

</div>

---

## Community

<div align="center">

[![Twitter](https://img.shields.io/badge/Twitter-@pippinlovesdot-1DA1F2?style=flat-square&logo=twitter&logoColor=white)](https://x.com/pippinlovesdot)
[![Telegram](https://img.shields.io/badge/Telegram-@dotlovesyou-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/dotlovesyou)

**Follow for launch announcements and early access.**

</div>

---

## License

MIT — use it, modify it, build on it.

---

<div align="center">

![DOT](https://pbs.twimg.com/profile_banners/1995542999946915840/1764609639/1500x500)

**Built by the $DOT team**

*Friends of Pippin · Believers in autonomous AI agents*

</div>
