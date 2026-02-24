"""
Audit Logger - Gold Tier Feature 10
Comprehensive JSON logging for all actions
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class AuditLogger:
    """
    Logs all actions to daily JSON files in /Logs/ directory.
    Each action is logged as a single JSON line for easy parsing.
    """

    def __init__(self, vault_path: Optional[str] = None):
        """Initialize audit logger"""
        if vault_path is None:
            vault_path = os.environ.get(
                'VAULT_PATH',
                str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault')
            )

        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / "Logs"

        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log_action(
        self,
        action_type: str,
        actor: str,
        target: str,
        result: str,
        parameters: Optional[Dict[str, Any]] = None,
        approval_status: Optional[str] = None,
        approved_by: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log an action to the daily JSON log file.

        Args:
            action_type: Type of action (email_send, linkedin_post, facebook_post, etc.)
            actor: Who performed the action (orchestrator, watcher, skill, human)
            target: Target of the action (email address, platform, file, etc.)
            result: Result of action (success, failure, dry_run)
            parameters: Optional parameters dict
            approval_status: Approval status (approved, auto, pending, rejected)
            approved_by: Who approved (human, system)
            error: Error message if result is failure
        """
        # Get today's log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"

        # Build log entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "result": result
        }

        # Add optional fields
        if parameters:
            entry["parameters"] = parameters

        if approval_status:
            entry["approval_status"] = approval_status

        if approved_by:
            entry["approved_by"] = approved_by

        if error:
            entry["error"] = error

        # Append to log file (one JSON object per line)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')

    def get_logs_for_date(self, date: str) -> list:
        """
        Get all log entries for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of log entry dicts
        """
        log_file = self.logs_dir / f"{date}.json"

        if not log_file.exists():
            return []

        entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

        return entries

    def get_logs_by_action_type(self, action_type: str, date: str) -> list:
        """
        Get all log entries of a specific type for a date.

        Args:
            action_type: Action type to filter by
            date: Date in YYYY-MM-DD format

        Returns:
            List of matching log entries
        """
        all_logs = self.get_logs_for_date(date)
        return [log for log in all_logs if log.get('action_type') == action_type]

    def get_logs_by_result(self, result: str, date: str) -> list:
        """
        Get all log entries with a specific result for a date.

        Args:
            result: Result to filter by (success, failure, dry_run)
            date: Date in YYYY-MM-DD format

        Returns:
            List of matching log entries
        """
        all_logs = self.get_logs_for_date(date)
        return [log for log in all_logs if log.get('result') == result]

    def count_actions_by_type(self, date: str) -> Dict[str, int]:
        """
        Count actions by type for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Dict mapping action_type to count
        """
        all_logs = self.get_logs_for_date(date)
        counts = {}

        for log in all_logs:
            action_type = log.get('action_type', 'unknown')
            counts[action_type] = counts.get(action_type, 0) + 1

        return counts


# Global logger instance
_global_logger = None


def get_logger(vault_path: Optional[str] = None) -> AuditLogger:
    """
    Get global audit logger instance (singleton pattern).

    Args:
        vault_path: Optional vault path (only used on first call)

    Returns:
        AuditLogger instance
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = AuditLogger(vault_path=vault_path)

    return _global_logger


def log_action(
    action_type: str,
    actor: str,
    target: str,
    result: str,
    **kwargs
) -> None:
    """
    Convenience function to log an action using global logger.

    Args:
        action_type: Type of action
        actor: Who performed the action
        target: Target of the action
        result: Result of action
        **kwargs: Additional optional parameters
    """
    logger = get_logger()
    logger.log_action(action_type, actor, target, result, **kwargs)


# Example usage patterns
def example_log_email():
    """Example: Log email send"""
    log_action(
        action_type="email_send",
        actor="orchestrator",
        target="client@example.com",
        parameters={"subject": "Invoice Follow-up", "body": "..."},
        approval_status="approved",
        approved_by="human",
        result="success"
    )


def example_log_social_post():
    """Example: Log social media post"""
    log_action(
        action_type="facebook_post",
        actor="orchestrator",
        target="facebook",
        parameters={"content": "Check out our new features!"},
        approval_status="approved",
        result="success"
    )


def example_log_error():
    """Example: Log error"""
    log_action(
        action_type="error",
        actor="gmail_watcher",
        target="gmail",
        result="failure",
        error="Connection timeout after 3 retries"
    )


def example_log_task_completion():
    """Example: Log task completion"""
    log_action(
        action_type="task_completed",
        actor="orchestrator",
        target="EMAIL_001.md",
        result="success"
    )
