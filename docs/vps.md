# Deploying to VPS

Deploy to any VPS provider (DigitalOcean, Linode, Vultr, Hetzner, etc.)

## Prerequisites

- VPS with Ubuntu 22.04+ (1GB RAM minimum)
- Domain name (optional, for HTTPS)
- Twitter Developer account with API keys
- OpenRouter API key

## Step 1: Server Setup

SSH into your server:

```bash
ssh root@your-server-ip
```

Update system and install dependencies:

```bash
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv python3-pip git postgresql nginx certbot python3-certbot-nginx
```

## Step 2: Setup PostgreSQL

```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE USER agentbot WITH PASSWORD 'your-secure-password';
CREATE DATABASE agentdb OWNER agentbot;
GRANT ALL PRIVILEGES ON DATABASE agentdb TO agentbot;
EOF
```

## Step 3: Clone Repository

```bash
# Create app directory
mkdir -p /opt/twitter-agent
cd /opt/twitter-agent

# Clone your fork
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Configure Environment

```bash
# Create .env file
cat > .env <<EOF
OPENROUTER_API_KEY=sk-or-v1-...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...
DATABASE_URL=postgresql://agentbot:your-secure-password@localhost:5432/agentdb
POST_INTERVAL_MINUTES=30
MENTIONS_INTERVAL_MINUTES=20
ENABLE_IMAGE_GENERATION=true
EOF

# Secure the file
chmod 600 .env
```

## Step 5: Create Systemd Service

```bash
cat > /etc/systemd/system/twitter-agent.service <<EOF
[Unit]
Description=Twitter Agent Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/twitter-agent
Environment=PATH=/opt/twitter-agent/venv/bin
EnvironmentFile=/opt/twitter-agent/.env
ExecStart=/opt/twitter-agent/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload and start
systemctl daemon-reload
systemctl enable twitter-agent
systemctl start twitter-agent
```

## Step 6: Check Status

```bash
# Check service status
systemctl status twitter-agent

# View logs
journalctl -u twitter-agent -f
```

## Step 7: Setup Nginx (Optional)

For HTTPS access to health endpoints:

```bash
cat > /etc/nginx/sites-available/twitter-agent <<EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/twitter-agent /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Add SSL (optional)
certbot --nginx -d your-domain.com
```

## Using Docker (Alternative)

If you prefer Docker:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Build and run
cd /opt/twitter-agent
docker build -t twitter-agent .
docker run -d \
  --name twitter-agent \
  --restart always \
  --env-file .env \
  -p 8080:8080 \
  twitter-agent
```

## Maintenance

### Update Bot

```bash
cd /opt/twitter-agent
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart twitter-agent
```

### View Logs

```bash
journalctl -u twitter-agent -f
# or with Docker
docker logs -f twitter-agent
```

### Backup Database

```bash
pg_dump -U agentbot agentdb > backup.sql
```

## Costs

Typical VPS pricing:

| Provider | 1GB RAM | 2GB RAM |
|----------|---------|---------|
| DigitalOcean | $6/mo | $12/mo |
| Linode | $5/mo | $10/mo |
| Vultr | $5/mo | $10/mo |
| Hetzner | $4/mo | $6/mo |

**Recommended**: 1GB RAM is sufficient for the bot.
