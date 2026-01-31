#!/bin/bash

# Script to set up cron job for market scan (runs every 2 days)
# This will add a cron job that runs daily at 2 AM, but the wrapper script
# ensures it only executes if 2 days have passed since the last run

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_SCRIPT="$SCRIPT_DIR/run_market_scan_cron.sh"

# Create the cron job entry
# Runs daily at 2:00 AM - the wrapper script handles the 2-day logic
CRON_ENTRY="0 2 * * * $CRON_SCRIPT >> $SCRIPT_DIR/market_scan_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT"; then
    echo "Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT" | crontab -
fi

# Add the new cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "The market scan will run every 2 days at 2:00 AM"
echo "Logs will be saved to: $SCRIPT_DIR/market_scan_cron.log"
echo ""
echo "To view your cron jobs: crontab -l"
echo "To remove this cron job: crontab -e (then delete the line)"
echo ""
echo "To test the script manually: $CRON_SCRIPT"
