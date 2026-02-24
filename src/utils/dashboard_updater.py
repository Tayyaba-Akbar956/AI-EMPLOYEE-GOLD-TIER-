"""Dashboard Updater - Maintain real-time Dashboard.md with system status"""
import json
from pathlib import Path
from datetime import datetime
from collections import deque

# Import vault management
try:
    from src.utils.vault_management import read_vault_file, write_vault_file, write_log, count_vault_items
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.utils.vault_management import read_vault_file, write_vault_file, write_log, count_vault_items


# Global activity buffer (max 10 activities)
activity_buffer = deque(maxlen=10)


def calculate_vault_counts() -> dict:
    """
    Calculate current item counts for all vault folders.

    Returns:
        Dictionary with counts for each folder
    """
    # Count items in each folder
    inbox_count = count_vault_items("Inbox", recursive=True)

    needs_action_urgent = count_vault_items("Needs_Action/urgent", recursive=False)
    needs_action_normal = count_vault_items("Needs_Action/normal", recursive=False)
    needs_action_total = needs_action_urgent + needs_action_normal

    done_count = count_vault_items("Done", recursive=True)

    return {
        'inbox': inbox_count,
        'needs_action': {
            'total': needs_action_total,
            'urgent': needs_action_urgent,
            'normal': needs_action_normal
        },
        'done': done_count,
        'total_items': inbox_count + needs_action_total + done_count
    }


def check_watcher_process() -> str:
    """Check if watcher process is running"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = ' '.join(proc.info.get('cmdline', []))
            if 'watcher' in cmdline.lower():
                return 'Active'
        return 'Stopped'
    except Exception:
        return 'Unknown'


def get_system_status() -> dict:
    """
    Get current system health and watcher status.

    Returns:
        Dictionary with status indicators
    """
    # Check if watcher process is running
    watcher_status = check_watcher_process()

    # Claude Code is assumed connected if dashboard is being updated
    claude_status = 'Connected'

    # Current time
    last_check = datetime.now().strftime('%H:%M:%S')

    # Overall system status
    if watcher_status == 'Active':
        overall_status = 'Active'
    elif watcher_status == 'Unknown':
        overall_status = 'Warning'
    else:
        overall_status = 'Stopped'

    return {
        'overall': overall_status,
        'watcher': watcher_status,
        'claude': claude_status,
        'last_check': last_check,
        'timestamp': datetime.now().isoformat()
    }


def add_activity(description: str):
    """
    Add new activity to recent activities.

    Args:
        description: Activity description
    """
    timestamp = datetime.now().strftime('%H:%M')
    activity = f"[{timestamp}] {description}"
    activity_buffer.appendleft(activity)


def get_recent_activities() -> str:
    """
    Get formatted recent activities for dashboard.

    Returns:
        Formatted activity list as markdown
    """
    if not activity_buffer:
        return "- No recent activity"

    return '\n'.join(f"- {activity}" for activity in list(activity_buffer)[:10])


def get_stats_file() -> Path:
    """Get path to daily stats file"""
    return Path("AI_Employee_Vault/Logs/daily_stats.json")


def create_new_stats(date: str) -> dict:
    """Create new daily stats dictionary"""
    return {
        'date': date,
        'emails_processed': 0,
        'files_organized': 0,
        'actions_completed': 0,
        'errors': 0
    }


def load_daily_stats() -> dict:
    """
    Load or initialize daily statistics.

    Returns:
        Dictionary with daily stats
    """
    stats_file = get_stats_file()
    today = datetime.now().strftime('%Y-%m-%d')

    if stats_file.exists():
        try:
            stats = json.loads(stats_file.read_text())
            # Reset if new day
            if stats.get('date') != today:
                stats = create_new_stats(today)
        except Exception:
            stats = create_new_stats(today)
    else:
        stats = create_new_stats(today)
        stats_file.parent.mkdir(parents=True, exist_ok=True)

    return stats


def update_daily_stats(stat_type: str):
    """
    Update specific daily statistic.

    Args:
        stat_type: Type of stat to increment ('email', 'file', 'completed', 'error')
    """
    stats = load_daily_stats()

    # Increment appropriate counter
    if stat_type == 'email':
        stats['emails_processed'] += 1
    elif stat_type == 'file':
        stats['files_organized'] += 1
    elif stat_type == 'completed':
        stats['actions_completed'] += 1
    elif stat_type == 'error':
        stats['errors'] += 1

    # Save updated stats
    stats_file = get_stats_file()
    stats_file.write_text(json.dumps(stats, indent=2))


def get_daily_stats_formatted() -> str:
    """
    Get formatted daily statistics for dashboard.

    Returns:
        Formatted stats as markdown
    """
    stats = load_daily_stats()

    return f"""- Emails Processed: {stats['emails_processed']}
- Files Organized: {stats['files_organized']}
- Actions Completed: {stats['actions_completed']}
- Errors: {stats['errors']}"""


def generate_dashboard_content(counts: dict, status: dict) -> str:
    """
    Generate complete Dashboard.md content.

    Args:
        counts: Vault item counts
        status: System status information

    Returns:
        Complete dashboard markdown
    """
    timestamp = status['timestamp']

    dashboard = f"""# AI Employee Dashboard

**Last Updated:** {timestamp}
**Status:** {status['overall']}

## Today's Summary
- Inbox: {counts['inbox']} items
- Needs Action: {counts['needs_action']['total']} items ({counts['needs_action']['urgent']} urgent, {counts['needs_action']['normal']} normal)
- Completed: {counts['done']} items

## Recent Activity
{get_recent_activities()}

## System Status
- Watcher: {status['watcher']}
- Claude Code: {status['claude']}
- Last Check: {status['last_check']}

## Today's Stats
{get_daily_stats_formatted()}

---
*AI Employee v1.0.0 - Bronze Tier*
"""
    return dashboard


def update_dashboard_complete() -> dict:
    """
    Perform complete dashboard update.

    Returns:
        Result dictionary with status
    """
    try:
        # Step 1: Calculate counts
        counts = calculate_vault_counts()

        # Step 2: Get status
        status = get_system_status()

        # Step 3: Generate content
        content = generate_dashboard_content(counts, status)

        # Step 4: Write to file
        result = write_vault_file("Dashboard.md", content)

        if result:
            write_log('INFO', 'DashboardUpdater', 'Dashboard updated successfully')
            return {
                'status': 'success',
                'timestamp': status['timestamp'],
                'counts': counts
            }
        else:
            return {
                'status': 'error',
                'error': 'Failed to write dashboard'
            }
    except Exception as e:
        write_log('ERROR', 'DashboardUpdater', f'Dashboard update failed: {e}')
        return {
            'status': 'error',
            'error': str(e)
        }


def log_and_update(activity: str, stat_type: str = None):
    """
    Add activity and update dashboard in one call.
    This is the MAIN function to call after processing any item.

    Args:
        activity: Activity description to log (e.g., "Processed file: document.pdf → Inbox/")
        stat_type: Optional stat type to increment ('email', 'file', 'completed', 'error')

    Example:
        >>> log_and_update("Detected new file: report.pdf", stat_type='file')
        >>> log_and_update("Moved invoice.pdf → Needs_Action/urgent/", stat_type='file')
    """
    # Add activity
    add_activity(activity)

    # Update stats if provided
    if stat_type:
        update_daily_stats(stat_type)

    # Full dashboard update
    result = update_dashboard_complete()

    # Print confirmation for CLI visibility
    if result['status'] == 'success':
        print(f"📊 Dashboard updated: {activity}")

    return result


def quick_update_counts():
    """
    Quick update - only refresh counts and timestamp.
    Use this when you want fast updates without regenerating everything.
    """
    try:
        counts = calculate_vault_counts()
        status = get_system_status()

        # Read current dashboard
        current_content = read_vault_file("Dashboard.md")
        if not current_content:
            # If no dashboard exists, do full update
            return update_dashboard_complete()

        # Replace just the counts and timestamp
        lines = current_content.split('\n')
        new_lines = []

        for line in lines:
            if line.startswith('**Last Updated:**'):
                new_lines.append(f"**Last Updated:** {status['timestamp']}")
            elif line.startswith('- Inbox:'):
                new_lines.append(f"- Inbox: {counts['inbox']} items")
            elif line.startswith('- Needs Action:'):
                new_lines.append(f"- Needs Action: {counts['needs_action']['total']} items ({counts['needs_action']['urgent']} urgent, {counts['needs_action']['normal']} normal)")
            elif line.startswith('- Completed:'):
                new_lines.append(f"- Completed: {counts['done']} items")
            else:
                new_lines.append(line)

        write_vault_file("Dashboard.md", '\n'.join(new_lines))
        return {'status': 'success', 'counts': counts}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# Auto-update trigger functions - Call these from watchers/processors
def on_file_detected(filename: str, destination: str = None):
    """
    Call this when a new file is detected by the watcher.

    Args:
        filename: Name of the detected file
        destination: Where it was moved (optional)
    """
    if destination:
        activity = f"File detected: {filename} → {destination}"
    else:
        activity = f"File detected: {filename}"
    return log_and_update(activity, stat_type='file')


def on_email_processed(subject: str, sender: str, destination: str):
    """
    Call this when an email is processed.

    Args:
        subject: Email subject
        sender: Email sender
        destination: Where it was routed
    """
    activity = f"Email: '{subject}' from {sender} → {destination}"
    return log_and_update(activity, stat_type='email')


def on_task_completed(task_name: str):
    """
    Call this when a task/action is completed.

    Args:
        task_name: Description of completed task
    """
    activity = f"Completed: {task_name}"
    return log_and_update(activity, stat_type='completed')


def on_error(error_msg: str, component: str = "System"):
    """
    Call this when an error occurs.

    Args:
        error_msg: Error message
        component: Component that had the error
    """
    activity = f"ERROR [{component}]: {error_msg}"
    return log_and_update(activity, stat_type='error')
