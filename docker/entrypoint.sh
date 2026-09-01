#!/bin/bash
# Entrypoint script for FamilyFinanceProject Docker container
# Handles initialization and application startup

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

# Determine dev mode once to keep behavior consistent across scripts
is_dev_mode() {
    local normalized
    normalized="$(echo "${DEV:-}" | tr '[:upper:]' '[:lower:]' | xargs)"
    if [ "$normalized" = "1" ] || [ "$normalized" = "true" ] || [ "$normalized" = "yes" ] || [ "$normalized" = "on" ]; then
        return 0
    fi
    return 1
}

# Check required environment variables
check_env_vars() {
    log "Checking required environment variables..."
    
    local missing_vars=()
    local is_dev=false
    if is_dev_mode; then
        is_dev=true
    fi
    
    if [ -z "$OPENAI_API_KEY" ]; then
        missing_vars+=("OPENAI_API_KEY")
    fi
    
    if [ "$is_dev" = true ]; then
        if [ -z "$TELEGRAM_TOKEN_DEV" ]; then
            missing_vars+=("TELEGRAM_TOKEN_DEV")
        fi
    else
        if [ -z "$TELEGRAM_TOKEN" ]; then
            missing_vars+=("TELEGRAM_TOKEN")
        fi
    fi
    
    if [ "$is_dev" = true ]; then
        if [ -z "$GOOGLE_SPREADSHEET_ID_DEV" ]; then
            missing_vars+=("GOOGLE_SPREADSHEET_ID_DEV")
        fi
    else
        if [ -z "$GOOGLE_SPREADSHEET_ID" ]; then
            missing_vars+=("GOOGLE_SPREADSHEET_ID")
        fi
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
    
    local creds_path="/app/.google_service_account_credentials.json"
    if [ ! -f "$creds_path" ]; then
        creds_path="/app/google_service_account_credentials.json"
    fi
    
    if [ ! -f "$creds_path" ]; then
        log_error "Google service account credentials file not found"
        log_error "Please ensure .google_service_account_credentials.json is mounted to /app/"
        exit 1
    fi
    
    # Check if the file is valid JSON
    if ! python -m json.tool "$creds_path" > /dev/null 2>&1; then
        log_error "Google service account credentials file is not valid JSON"
        exit 1
    fi
    
    log_success "Google service account credentials file is valid"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    # Create voice_messages directory if it doesn't exist
    if [ ! -d "/app/voice_messages" ]; then
        mkdir -p /app/voice_messages
        log "Created voice_messages directory"
    fi
    
    # Try to set permissions, but don't fail if we can't (volume mount case)
    if chmod 755 /app/voice_messages 2>/dev/null; then
        log "Set permissions for voice_messages directory"
    else
        log_warning "Could not set permissions for voice_messages (likely mounted volume - this is OK)"
    fi
    
    log_success "Directories setup complete"
}

# The application removes each message's OGA and WAV files after processing.
# Periodic and historical audio cleanup is intentionally disabled.

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
    log "Audio cleanup: Per-message enabled; periodic cleanup disabled"
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
    
    if is_dev_mode; then
        log_warning "!!! RUNNING IN DEV MODE !!!"
    fi
    
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
