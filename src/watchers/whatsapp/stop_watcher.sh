#!/bin/bash
# Stop WhatsApp Watcher - Cross-platform script

echo "Stopping WhatsApp watcher..."

# Kill node processes
echo "Stopping Node.js processes..."
tasklist //FI "IMAGENAME eq node.exe" 2>nul | grep node.exe | awk '{print $2}' | while read pid; do
    taskkill //PID $pid //F 2>nul
done

# Kill Chrome processes started by Puppeteer
echo "Stopping Chrome processes..."
tasklist //FI "IMAGENAME eq chrome.exe" 2>nul | grep chrome.exe | awk '{print $2}' | while read pid; do
    taskkill //PID $pid //F 2>nul
done

# Clean up session lock
echo "Cleaning up session locks..."
rm -rf .wwebjs_auth/session/SingletonLock 2>/dev/null
rm -rf .wwebjs_auth/session/SingletonSocket 2>/dev/null
rm -rf .wwebjs_auth/session/SingletonCookie 2>/dev/null

echo ""
echo "✅ WhatsApp watcher stopped!"
echo "You can now restart it with: node whatsapp_watcher.js"
