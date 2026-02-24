"""
Unit tests for JSON Audit Logging (Feature 10)
Tests comprehensive action logging to JSON files
"""
import pytest
from pathlib import Path
from datetime import datetime
import json


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()
    (vault / "Logs").mkdir()
    return vault


class TestAuditLogger:
    """Test audit logger initialization and basic logging"""

    def test_logger_initialization(self, vault_path):
        """Test that audit logger initializes correctly"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        assert logger.vault_path == vault_path
        assert (vault_path / "Logs").exists()

    def test_log_action_creates_file(self, vault_path):
        """Test that logging creates JSON file"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="email_send",
            actor="orchestrator",
            target="client@example.com",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"
        assert log_file.exists()

    def test_log_entry_format(self, vault_path):
        """Test that log entries have correct format"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="linkedin_post",
            actor="orchestrator",
            target="linkedin",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            line = f.readline()
            entry = json.loads(line)

        assert "timestamp" in entry
        assert entry["action_type"] == "linkedin_post"
        assert entry["actor"] == "orchestrator"
        assert entry["target"] == "linkedin"
        assert entry["result"] == "success"


class TestActionTypes:
    """Test different action types"""

    def test_log_email_send(self, vault_path):
        """Test logging email send action"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="email_send",
            actor="orchestrator",
            target="client@example.com",
            parameters={"subject": "Test", "body": "Hello"},
            approval_status="approved",
            approved_by="human",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["action_type"] == "email_send"
        assert entry["approval_status"] == "approved"
        assert entry["approved_by"] == "human"

    def test_log_social_post(self, vault_path):
        """Test logging social media post"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="facebook_post",
            actor="orchestrator",
            target="facebook",
            parameters={"content": "Test post"},
            approval_status="approved",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["action_type"] == "facebook_post"
        assert entry["target"] == "facebook"

    def test_log_odoo_action(self, vault_path):
        """Test logging Odoo action"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="odoo_invoice",
            actor="orchestrator",
            target="odoo",
            parameters={"invoice_id": 123, "amount": 5000.0},
            approval_status="approved",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["action_type"] == "odoo_invoice"
        assert "invoice_id" in entry["parameters"]

    def test_log_task_completion(self, vault_path):
        """Test logging task completion"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="task_completed",
            actor="orchestrator",
            target="EMAIL_001.md",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["action_type"] == "task_completed"

    def test_log_error(self, vault_path):
        """Test logging error action"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="error",
            actor="gmail_watcher",
            target="gmail",
            result="failure",
            error="Connection timeout"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["action_type"] == "error"
        assert entry["result"] == "failure"
        assert entry["error"] == "Connection timeout"


class TestApprovalTracking:
    """Test approval workflow tracking"""

    def test_log_approval_created(self, vault_path):
        """Test logging approval file creation"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="approval_created",
            actor="orchestrator",
            target="EMAIL_followup_20260224.md",
            approval_status="pending",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["approval_status"] == "pending"

    def test_log_approval_decision(self, vault_path):
        """Test logging approval decision"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="approval_decision",
            actor="human",
            target="EMAIL_followup_20260224.md",
            approval_status="approved",
            approved_by="human",
            result="success"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["approval_status"] == "approved"
        assert entry["approved_by"] == "human"


class TestMultipleEntries:
    """Test multiple log entries"""

    def test_multiple_entries_same_day(self, vault_path):
        """Test that multiple entries append to same file"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))

        logger.log_action(action_type="action1", actor="actor1", target="target1", result="success")
        logger.log_action(action_type="action2", actor="actor2", target="target2", result="success")
        logger.log_action(action_type="action3", actor="actor3", target="target3", result="success")

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 3

        entries = [json.loads(line) for line in lines]
        assert entries[0]["action_type"] == "action1"
        assert entries[1]["action_type"] == "action2"
        assert entries[2]["action_type"] == "action3"


class TestLogRetention:
    """Test log retention and cleanup"""

    def test_old_logs_not_deleted(self, vault_path):
        """Test that old logs are retained (90 day minimum)"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))

        # Create old log file
        old_date = "2026-01-01"
        old_log = vault_path / "Logs" / f"{old_date}.json"
        old_log.write_text('{"test": "old log"}\n')

        # Log new action
        logger.log_action(action_type="test", actor="test", target="test", result="success")

        # Old log should still exist
        assert old_log.exists()


class TestDryRunMode:
    """Test dry run mode"""

    def test_dry_run_logs_with_flag(self, vault_path):
        """Test that dry run actions are logged with dry_run result"""
        from src.utils.audit_logger import AuditLogger

        logger = AuditLogger(vault_path=str(vault_path))
        logger.log_action(
            action_type="email_send",
            actor="orchestrator",
            target="test@example.com",
            result="dry_run"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["result"] == "dry_run"
