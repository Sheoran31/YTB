#!/bin/bash
# Auto-start script for AUTOTRADE bot
# Called by macOS LaunchAgent at 8:45 AM Mon-Fri

cd /Users/purushottam/YOGESH/WORKPLACE/AUTOTRADE

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Activate virtual environment
source venv/bin/activate

# Kill any old trader process
pkill -f "python trader.py" 2>/dev/null

# Wait 2 seconds for cleanup
sleep 2

# Start bot (auto mode — waits for market open, asks PAPER/LIVE on Telegram)
python trader.py > auto_live.log 2>&1 &

echo "$(date) — Bot started (PID: $!)" >> logs/launchd_out.log
