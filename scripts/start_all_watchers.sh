#!/bin/bash
# Start All Watchers Script for AI Employee Silver
# Usage: ./start_all_watchers.sh

echo "=========================================="
echo "AI Employee Silver - Starting All Watchers"
echo "=========================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Activating .venv..."
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        echo "❌ Virtual environment not found!"
        echo "Run: python -m venv .venv"
        exit 1
    fi
fi

echo "✅ Virtual environment active"
echo ""

# Start Gmail Watcher
echo "1️⃣  Starting Gmail Watcher..."
python src/watchers/gmail_watcher.py > logs/gmail.log 2>&1 &
GMAIL_PID=$!
echo "   ✅ Gmail watcher started (PID: $GMAIL_PID)"

# Start Filesystem Watcher
echo "2️⃣  Starting Filesystem Watcher..."
python src/watchers/filesystem_watcher.py > logs/filesystem.log 2>&1 &
FILESYSTEM_PID=$!
echo "   ✅ Filesystem watcher started (PID: $FILESYSTEM_PID)"

# Start WhatsApp Watcher
echo "3️⃣  Starting WhatsApp Watcher..."
if [ -d "src/watchers/whatsapp/node_modules" ]; then
    node src/watchers/whatsapp/whatsapp_watcher.js > logs/whatsapp.log 2>&1 &
    WHATSAPP_PID=$!
    echo "   ✅ WhatsApp watcher started (PID: $WHATSAPP_PID)"
else
    echo "   ⚠️  WhatsApp dependencies not installed"
    echo "   Run: cd src/watchers/whatsapp && npm install"
fi

# Start LinkedIn Watcher
echo "4️⃣  Starting LinkedIn Watcher..."
python src/watchers/linkedin_watcher.py > logs/linkedin.log 2>&1 &
LINKEDIN_PID=$!
echo "   ✅ LinkedIn watcher started (PID: $LINKEDIN_PID)"

# Save PIDs to file
echo "$GMAIL_PID" > .watcher_pids
echo "$FILESYSTEM_PID" >> .watcher_pids
if [ ! -z "$WHATSAPP_PID" ]; then
    echo "$WHATSAPP_PID" >> .watcher_pids
fi
echo "$LINKEDIN_PID" >> .watcher_pids

echo ""
echo "=========================================="
echo "✅ All watchers started successfully!"
echo "=========================================="
echo ""
echo "📊 Status:"
echo "   - Gmail: PID $GMAIL_PID"
echo "   - Filesystem: PID $FILESYSTEM_PID"
if [ ! -z "$WHATSAPP_PID" ]; then
    echo "   - WhatsApp: PID $WHATSAPP_PID"
fi
echo "   - LinkedIn: PID $LINKEDIN_PID"
echo ""
echo "📝 Logs:"
echo "   - View all: tail -f logs/*.log"
echo "   - Gmail: tail -f logs/gmail.log"
echo "   - Filesystem: tail -f logs/filesystem.log"
echo "   - WhatsApp: tail -f logs/whatsapp.log"
echo "   - LinkedIn: tail -f logs/linkedin.log"
echo ""
echo "🛑 To stop all watchers:"
echo "   ./stop_all_watchers.sh"
echo "   OR: pkill -f watcher"
echo ""
echo "✅ Watchers are now running in background!"
