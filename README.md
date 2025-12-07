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

The system operates on **two triggers**:

| Scheduled Posts | Reactive Engagement |
|-----------------|---------------------|
| Cron-based (configurable interval) | Webhook-triggered |
| Generates original content | Handles mentions & replies |
| Creates matching images | LLM decides: respond or ignore |
| Posts to Twitter | Can use tools (web search, etc.) |

This separation keeps the codebase simple while enabling both proactive and reactive behavior.

---

## Capabilities

🧠 **Deep Personality Generation** — Complete character profiles with backstory, beliefs, values, and speech patterns. Not templates — synthesized personalities.

🐦 **Autonomous Posting** — Schedule-based or trigger-based content generation. Your agent posts in its authentic voice without manual intervention.

💬 **Reply & Mention Handling** — Monitors conversations and responds contextually. LLM decides whether to reply, use tools, or ignore. Requires Twitter API Pro tier for mention access.

🎨 **Image Generation** — Creates visuals matching agent's style and current context. Supports multiple providers.

🔧 **Extensible Tools** — Plug in web search, external APIs, blockchain data, custom integrations. The tool system is designed for expansion.

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

Real-time web search capability powered by **Perplexity** via OpenRouter:

- **Perplexity Sonar** — Online search model for current information, news, and facts. Automatically invoked by the LLM when it needs fresh data. Integrated through OpenRouter for unified API access.

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
│   └── personality.py       # Generated character prompt
│
├── services/
│   ├── autopost.py          # Scheduled posting logic
│   ├── mentions.py          # Mention/reply handler with tool calling
│   ├── llm.py               # OpenRouter client
│   ├── twitter.py           # Twitter API v2 integration
│   ├── image_gen.py         # Image generation
│   └── database.py          # PostgreSQL for history
│
├── tools/
│   ├── registry.py          # Available tools for LLM
│   └── web_search.py        # Web search capability
│
├── main.py                  # FastAPI + APScheduler entry point
├── requirements.txt         # Dependencies
└── .env.example             # API keys template
```

Everything is modular. Swap the LLM provider, add new tools, adjust posting schedules — the architecture supports it.

---

## Services Documentation

### Auto-posting (`services/autopost.py`)

The bot automatically generates and posts tweets at configurable intervals using APScheduler.

**How it works:**
1. Fetches recent posts from database to provide context (avoids repetition)
2. Sends personality prompt + context to LLM with structured output format
3. LLM returns `{text: "...", include_picture: true/false}`
4. If `include_picture` is true and image generation is enabled, generates an image
5. Posts tweet to Twitter (with optional media)
6. Saves post to database for future context

**Configuration:**
- `POST_INTERVAL_MINUTES` — Time between auto-posts (default: 30)
- `ENABLE_IMAGE_GENERATION` — Set to `false` to disable all image generation

### Image Generation (`services/image_gen.py`)

Generates images using Gemini 3 Pro via OpenRouter, with support for reference images.

**How `assets/` folder works:**
- Place 1 or more reference images in `assets/` folder (supports: jpg, png, jpeg, gif, webp)
- Bot randomly selects up to 2 images as style/character reference
- Reference images are sent to the model along with the generation prompt
- If `assets/` is empty, images are generated without reference (pure text-to-image)
- Use reference images to maintain consistent character appearance across posts

**Example use case:** Place photos of your bot's character/avatar in `assets/`. The model will use these as reference when generating new images, keeping the visual style consistent.

### Personality (`config/personality.py`)

Contains `SYSTEM_PROMPT` that defines your bot's entire character — how it thinks, writes, and behaves.

**What to customize:**
- Personality traits and worldview
- Communication style (formal, casual, chaotic, lowercase, etc.)
- Topics to discuss and topics to avoid
- Emoji and punctuation preferences
- Example tweets that capture the vibe
- Behavioral rules (no hashtags, no engagement bait, etc.)

The more detailed your personality prompt, the more consistent and authentic your bot will feel.

### Database (`services/database.py`)

PostgreSQL storage for post history, enabling context-aware generation.

**Tables:**
- `posts` — Stores all posted tweets (text, tweet_id, include_picture, created_at)
- `mentions` — Stores mention interactions (prepared for future mention handling)

**Why it matters:** By storing post history, the bot can reference its previous tweets and avoid repetition. The LLM sees the last 50 posts as context when generating new content.

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
- Reply to tweets (prepared for mention handling)
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
- [ ] **Web platform launch** ← Next week

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
