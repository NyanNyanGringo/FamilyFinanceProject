# Docker Deployment Guide for FamilyFinanceProject

Simple Docker setup for running the Telegram bot on VDS/VPS servers.

## 🚀 Quick Start (Local Testing)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd FamilyFinanceProject

# 2. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 3. Add Google credentials
# Place your .google_service_account_credentials.json in project root

# 4. Run
docker-compose up -d
```

## 🖥️ VDS/VPS Deployment

### 🚀 One-Command Deployment (Recommended)

Uses Docker Context for seamless remote deployment:

```bash
# 1. Run deployment script (first time setup + deploy)
./deploy-simple.sh myvps

# 2. For updates, just run again
./deploy-simple.sh myvps
```

The script will:
- Ask for your VPS IP and SSH username
- Create Docker context automatically
- Deploy your bot to VPS
- Switch back to local development

**Prerequisites:**
- SSH key access to your VPS
- Docker installed on VPS (script can help with this)

### 📋 Manual VDS Setup (Alternative)

<details>
<summary>Click to expand manual setup steps</summary>

#### Step 1: Install Docker on VDS

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Step 2: Setup Project on VDS

```bash
# Clone repository
git clone <your-repo-url>
cd FamilyFinanceProject
```

#### Step 3: Configure Environment (.env file)

Create `.env` file on VDS:
```bash
nano .env
```

Add your credentials:
```bash
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_TOKEN=your_telegram_bot_token_here
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id_here
```

#### Step 4: Setup Google Credentials

Create credentials file on VDS:
```bash
nano .google_service_account_credentials.json
```

Paste your Google Service Account JSON (the entire content from your credentials file).

#### Step 5: Deploy

```bash
# Create voice messages directory
mkdir -p voice_messages

# Start the bot
docker-compose up -d

# Check logs
docker-compose logs -f
```

</details>

## 📋 Essential Commands

```bash
# Start bot
docker-compose up -d

# Stop bot
docker-compose down

# View logs
docker-compose logs -f

# Restart bot
docker-compose restart

# Check status
docker-compose ps

# Health check
docker exec familyfinance-bot /usr/local/bin/healthcheck.sh
```

## 🔧 Development Mode

For development with live code updates:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 🐛 Troubleshooting

### Bot not starting
```bash
# Check logs for errors
docker-compose logs

# Verify environment variables
docker exec familyfinance-bot env | grep -E "(OPENAI|TELEGRAM|GOOGLE)"

# Check credentials file
docker exec familyfinance-bot cat /app/.google_service_account_credentials.json
```

### High disk usage
```bash
# Check voice messages size
docker exec familyfinance-bot du -sh /app/voice_messages

# Manual cleanup (remove files older than 7 days)
docker exec familyfinance-bot find /app/voice_messages -type f -mtime +7 -delete
```

### Update bot
```bash
# Using one-command deployment
./deploy-simple.sh myvps

# Or manually
git pull
docker-compose build
docker-compose up -d
```

## 📁 File Structure

```
FamilyFinanceProject/
├── .env                                    # Your API keys
├── .google_service_account_credentials.json # Google credentials
├── docker-compose.yml                     # Production setup
├── docker-compose.dev.yml                 # Development setup
├── Dockerfile                            # Container configuration
├── voice_messages/                       # Audio files (auto-created)
└── src/                                 # Application code
```

## ⚠️ Important Notes

- **Voice files accumulate** - monitor disk space and clean manually if needed
- **Keep credentials secure** - never commit `.env` or credentials to git
- **Bot uses polling** - no need to open ports or setup webhooks
- **Container auto-restarts** - if bot crashes, it will restart automatically

## 🆘 Support

If the bot doesn't work:
1. Check logs: `docker-compose logs -f`
2. Verify all 3 environment variables are set correctly
3. Ensure Google credentials JSON is valid
4. Make sure your Google Sheet is shared with the service account email

---

**That's it! Your bot should now be running on your VDS! 🤖**