@echo off
REM Stop WhatsApp Watcher - Windows Script

echo Stopping WhatsApp watcher...

REM Kill Node.js processes running whatsapp_watcher
for /f "tokens=2" %%i in ('tasklist ^| findstr /i "node.exe"') do (
    taskkill /PID %%i /F 2>nul
)

REM Kill Chrome processes started by Puppeteer
for /f "tokens=2" %%i in ('tasklist ^| findstr /i "chrome.exe"') do (
    taskkill /PID %%i /F 2>nul
)

echo WhatsApp watcher stopped!
echo You can now restart it with: node whatsapp_watcher.js
