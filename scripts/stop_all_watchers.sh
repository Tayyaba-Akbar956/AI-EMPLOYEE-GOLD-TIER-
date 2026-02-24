#!/bin/bash
# Stop All Watchers Script for AI Employee Silver
# Usage: ./stop_all_watchers.sh

echo "=========================================="
echo "AI Employee Silver - Stopping All Watchers"
echo "=========================================="
echo ""

# Check if PID file exists
if [ -f ".watcher_pids" ]; then
    echo "📋 Reading saved PIDs..."
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid
            echo "   ✅ Stopped process: $pid"
        else
            echo "   ⏭️  Process $pid not running"
        fi
    done < .watcher_pids
    rm .watcher_pids
    echo ""
fi

# Kill any remaining watcher processes
echo "🔍 Checking for remaining watcher processes..."

# Stop Python watchers
pkill -f "gmail_watcher.py" && echo "   ✅ Stopped Gmail watcher"
pkill -f "filesystem_watcher.py" && echo "   ✅ Stopped Filesystem watcher"
pkill -f "linkedin_watcher.py" && echo "   ✅ Stopped LinkedIn watcher"

# Stop Node.js watcher
pkill -f "whatsapp_watcher.js" && echo "   ✅ Stopped WhatsApp watcher"

echo ""
echo "=========================================="
echo "✅ All watchers stopped!"
echo "=========================================="
echo ""
echo "📊 Verify:"
echo "   ps aux | grep -E '(gmail|filesystem|whatsapp|linkedin)_watcher'"
echo ""
