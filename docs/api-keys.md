# Getting API Keys

This guide explains how to obtain the required API keys for running your Twitter Agent.

## Twitter API Keys

### Step 1: Create Developer Account

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Sign in with your Twitter account
3. Apply for developer access (if not already approved)

### Step 2: Create a Project and App

1. Go to Developer Portal → Projects & Apps
2. Click "Create Project"
3. Fill in project details:
   - Project name: e.g., "My Twitter Agent"
   - Use case: Select appropriate option
4. Create an App within the project

### Step 3: Get API Keys

In your App settings, you'll find:

| Key | Location | Description |
|-----|----------|-------------|
| `TWITTER_API_KEY` | Keys and tokens → API Key | Also called Consumer Key |
| `TWITTER_API_SECRET` | Keys and tokens → API Secret | Also called Consumer Secret |
| `TWITTER_BEARER_TOKEN` | Keys and tokens → Bearer Token | For read-only requests |
| `TWITTER_ACCESS_TOKEN` | Keys and tokens → Access Token | For posting tweets |
| `TWITTER_ACCESS_SECRET` | Keys and tokens → Access Token Secret | For posting tweets |

### Step 4: Set Permissions

1. Go to App settings → User authentication settings
2. Click "Set up"
3. Configure:
   - App permissions: **Read and write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URL: `https://example.com` (placeholder)
   - Website URL: Your website or Twitter profile
4. Save and regenerate tokens if needed

### Important Notes

- **Free tier** allows posting but NOT reading mentions
- **Basic tier** ($100/month) required for mention replies
- Keep your keys secret - never commit them to git

---

## OpenRouter API Key

OpenRouter provides access to multiple LLM and image generation models through a single API.

### Step 1: Create Account

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up with Google/GitHub or email

### Step 2: Add Credits

1. Go to Account → Credits
2. Add credits (minimum $5 recommended to start)
3. Enable auto-recharge if desired

### Step 3: Generate API Key

1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Click "Create Key"
3. Name it (e.g., "Twitter Agent")
4. Copy the key (starts with `sk-or-v1-...`)

### Models Used

The agent uses these models by default:

| Purpose | Model | ~Cost per call |
|---------|-------|----------------|
| Text Generation | `anthropic/claude-sonnet-4` | ~$0.003-0.01 |
| Image Generation | `google/gemini-2.0-flash-exp:free` | Free |

### Cost Estimate

Typical monthly costs with default settings (posting every 30 min):

- ~1,440 posts/month
- ~$5-15/month on OpenRouter
- Image generation is free with Gemini

---

## PostgreSQL Database

### Option 1: Railway (Recommended)

Railway automatically provisions PostgreSQL and sets `DATABASE_URL`.

### Option 2: Supabase

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Go to Settings → Database
4. Copy the "Connection string" (URI format)

Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres`

### Option 3: Neon

1. Go to [neon.tech](https://neon.tech)
2. Create account and project
3. Copy the connection string from dashboard

### Option 4: Self-hosted

See [vps.md](vps.md) for PostgreSQL setup on your own server.

---

## Environment Variables Summary

```bash
# Twitter API
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Bot Settings
POST_INTERVAL_MINUTES=30
MENTIONS_INTERVAL_MINUTES=20
ENABLE_IMAGE_GENERATION=true
```

## Security Best Practices

1. **Never commit keys to git** - use `.env` files
2. **Use environment variables** on hosting platforms
3. **Rotate keys** periodically
4. **Use separate keys** for development and production
5. **Monitor usage** on OpenRouter dashboard
