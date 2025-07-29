#!/bin/bash
# Health check script for FamilyFinanceProject Docker container
# Verifies that the application is running properly

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check function
check_health() {
    local exit_code=0
    
    # Check 1: Health status file (created by entrypoint)
    if [ -f "/tmp/health_status" ]; then
        local status=$(cat /tmp/health_status)
        if [ "$status" != "healthy" ]; then
            echo -e "${RED}Health status: $status${NC}" >&2
            exit_code=1
        fi
    else
        echo -e "${RED}Health status file not found${NC}" >&2
        exit_code=1
    fi
    
    # Check 2: Python application process
    if ! pgrep -f "python.*run_server.py" > /dev/null; then
        echo -e "${RED}Python application process not found${NC}" >&2
        exit_code=1
    fi
    
    # Check 3: Required directories exist and are writable
    if [ ! -d "/app/voice_messages" ]; then
        echo -e "${RED}Voice messages directory not found${NC}" >&2
        exit_code=1
    elif [ ! -w "/app/voice_messages" ]; then
        echo -e "${RED}Voice messages directory not writable${NC}" >&2
        exit_code=1
    fi
    
    # Check 4: Google credentials file exists and is readable
    if [ ! -f "/app/google_service_account_credentials.json" ]; then
        echo -e "${RED}Google credentials file not found${NC}" >&2
        exit_code=1
    elif [ ! -r "/app/google_service_account_credentials.json" ]; then
        echo -e "${RED}Google credentials file not readable${NC}" >&2
        exit_code=1
    fi
    
    # Check 5: Environment variables are set
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
        echo -e "${RED}Missing environment variables: ${missing_vars[*]}${NC}" >&2
        exit_code=1
    fi
    
    # Check 6: Disk space (warn if low)
    local disk_usage=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        echo -e "${YELLOW}Warning: Disk usage is ${disk_usage}%${NC}" >&2
        # Don't fail health check for high disk usage, just warn
    fi
    
    # Check 7: Memory usage (warn if high)
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    if [ "$memory_usage" -gt 90 ]; then
        echo -e "${YELLOW}Warning: Memory usage is ${memory_usage}%${NC}" >&2
        # Don't fail health check for high memory usage, just warn
    fi
    
    # Return result
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}Health check passed${NC}"
        return 0
    else
        echo -e "${RED}Health check failed${NC}" >&2
        return 1
    fi
}

# Extended health check for development
check_health_verbose() {
    echo -e "${BLUE}=== FamilyFinanceProject Health Check ===${NC}"
    
    # Basic checks
    check_health
    local basic_result=$?
    
    # Additional verbose information
    echo -e "${BLUE}=== System Information ===${NC}"
    echo "Timestamp: $(date)"
    echo "Uptime: $(uptime)"
    echo "Python processes:"
    pgrep -fa python || echo "No Python processes found"
    
    echo -e "${BLUE}=== Disk Usage ===${NC}"
    df -h /app
    
    echo -e "${BLUE}=== Memory Usage ===${NC}"
    free -h
    
    echo -e "${BLUE}=== Voice Messages Directory ===${NC}"
    if [ -d "/app/voice_messages" ]; then
        echo "Files count: $(find /app/voice_messages -type f | wc -l)"
        echo "Directory size: $(du -sh /app/voice_messages 2>/dev/null || echo 'Unknown')"
        echo "Oldest file: $(find /app/voice_messages -type f -printf '%T+ %p\n' 2>/dev/null | sort | head -1 || echo 'None')"
        echo "Newest file: $(find /app/voice_messages -type f -printf '%T+ %p\n' 2>/dev/null | sort | tail -1 || echo 'None')"
    else
        echo "Directory not found"
    fi
    
    echo -e "${BLUE}=== Environment Variables ===${NC}"
    echo "OPENAI_API_KEY: $([ -n "$OPENAI_API_KEY" ] && echo 'Set' || echo 'Not set')"
    echo "TELEGRAM_TOKEN: $([ -n "$TELEGRAM_TOKEN" ] && echo 'Set' || echo 'Not set')"
    echo "GOOGLE_SPREADSHEET_ID: $([ -n "$GOOGLE_SPREADSHEET_ID" ] && echo 'Set' || echo 'Not set')"
    echo "DEV: ${DEV:-Not set}"
    echo "AUDIO_CLEANUP_DAYS: ${AUDIO_CLEANUP_DAYS:-7}"
    echo "AUDIO_CLEANUP_ON_START: ${AUDIO_CLEANUP_ON_START:-true}"
    echo "AUDIO_CLEANUP_PERIODIC: ${AUDIO_CLEANUP_PERIODIC:-true}"
    echo "AUDIO_CLEANUP_INTERVAL: ${AUDIO_CLEANUP_INTERVAL:-24}"
    
    echo -e "${BLUE}================================${NC}"
    
    return $basic_result
}

# Main execution
case "${1:-}" in
    "verbose"|"-v"|"--verbose")
        check_health_verbose
        ;;
    *)
        check_health
        ;;
esac