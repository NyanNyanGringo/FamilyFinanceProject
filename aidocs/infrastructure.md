# Infrastructure Documentation

## Overview
The FamilyFinanceProject uses Docker for containerization and deployment, making it easy to run on local machines and VDS/VPS servers.

## Docker Architecture

### Container Setup
- **Base Image**: Python 3.10-slim
- **Working Directory**: /app
- **User**: Non-root user (app) with UID 1000
- **Health Check**: Custom health check script at 60-second intervals

### Docker Compose Configuration

#### Services
```yaml
familyfinance-bot:
  - Build from local Dockerfile
  - Automatic restart policy
  - Environment variables from .env file
  - Volume mounts for:
    - Voice messages persistence
    - Google credentials
    - Logs directory
```

#### Volumes
1. **Voice Messages**: `./voice_messages:/app/voice_messages`
   - Stores audio files from users
   - Persists between container restarts
   - Automatic cleanup recommended

2. **Google Credentials**: `.google_service_account_credentials.json` mounted as read-only

3. **Logs**: `./logs:/app/logs` for application logging

### Recent Docker Improvements (August 2025)

#### Poetry Installation Fix
- Resolved issue with Poetry being reinstalled on every build
- Improved Docker layer caching by separating Poetry installation from dependency installation
- Build process now properly caches Python dependencies

#### Permission Handling
- Added graceful error handling for chmod operations
- Handles volume mount cases where permissions can't be changed
- Prevents container startup failures due to permission errors

## Deployment Methods

### Local Development
```bash
docker-compose up -d
```

### Production Deployment (VDS/VPS)
1. **One-Command Deployment**: `./deploy-simple.sh myvps`
2. **Manual Deployment**: SSH + docker-compose

### Health Monitoring
- Health check endpoint runs every 60 seconds
- Verifies bot connectivity and basic functionality
- Container automatically restarts on health check failure

## Security Considerations

### File Permissions
- Application runs as non-root user
- Sensitive files (credentials) mounted as read-only
- Voice messages directory requires write permissions

### Environment Variables
- Stored in `.env` file (not committed to git)
- Contains:
  - OPENAI_API_KEY
  - TELEGRAM_TOKEN
  - GOOGLE_SPREADSHEET_ID

## Maintenance

### Log Management
- Logs stored in `/app/logs` directory
- Accessible via: `docker-compose logs -f`

### Voice Messages Cleanup
- Voice files accumulate over time
- Manual cleanup recommended:
  ```bash
  docker exec familyfinance-bot find /app/voice_messages -type f -mtime +7 -delete
  ```

### Container Updates
```bash
# Pull latest changes
git pull

# Rebuild container
docker-compose build

# Restart with new version
docker-compose up -d
```

## Troubleshooting

### Common Issues
1. **Container not starting**: Check logs with `docker-compose logs`
2. **Permission errors**: Verify volume mount permissions
3. **High memory usage**: Check voice messages accumulation
4. **Bot not responding**: Verify API keys in .env file

### Debug Commands
```bash
# Check container status
docker-compose ps

# View environment variables
docker exec familyfinance-bot env | grep -E "(OPENAI|TELEGRAM|GOOGLE)"

# Test health check
docker exec familyfinance-bot /usr/local/bin/healthcheck.sh

# Interactive shell
docker exec -it familyfinance-bot /bin/bash
```