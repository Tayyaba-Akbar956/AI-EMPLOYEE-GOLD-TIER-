# Check Watchers - Gold Tier Feature 7
# Shows PM2 status and health summary for all watchers

Write-Host "AI Employee Watcher Health Check" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Get PM2 status
Write-Host "PM2 Process Status:" -ForegroundColor Yellow
pm2 status

# Get detailed info for each watcher
Write-Host "`nDetailed Health Summary:" -ForegroundColor Yellow
Write-Host "------------------------`n" -ForegroundColor Yellow

$watchers = @("gmail-watcher", "whatsapp-watcher", "linkedin-watcher", "file-watcher", "orchestrator")

foreach ($watcher in $watchers) {
    $info = pm2 info $watcher 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $watcher" -ForegroundColor Green

        # Parse status from pm2 info output
        $status = $info | Select-String "status" | Select-Object -First 1
        $uptime = $info | Select-String "uptime" | Select-Object -First 1
        $restarts = $info | Select-String "restarts" | Select-Object -First 1

        if ($status) { Write-Host "  $status" -ForegroundColor Gray }
        if ($uptime) { Write-Host "  $uptime" -ForegroundColor Gray }
        if ($restarts) { Write-Host "  $restarts" -ForegroundColor Gray }
        Write-Host ""
    } else {
        Write-Host "✗ $watcher - NOT RUNNING" -ForegroundColor Red
        Write-Host ""
    }
}

# Check for errors in logs
Write-Host "Recent Errors (last 50 lines):" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow
$errors = pm2 logs --err --lines 50 --nostream 2>$null | Select-String -Pattern "error|exception|failed" -CaseSensitive:$false
if ($errors) {
    $errors | ForEach-Object { Write-Host $_ -ForegroundColor Red }
} else {
    Write-Host "No recent errors found" -ForegroundColor Green
}

Write-Host "`nUse 'pm2 logs <name>' to view specific watcher logs" -ForegroundColor Gray
Write-Host "Use 'pm2 monit' for real-time monitoring" -ForegroundColor Gray
