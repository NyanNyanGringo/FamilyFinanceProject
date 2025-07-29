#!/bin/bash

# =============================================================================
# FamilyFinanceProject - Simple One-Command VPS Deployment
# Uses Docker Context for seamless remote deployment
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Check if context name provided
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <vps-context-name>"
    echo "Example: $0 myvps"
    echo ""
    echo "If context doesn't exist, it will be created."
    echo "You'll need: VPS IP, username, and SSH key access"
    exit 1
fi

CONTEXT_NAME="$1"

# Check if context exists
if ! docker context ls | grep -q "^$CONTEXT_NAME "; then
    log_info "Context '$CONTEXT_NAME' not found. Creating new context..."
    echo ""
    read -p "Enter VPS IP address: " VPS_IP
    read -p "Enter SSH username (default: root): " SSH_USER
    SSH_USER=${SSH_USER:-root}
    
    log_info "Creating Docker context for $SSH_USER@$VPS_IP"
    docker context create "$CONTEXT_NAME" --docker "host=ssh://$SSH_USER@$VPS_IP"
    
    log_info "Testing connection..."
    docker --context "$CONTEXT_NAME" version >/dev/null
    log_success "Context created and tested successfully!"
else
    log_info "Using existing context: $CONTEXT_NAME"
fi

# Deploy to VPS
log_info "Deploying to VPS using context: $CONTEXT_NAME"

# Switch context and deploy
docker context use "$CONTEXT_NAME"
docker-compose down 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# Check deployment
log_info "Checking deployment status..."
sleep 5
if docker-compose ps | grep -q "Up"; then
    log_success "Deployment successful! Bot is running on VPS."
    echo ""
    echo "Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop bot:  docker-compose down"
    echo "  Restart:   docker-compose restart"
else
    log_warning "Container may not be running. Check logs:"
    docker-compose logs --tail=20
fi

# Switch back to default context
docker context use default
log_info "Switched back to local context"