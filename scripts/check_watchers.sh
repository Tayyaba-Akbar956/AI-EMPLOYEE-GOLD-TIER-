#!/bin/bash
# Check Status of All Watchers
# Usage: ./check_watchers.sh

echo "=========================================="
echo "AI Employee Silver - Watcher Status"
echo "=========================================="
echo ""

# Function to check if process is running
check_watcher() {
    local name=$1
    local pattern=$2

    if pgrep -f "$pattern" > /dev/null; then
        local pid=$(pgrep -f "$pattern")
        echo "✅ $name: RUNNING (PID: $pid)"
        return 0
    else
        echo "❌ $name: NOT RUNNING"
        return 1
    fi
}

# Check each watcher
check_watcher "Gmail Watcher" "gmail_watcher.py"
check_watcher "Filesystem Watcher" "filesystem_watcher.py"
check_watcher "WhatsApp Watcher" "whatsapp_watcher.js"
check_watcher "LinkedIn Watcher" "linkedin_watcher.py"

echo ""
echo "=========================================="
echo "📊 Detailed Process List"
echo "=========================================="
ps aux | grep -E "(gmail|filesystem|whatsapp|linkedin)_watcher" | grep -v grep

echo ""
echo "=========================================="
echo "📝 Recent Log Activity"
echo "=========================================="

if [ -d "logs" ]; then
    echo ""
    echo "Gmail (last 3 lines):"
    tail -n 3 logs/gmail.log 2>/dev/null || echo "   No log file"

    echo ""
    echo "Filesystem (last 3 lines):"
    tail -n 3 logs/filesystem.log 2>/dev/null || echo "   No log file"

    echo ""
    echo "WhatsApp (last 3 lines):"
    tail -n 3 logs/whatsapp.log 2>/dev/null || echo "   No log file"

    echo ""
    echo "LinkedIn (last 3 lines):"
    tail -n 3 logs/linkedin.log 2>/dev/null || echo "   No log file"
else
    echo "⚠️  Logs directory not found"
fi

echo ""
echo "=========================================="
echo "📁 Vault Status"
echo "=========================================="

if [ -d "AI_Employee_Vault/Inbox" ]; then
    echo "Inbox items:"
    echo "   - Emails: $(find AI_Employee_Vault/Inbox/emails -type f 2>/dev/null | wc -l)"
    echo "   - Files: $(find AI_Employee_Vault/Inbox/files -type f 2>/dev/null | wc -l)"
    echo "   - WhatsApp: $(find AI_Employee_Vault/Inbox/whatsapp -type f 2>/dev/null | wc -l)"
    echo "   - LinkedIn: $(find AI_Employee_Vault/Inbox/linkedin -type f 2>/dev/null | wc -l)"
else
    echo "⚠️  Vault not found"
fi

echo ""
