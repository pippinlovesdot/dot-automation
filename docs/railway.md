# Deploying to Railway

Railway is the easiest way to deploy your Twitter Agent.

## Prerequisites

- GitHub account
- Railway account ([railway.app](https://railway.app))
- Twitter Developer account with API keys
- OpenRouter API key

## Step 1: Fork the Repository

1. Fork this repository to your GitHub account
2. Clone locally if you want to customize prompts/personality

## Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your forked repository
5. Railway will auto-detect Python and start building

## Step 3: Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Wait for the database to provision
4. Railway automatically sets `DATABASE_URL`

## Step 4: Set Environment Variables

1. Click on your service (not the database)
2. Go to "Variables" tab
3. Add these variables:

```
OPENROUTER_API_KEY=sk-or-v1-...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...
POST_INTERVAL_MINUTES=30
MENTIONS_INTERVAL_MINUTES=20
ENABLE_IMAGE_GENERATION=true
```

> **Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

## Step 5: Add Reference Images (Optional)

For consistent character appearance in generated images:

1. Add images to `assets/` folder in your repo
2. Commit and push
3. Railway will redeploy automatically

## Step 6: Verify Deployment

1. Click "Settings" → find your public URL (e.g., `your-agent.up.railway.app`)
2. Visit `https://your-agent.up.railway.app/health`
3. Should return `{"status": "healthy"}`

## Step 7: Check Logs

1. Click "Deployments" tab
2. Click on the latest deployment
3. View logs to see bot activity

You should see:
```
INFO: Starting Twitter Agent...
INFO: Database connected
INFO: Scheduler started
INFO: Uvicorn running on http://0.0.0.0:8080
```

## Useful Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Basic status |
| `/health` | Health check |
| `/metrics` | Bot statistics |
| `/tier-status` | Twitter API tier info |
| `/force-post` | Trigger immediate post |
| `/force-mentions` | Check mentions now |

## Troubleshooting

### Bot not posting

1. Check logs for errors
2. Verify `OPENROUTER_API_KEY` is set correctly
3. Check `/tier-status` for rate limit info

### Database connection errors

1. Ensure PostgreSQL addon is provisioned
2. Check `DATABASE_URL` is set (click on variable to see value)
3. Try redeploying

### Image generation not working

1. Verify `ENABLE_IMAGE_GENERATION=true`
2. Check OpenRouter API key has access to image models
3. Add reference images to `assets/` folder

## Costs

Railway pricing (as of 2024):
- **Hobby**: $5/month (includes $5 credit)
- **Pro**: $20/month (team features)

PostgreSQL is included in the base price.

Typical usage: ~$5-10/month for a bot posting every 30 minutes.
