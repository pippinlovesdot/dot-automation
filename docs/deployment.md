# Deployment Guide

This guide covers deploying the Twitter Agent Bot to various platforms.

## Requirements

### System Requirements
- Python 3.11+
- PostgreSQL database
- Persistent storage for assets (reference images)

### Environment Variables

All platforms require these environment variables:

```bash
# OpenRouter API (LLM + Image Generation)
OPENROUTER_API_KEY=sk-or-...

# Twitter API v2 credentials
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...

# PostgreSQL Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Bot Settings (optional, defaults shown)
POST_INTERVAL_MINUTES=30
MENTIONS_INTERVAL_MINUTES=20
ENABLE_IMAGE_GENERATION=true
```

See [api-keys.md](api-keys.md) for how to obtain these keys.

## Platform Guides

| Platform | Difficulty | Cost | Guide |
|----------|------------|------|-------|
| Railway | Easy | $5+/mo | [railway.md](railway.md) |
| Render | Easy | $7+/mo | [render.md](render.md) |
| VPS | Medium | $5+/mo | [vps.md](vps.md) |

## Quick Start (Railway)

1. Fork this repository
2. Create Railway project from GitHub
3. Add PostgreSQL database
4. Set environment variables
5. Deploy

See [railway.md](railway.md) for detailed steps.

## Database Setup

The bot automatically creates required tables on first run:

```sql
-- Posts table
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    tweet_id VARCHAR(50),
    include_picture BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Mentions table
CREATE TABLE mentions (
    id SERIAL PRIMARY KEY,
    tweet_id VARCHAR(50) UNIQUE,
    author_handle VARCHAR(50),
    author_text TEXT,
    our_reply TEXT,
    action VARCHAR(20),
    tools_used TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bot state table
CREATE TABLE bot_state (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Reference Images

Place character reference images in the `assets/` folder for consistent image generation.

Supported formats: `.png`, `.jpg`, `.jpeg`, `.jfif`, `.gif`, `.webp`

## Health Check

The bot exposes these endpoints:

- `GET /` - Basic status
- `GET /health` - Health check
- `GET /metrics` - Bot statistics
- `GET /tier-status` - Twitter API tier info

## Twitter API Tiers

| Feature | Free | Basic ($100/mo) | Pro |
|---------|------|-----------------|-----|
| Post tweets | Yes | Yes | Yes |
| Read mentions | No | Yes | Yes |
| Rate limits | 50/day | 100/day | 300/day |

The bot automatically detects your tier and disables unavailable features.
