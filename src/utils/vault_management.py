"""Vault Management Module - Core file operations for AI Employee Vault"""
from pathlib import Path
from datetime import datetime
import re


def read_vault_file(filename: str) -> str | None:
    """
    Read file content from vault.

    Args:
        filename: Path relative to vault root (e.g., "Dashboard.md" or "Inbox/email.md")

    Returns:
        File content as string, or None if file doesn't exist
    """
    vault_base = Path("AI_Employee_Vault")
    file_path = vault_base / filename

    try:
        return file_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        write_log("ERROR", "VaultManager", f"File not found: {filename}")
        return None
    except Exception as e:
        write_log("ERROR", "VaultManager", f"Error reading {filename}: {e}")
        return None


def write_vault_file(filename: str, content: str) -> bool:
    """
    Write content to vault file.

    Args:
        filename: Path relative to vault root
        content: Content to write

    Returns:
        True if successful, False otherwise
    """
    vault_base = Path("AI_Employee_Vault")
    file_path = vault_base / filename

    try:
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically
        file_path.write_text(content, encoding='utf-8')

        write_log("INFO", "VaultManager", f"Wrote file: {filename}")
        return True
    except Exception as e:
        write_log("ERROR", "VaultManager", f"Error writing {filename}: {e}")
        return False


def list_vault_directory(directory: str, pattern: str = "*.md") -> list[str]:
    """
    List files in vault directory.

    Args:
        directory: Directory path relative to vault root
        pattern: Glob pattern for filtering (default: "*.md")

    Returns:
        List of filenames
    """
    vault_base = Path("AI_Employee_Vault")
    dir_path = vault_base / directory

    if not dir_path.exists():
        return []

    return [f.name for f in dir_path.glob(pattern) if f.is_file()]


def count_vault_items(directory: str, recursive: bool = True) -> int:
    """
    Count markdown files in directory.

    Args:
        directory: Directory path relative to vault root
        recursive: Count in subdirectories too (default: True)

    Returns:
        Number of .md files found
    """
    vault_base = Path("AI_Employee_Vault")
    dir_path = vault_base / directory

    if not dir_path.exists():
        return 0

    if recursive:
        return len(list(dir_path.rglob("*.md")))
    else:
        return len(list(dir_path.glob("*.md")))


def write_log(level: str, component: str, message: str):
    """
    Write entry to daily log file.

    Args:
        level: Log level (INFO, WARN, ERROR)
        component: Component name (e.g., "VaultManager", "EmailProcessor")
        message: Log message
    """
    timestamp = datetime.now().isoformat()
    log_dir = Path("AI_Employee_Vault/Logs")
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    # Ensure logs directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Format log entry
    log_entry = f"[{timestamp}] [{level}] [{component}] {message}\n"

    # Append to log file
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

    # Also add to dashboard activity buffer for real-time updates
    try:
        from src.utils.dashboard_updater import add_activity
        # Create a user-friendly activity message
        activity_msg = f"[{component}] {message}"
        add_activity(activity_msg)
    except Exception:
        # Silently fail if dashboard updater not available
        pass


def update_dashboard_timestamp():
    """Update Dashboard.md with current timestamp"""
    content = read_vault_file("Dashboard.md")
    if not content:
        return False

    # Update timestamp
    timestamp = datetime.now().isoformat()
    content = re.sub(
        r'\*\*Last Updated:\*\* .+',
        f'**Last Updated:** {timestamp}',
        content
    )

    return write_vault_file("Dashboard.md", content)


def get_inbox_count() -> int:
    """Get total number of items in Inbox"""
    return count_vault_items("Inbox", recursive=True)


def get_needs_action_count() -> dict:
    """Get counts for Needs_Action folder"""
    return {
        'urgent': count_vault_items("Needs_Action/urgent", recursive=False),
        'normal': count_vault_items("Needs_Action/normal", recursive=False),
        'total': count_vault_items("Needs_Action", recursive=True)
    }


def get_done_count() -> int:
    """Get total number of completed items"""
    return count_vault_items("Done", recursive=True)
