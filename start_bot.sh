#!/bin/bash
# Auto-start script for AUTOTRADE bot
# Called by macOS LaunchAgent at 8:45 AM Mon-Fri

cd /Users/purushottam/YOGESH/WORKPLACE/AUTOTRADE

# Ensure logs directory exists
mkdir -p logs

# Skip weekends
DOW=$(date +%u)
if [ "$DOW" -gt 5 ]; then
    echo "$(date) — Weekend, skipping" >> logs/launchd_out.log
    exit 0
fi

# Skip if already running (match full path or just trader.py)
if pgrep -f "trader.py" > /dev/null; then
    echo "$(date) — Already running, skipping" >> logs/launchd_out.log
    exit 0
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Activate virtual environment
source venv/bin/activate

# Start bot (auto mode — waits for market open, asks PAPER/LIVE on Telegram)
python trader.py >> auto_live.log 2>&1 &

echo "$(date) — Bot started (PID: $!)" >> logs/launchd_out.log
