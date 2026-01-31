#!/bin/bash

# Wrapper script for cron job that ensures market scan runs every 2 days
# This script tracks the last run time and only executes if 2 days have passed
# Also handles git pull before scan and git commit/push after scan

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Get the repository root (parent of cards_binders)
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOCK_FILE="$SCRIPT_DIR/.last_market_scan"
SCAN_SCRIPT="$SCRIPT_DIR/run_market_scan.sh"
DB_FILE="$SCRIPT_DIR/collections.db"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; }

# Check if lock file exists and read last run timestamp
if [ -f "$LOCK_FILE" ]; then
    LAST_RUN=$(cat "$LOCK_FILE")
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_RUN))
    DAYS_PASSED=$((TIME_DIFF / 86400))  # 86400 seconds in a day
    
    if [ $DAYS_PASSED -lt 2 ]; then
        log "Last scan was $DAYS_PASSED day(s) ago. Skipping (needs 2 days)."
        exit 0
    fi
fi

log "Starting automated market scan process..."

# Step 1: Git pull
log "Pulling latest changes from repository..."
cd "$REPO_ROOT"
if ! git pull; then
    error "Git pull failed. Continuing anyway..."
fi

# Step 2: Run the market scan
cd "$SCRIPT_DIR"
log "Running market scan (last run: $(date -r "$LOCK_FILE" 2>/dev/null || echo 'never'))"
if ! "$SCAN_SCRIPT" --source all 25; then
    error "Market scan failed!"
    exit 1
fi

# Step 3: Git add, commit, and push
cd "$REPO_ROOT"
if [ -f "$DB_FILE" ]; then
    log "Adding collections.db to git..."
    git add "$DB_FILE"
    
    if git diff --staged --quiet; then
        warn "No changes to collections.db to commit."
    else
        log "Committing changes..."
        COMMIT_MSG="Automated market scan update - $(date '+%Y-%m-%d %H:%M:%S')"
        git commit -m "$COMMIT_MSG" || warn "Commit failed or nothing to commit"
        
        log "Pushing changes to remote..."
        if git push; then
            success "Changes pushed successfully!"
        else
            error "Git push failed!"
            exit 1
        fi
    fi
else
    warn "collections.db not found at $DB_FILE - skipping git operations"
fi

# Update lock file with current timestamp
date +%s > "$LOCK_FILE"
success "Market scan completed. Next run will be in 2 days."
