# Setup Task Scheduler - Gold Tier Feature 7
# Registers all Windows Task Scheduler tasks for AI Employee automation

# Requires Administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script requires Administrator privileges" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
    exit 1
}

Write-Host "Setting up Windows Task Scheduler tasks..." -ForegroundColor Cyan
Write-Host "==========================================`n" -ForegroundColor Cyan

# Get project root
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = (Get-Command python).Source

# Task 1: Orchestrator on login
Write-Host "Creating task: AIEmployee_Orchestrator (on login)" -ForegroundColor Yellow
$action1 = New-ScheduledTaskAction -Execute "pm2" -Argument "resurrect"
$trigger1 = New-ScheduledTaskTrigger -AtLogOn
$principal1 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "AIEmployee_Orchestrator" -Action $action1 -Trigger $trigger1 -Principal $principal1 -Settings $settings1 -Force | Out-Null
Write-Host "✓ AIEmployee_Orchestrator created" -ForegroundColor Green

# Task 2: Morning Briefing (Monday 7:00 AM)
Write-Host "`nCreating task: AIEmployee_MorningBriefing (Monday 7:00 AM)" -ForegroundColor Yellow
$action2 = New-ScheduledTaskAction -Execute $pythonPath -Argument "$projectRoot\src\orchestrator\orchestrator.py --task briefing" -WorkingDirectory $projectRoot
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 7:00AM
$principal2 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "AIEmployee_MorningBriefing" -Action $action2 -Trigger $trigger2 -Principal $principal2 -Settings $settings2 -Force | Out-Null
Write-Host "✓ AIEmployee_MorningBriefing created" -ForegroundColor Green

# Task 3: Social Post (Friday 10:00 AM)
Write-Host "`nCreating task: AIEmployee_SocialPost (Friday 10:00 AM)" -ForegroundColor Yellow
$action3 = New-ScheduledTaskAction -Execute $pythonPath -Argument "$projectRoot\src\orchestrator\orchestrator.py --task social" -WorkingDirectory $projectRoot
$trigger3 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 10:00AM
$principal3 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "AIEmployee_SocialPost" -Action $action3 -Trigger $trigger3 -Principal $principal3 -Settings $settings3 -Force | Out-Null
Write-Host "✓ AIEmployee_SocialPost created" -ForegroundColor Green

# Task 4: Weekly Audit (Sunday 11:00 PM)
Write-Host "`nCreating task: AIEmployee_WeeklyAudit (Sunday 11:00 PM)" -ForegroundColor Yellow
$action4 = New-ScheduledTaskAction -Execute $pythonPath -Argument "$projectRoot\src\orchestrator\orchestrator.py --task audit" -WorkingDirectory $projectRoot
$trigger4 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 11:00PM
$principal4 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings4 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "AIEmployee_WeeklyAudit" -Action $action4 -Trigger $trigger4 -Principal $principal4 -Settings $settings4 -Force | Out-Null
Write-Host "✓ AIEmployee_WeeklyAudit created" -ForegroundColor Green

# Task 5: Watcher Health Check (Every 30 minutes)
Write-Host "`nCreating task: AIEmployee_WatcherHealth (Every 30 minutes)" -ForegroundColor Yellow
$action5 = New-ScheduledTaskAction -Execute "pm2" -Argument "resurrect"
$trigger5 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::MaxValue)
$principal5 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings5 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "AIEmployee_WatcherHealth" -Action $action5 -Trigger $trigger5 -Principal $principal5 -Settings $settings5 -Force | Out-Null
Write-Host "✓ AIEmployee_WatcherHealth created" -ForegroundColor Green

# Show all created tasks
Write-Host "`nVerifying created tasks:" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object {$_.TaskName -like "AIEmployee_*"} | Format-Table TaskName, State, @{Label="Next Run";Expression={(Get-ScheduledTaskInfo $_).NextRunTime}} -AutoSize

Write-Host "`n✓ All Task Scheduler tasks created successfully!" -ForegroundColor Green
Write-Host "`nYou can view/manage these tasks in Task Scheduler (taskschd.msc)" -ForegroundColor Gray
Write-Host "To remove all tasks, run: Get-ScheduledTask | Where-Object {`$_.TaskName -like 'AIEmployee_*'} | Unregister-ScheduledTask -Confirm:`$false" -ForegroundColor Gray
