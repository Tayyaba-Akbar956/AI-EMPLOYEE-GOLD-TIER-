# Start All Watchers - Gold Tier Feature 7
# Starts all 5 PM2 processes for the AI Employee system

Write-Host "Starting AI Employee watchers..." -ForegroundColor Cyan

# Get project root
$projectRoot = Split-Path -Parent $PSScriptRoot

# Start Gmail watcher
Write-Host "`nStarting Gmail watcher..." -ForegroundColor Yellow
pm2 start "$projectRoot\src\watchers\gmail_watcher.py" --interpreter python3 --name gmail-watcher

# Start WhatsApp watcher
Write-Host "Starting WhatsApp watcher..." -ForegroundColor Yellow
pm2 start "$projectRoot\src\watchers\whatsapp\whatsapp_watcher.js" --name whatsapp-watcher

# Start LinkedIn watcher
Write-Host "Starting LinkedIn watcher..." -ForegroundColor Yellow
pm2 start "$projectRoot\src\watchers\linkedin_watcher.py" --interpreter python3 --name linkedin-watcher

# Start Filesystem watcher
Write-Host "Starting Filesystem watcher..." -ForegroundColor Yellow
pm2 start "$projectRoot\src\watchers\filesystem_watcher.py" --interpreter python3 --name file-watcher

# Start Orchestrator
Write-Host "Starting Orchestrator..." -ForegroundColor Yellow
pm2 start "$projectRoot\src\orchestrator\orchestrator.py" --interpreter python3 --name orchestrator

# Save PM2 process list
Write-Host "`nSaving PM2 process list..." -ForegroundColor Yellow
pm2 save

# Show status
Write-Host "`nCurrent status:" -ForegroundColor Cyan
pm2 status

Write-Host "`n✓ All watchers started successfully!" -ForegroundColor Green
Write-Host "Use 'pm2 logs' to view logs" -ForegroundColor Gray
Write-Host "Use 'pm2 monit' for real-time monitoring" -ForegroundColor Gray
