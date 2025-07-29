#!/bin/bash
# Entrypoint script for FamilyFinanceProject Docker container
# Handles initialization, audio cleanup, and application startup

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] ENTRYPOINT:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ENTRYPOINT:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ENTRYPOINT:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ENTRYPOINT:${NC} $1"
}

# Check required environment variables
check_env_vars() {
    log "Checking required environment variables..."
    
    local missing_vars=()
    
    if [ -z "$OPENAI_API_KEY" ]; then
        missing_vars+=("OPENAI_API_KEY")
    fi
    
    if [ -z "$TELEGRAM_TOKEN" ]; then
        missing_vars+=("TELEGRAM_TOKEN")
    fi
    
    if [ -z "$GOOGLE_SPREADSHEET_ID" ]; then
        missing_vars+=("GOOGLE_SPREADSHEET_ID")
    fi
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        log_error "Please check your .env file or environment configuration"
        exit 1
    fi
    
    log_success "All required environment variables are present"
}

# Check Google credentials file
check_credentials() {
    log "Checking Google service account credentials..."
    
    if [ ! -f "/app/.google_service_account_credentials.json" ]; then
        log_error "Google service account credentials file not found"
        log_error "Please ensure .google_service_account_credentials.json is mounted to /app/"
        exit 1
    fi
    
    # Check if the file is valid JSON
    if ! python -m json.tool /app/.google_service_account_credentials.json > /dev/null 2>&1; then
        log_error "Google service account credentials file is not valid JSON"
        exit 1
    fi
    
    log_success "Google service account credentials file is valid"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p /app/voice_messages
    
    # Set proper permissions
    chmod 755 /app/voice_messages
    
    log_success "Directories created successfully"
}

# Audio cleanup functionality removed - voice messages will accumulate
# Consider manual cleanup if disk space becomes an issue

# Health check setup
setup_health_check() {
    log "Setting up health check..."
    
    # Create a simple health check file
    echo "healthy" > /tmp/health_status
    
    log_success "Health check setup complete"
}

# Display configuration
show_config() {
    log "=== FamilyFinanceProject Configuration ==="
    log "Development mode: ${DEV:-false}"
    log "Python version: $(python --version)"
    log "Working directory: $(pwd)"
    log "Audio cleanup: Disabled (voice files will accumulate)"
    log "=============================================="
}

# Graceful shutdown handler
shutdown_handler() {
    log "Received shutdown signal, cleaning up..."
    
    # Kill background processes
    jobs -p | xargs -r kill
    
    # Update health status
    echo "shutting_down" > /tmp/health_status
    
    log_success "Cleanup complete, exiting..."
    exit 0
}

# Set up signal handlers
trap shutdown_handler SIGTERM SIGINT

# Main initialization
main() {
    log "Starting FamilyFinanceProject container initialization..."
    
    # Run initialization steps
    check_env_vars
    check_credentials
    create_directories
    setup_health_check
    show_config
    
    log_success "Container initialization complete!"
    log "Starting application: $*"
    
    # Start the application
    exec "$@"
}

# Run main function with all arguments
main "$@"