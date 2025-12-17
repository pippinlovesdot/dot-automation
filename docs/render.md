# Deploying to Render

Render is a simple platform similar to Railway with good free tier options.

## Prerequisites

- GitHub account
- Render account ([render.com](https://render.com))
- Twitter Developer account with API keys
- OpenRouter API key

## Step 1: Fork the Repository

1. Fork this repository to your GitHub account
2. Clone locally if you want to customize prompts/personality

## Step 2: Create PostgreSQL Database

1. Go to [render.com](https://render.com) and sign in
2. Click "New" → "PostgreSQL"
3. Configure:
   - Name: `agent-db`
   - Region: Choose closest to you
   - Plan: Free (or Starter for production)
4. Click "Create Database"
5. Wait for provisioning, then copy the **Internal Database URL**

## Step 3: Create Web Service

1. Click "New" → "Web Service"
2. Connect your GitHub account if not already
3. Select your forked repository
4. Configure:
   - Name: `twitter-agent`
   - Region: Same as database
   - Branch: `main`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
5. Select instance type (Starter recommended)

## Step 4: Set Environment Variables

In the web service settings, add these environment variables:

```
DATABASE_URL=<paste Internal Database URL from Step 2>
OPENROUTER_API_KEY=sk-or-v1-...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...
POST_INTERVAL_MINUTES=30
MENTIONS_INTERVAL_MINUTES=20
ENABLE_IMAGE_GENERATION=true
PORT=8080
```

## Step 5: Deploy

1. Click "Create Web Service"
2. Render will build and deploy automatically
3. Wait for "Live" status

## Step 6: Verify Deployment

1. Click on your service URL (e.g., `twitter-agent.onrender.com`)
2. Visit `https://twitter-agent.onrender.com/health`
3. Should return `{"status": "healthy"}`

## Important: Prevent Sleep

Render free tier services sleep after 15 minutes of inactivity. To prevent this:

### Option 1: Use Starter Plan ($7/mo)
Starter plan services don't sleep.

### Option 2: External Ping Service
Use a free service like [UptimeRobot](https://uptimerobot.com) to ping your `/health` endpoint every 5 minutes.

### Option 3: Cron-job.org
Set up a free cron job at [cron-job.org](https://cron-job.org) to hit your endpoint regularly.

## Troubleshooting

### Service keeps sleeping

- Upgrade to Starter plan, or
- Set up external ping service

### Database connection timeout

1. Ensure you're using the **Internal** Database URL (not External)
2. Check database is in same region as web service

### Build failures

1. Check Python version compatibility
2. Ensure `requirements.txt` is in root directory
3. Check build logs for specific errors

## Costs

Render pricing (as of 2024):

| Service | Free | Starter |
|---------|------|---------|
| Web Service | Sleep after 15min | $7/mo |
| PostgreSQL | 90 days, then $7/mo | $7/mo |

**Recommended**: Starter plan for both ($14/mo total) for reliable 24/7 operation.
