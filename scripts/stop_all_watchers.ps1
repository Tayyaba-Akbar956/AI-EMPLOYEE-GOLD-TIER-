# Stop All Watchers - Gold Tier Feature 7
# Stops all PM2 processes for the AI Employee system

Write-Host "Stopping AI Employee watchers..." -ForegroundColor Cyan

# Stop all PM2 processes
Write-Host "`nStopping all processes..." -ForegroundColor Yellow
pm2 stop all

# Show status
Write-Host "`nCurrent status:" -ForegroundColor Cyan
pm2 status

Write-Host "`n✓ All watchers stopped successfully!" -ForegroundColor Green
Write-Host "Use 'pm2 start all' to restart all processes" -ForegroundColor Gray
Write-Host "Use 'pm2 delete all' to remove all processes" -ForegroundColor Gray
