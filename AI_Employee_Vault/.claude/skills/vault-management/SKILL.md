---
name: vault-management
description: Manage all file operations within the AI_Employee_Vault Obsidian vault. Use when Claude needs to read, write, list, or count files in the vault structure. Handles Dashboard.md updates, logging to Logs/, and all vault file operations.
---

# Vault Management Skill

This skill provides comprehensive file management capabilities for the AI_Employee_Vault Obsidian vault system. It handles all read, write, list, and count operations across the vault's folder structure.

## Purpose

Enable Claude to autonomously manage the Obsidian vault that serves as the core data store for the AI Employee system. This includes reading from and writing to markdown files, counting items in directories, and maintaining system logs.

## Core Capabilities

### 1. File Reading
Read any markdown file from the vault:
```python
from pathlib import Path

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
```

### 2. File Writing
Write or update files in the vault:
```python
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
```

### 3. Directory Listing
List files in any vault directory:
```python
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
```

### 4. Item Counting
Count items in vault directories:
```python
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
```

### 5. Logging Operations
Write to daily log files:
```python
from datetime import datetime

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
```

## Vault Structure

The AI_Employee_Vault has this structure:
```
AI_Employee_Vault/
├── Dashboard.md           # Real-time system status
├── Company_Handbook.md    # Rules and guidelines
├── Inbox/                 # Incoming items
│   ├── emails/
│   └── files/
├── Needs_Action/          # Items requiring action
│   ├── urgent/
│   └── normal/
├── Done/                  # Completed items
│   └── YYYY-MM/
└── Logs/                  # Daily logs
    └── YYYY-MM-DD.log
```

## Common Operations

### Update Dashboard
```python
def update_dashboard_timestamp():
    """Update Dashboard.md with current timestamp"""
    content = read_vault_file("Dashboard.md")
    if not content:
        return False
    
    # Update timestamp
    timestamp = datetime.now().isoformat()
    import re
    content = re.sub(
        r'\*\*Last Updated:\*\* .+',
        f'**Last Updated:** {timestamp}',
        content
    )
    
    return write_vault_file("Dashboard.md", content)
```

### Get Inbox Count
```python
def get_inbox_count() -> int:
    """Get total number of items in Inbox"""
    return count_vault_items("Inbox", recursive=True)
```

### Get Needs Action Count
```python
def get_needs_action_count() -> dict:
    """Get counts for Needs_Action folder"""
    return {
        'urgent': count_vault_items("Needs_Action/urgent", recursive=False),
        'normal': count_vault_items("Needs_Action/normal", recursive=False),
        'total': count_vault_items("Needs_Action", recursive=True)
    }
```

### Get Done Count
```python
def get_done_count() -> int:
    """Get total number of completed items"""
    return count_vault_items("Done", recursive=True)
```

## Error Handling

Always handle errors gracefully:
- File not found → Return None or empty list, log error
- Permission denied → Log error with suggested fix
- Invalid path → Validate path format, log error
- Disk full → Log critical error, alert immediately

## Best Practices

1. **Always log operations**: Every write should be logged
2. **Use atomic writes**: Write to temp file, then rename
3. **Validate paths**: Ensure paths are within vault
4. **Handle Unicode**: Use UTF-8 encoding consistently
5. **Create directories**: Use `mkdir(parents=True, exist_ok=True)`
6. **Check existence**: Verify files exist before reading

## Examples

### Example 1: Read Dashboard
```python
dashboard_content = read_vault_file("Dashboard.md")
if dashboard_content:
    print(dashboard_content)
```

### Example 2: Save New Email
```python
email_md = """# Email: Invoice Due
**From:** client@example.com
**Date:** 2026-02-15

Invoice #123 is due.
"""

write_vault_file("Inbox/emails/2026-02-15_invoice.md", email_md)
```

### Example 3: Count All Items
```python
counts = {
    'inbox': get_inbox_count(),
    'needs_action': get_needs_action_count(),
    'done': get_done_count()
}
print(f"Inbox: {counts['inbox']}")
print(f"Needs Action: {counts['needs_action']['total']}")
print(f"Done: {counts['done']}")
```

## Integration

This skill is used by:
- email-processor: Saves processed emails to vault
- file-organizer: Saves organized files to vault
- dashboard-updater: Updates Dashboard.md and counts items

## Notes

- All file paths are relative to AI_Employee_Vault/
- Only markdown files (.md) are counted in item totals
- Logs are organized by date (YYYY-MM-DD.log)
- Dashboard.md must always exist for system to function