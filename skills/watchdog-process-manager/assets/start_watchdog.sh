#!/bin/bash

# Startup script for Watchdog Process Manager
# This script starts the watchdog supervisor with proper configuration

set -e

# Configuration
CONFIG_FILE="${CONFIG_FILE:-./config.yaml}"
LOG_FILE="${LOG_FILE:-/var/log/watchdog-supervisor.log}"
PID_FILE="${PID_FILE:-/var/run/watchdog-supervisor.pid}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if watchdog is already running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # Stale PID file, remove it
            rm -f "$PID_FILE"
            return 1
        fi
    else
        return 1
    fi
}

# Function to start the watchdog
start_watchdog() {
    if is_running; then
        print_error "Watchdog is already running (PID $(cat $PID_FILE))"
        exit 1
    fi

    print_status "Starting Watchdog Process Manager..."

    # Check if config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi

    # Create log directory if it doesn't exist
    LOG_DIR=$(dirname "$LOG_FILE")
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
    fi

    # Start the supervisor in background
    nohup python3 -m watchdog-process-manager.supervisor \
        monitor \
        --config "$CONFIG_FILE" \
        --log-file "$LOG_FILE" \
        > /dev/null 2>&1 &

    # Get the PID of the background process
    SUPERVISOR_PID=$!

    # Write PID to file
    echo $SUPERVISOR_PID > "$PID_FILE"

    # Verify the process is running
    sleep 2
    if ps -p $SUPERVISOR_PID > /dev/null 2>&1; then
        print_status "Watchdog Process Manager started successfully"
        print_status "PID: $SUPERVISOR_PID"
        print_status "Log file: $LOG_FILE"
        print_status "Configuration: $CONFIG_FILE"
    else
        print_error "Failed to start Watchdog Process Manager"
        exit 1
    fi
}

# Function to stop the watchdog
stop_watchdog() {
    if ! is_running; then
        print_warning "Watchdog is not running"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    print_status "Stopping Watchdog Process Manager (PID: $PID)..."

    # Try graceful shutdown first
    kill -TERM "$PID" 2>/dev/null || true

    # Wait for graceful shutdown
    COUNT=0
    while [ $COUNT -lt 30 ] && ps -p "$PID" > /dev/null 2>&1; do
        sleep 1
        COUNT=$((COUNT + 1))
    done

    # If still running, force kill
    if ps -p "$PID" > /dev/null 2>&1; then
        print_warning "Process still running after TERM signal, sending KILL..."
        kill -KILL "$PID" 2>/dev/null || true

        # Wait a bit more
        sleep 2
    fi

    # Remove PID file
    rm -f "$PID_FILE"

    if ps -p "$PID" > /dev/null 2>&1; then
        print_error "Failed to stop Watchdog Process Manager"
        exit 1
    else
        print_status "Watchdog Process Manager stopped successfully"
    fi
}

# Function to restart the watchdog
restart_watchdog() {
    print_status "Restarting Watchdog Process Manager..."
    stop_watchdog
    sleep 2
    start_watchdog
}

# Function to check status
check_status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_status "Watchdog Process Manager is running (PID: $PID)"

            # Show status of managed processes
            echo "Managed processes:"
            python3 -m watchdog-process-manager.supervisor status --config "$CONFIG_FILE" 2>/dev/null || echo "Unable to get process status"
        else
            print_warning "PID file exists but process is not running (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "Watchdog Process Manager is not running"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|status|help}"
    echo ""
    echo "Environment variables:"
    echo "  CONFIG_FILE   Configuration file path (default: ./config.yaml)"
    echo "  LOG_FILE      Log file path (default: /var/log/watchdog-supervisor.log)"
    echo "  PID_FILE      PID file path (default: /var/run/watchdog-supervisor.pid)"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start the watchdog"
    echo "  $0 start --config prod.yaml # Start with specific config"
    echo "  $0 status                   # Check status"
    echo "  $0 stop                     # Stop the watchdog"
    echo "  $0 restart                  # Restart the watchdog"
}

# Main logic
case "$1" in
    start)
        start_watchdog
        ;;
    stop)
        stop_watchdog
        ;;
    restart)
        restart_watchdog
        ;;
    status)
        check_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        if [ -z "$1" ]; then
            show_usage
        else
            print_error "Invalid command: $1"
            show_usage
            exit 1
        fi
        ;;
esac