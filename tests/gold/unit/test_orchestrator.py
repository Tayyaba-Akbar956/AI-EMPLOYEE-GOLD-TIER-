"""
Unit tests for the Orchestrator (Feature 1)
Tests claim-by-move, task detection, lifecycle management
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import shutil


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault structure for testing"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()

    # Create required folders
    (vault / "Needs_Action").mkdir()
    (vault / "In_Progress").mkdir()
    (vault / "Done").mkdir()
    (vault / "Approved").mkdir()
    (vault / "Rejected").mkdir()
    (vault / "Logs").mkdir()
    (vault / "Pending_Approval").mkdir()

    # Create Dashboard.md
    (vault / "Dashboard.md").write_text("# Dashboard\n")

    return vault


@pytest.fixture
def mock_db(tmp_path):
    """Create a mock database"""
    db_path = tmp_path / "test.db"
    return db_path


class TestTaskClaiming:
    """Test claim-by-move functionality"""

    def test_claim_task_moves_file_to_in_progress(self, vault_path):
        """Test that claiming a task moves it from Needs_Action to In_Progress"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create a task file
        task_file = vault_path / "Needs_Action" / "EMAIL_test.md"
        task_file.write_text("---\ntype: email\n---\nTest email content")

        orch = Orchestrator(vault_path=str(vault_path))
        claimed = orch.claim_task("EMAIL_test.md")

        assert claimed is True
        assert not task_file.exists()
        assert (vault_path / "In_Progress" / "EMAIL_test.md").exists()

    def test_claim_nonexistent_task_returns_false(self, vault_path):
        """Test that claiming a nonexistent task returns False"""
        from src.orchestrator.orchestrator import Orchestrator

        orch = Orchestrator(vault_path=str(vault_path))
        claimed = orch.claim_task("NONEXISTENT.md")

        assert claimed is False

    def test_claim_task_atomic_operation(self, vault_path):
        """Test that claim is atomic - no partial moves"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "Needs_Action" / "TASK_001.md"
        task_file.write_text("---\ntype: email\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))

        # Simulate failure during move
        with patch('shutil.move', side_effect=Exception("Move failed")):
            with pytest.raises(Exception):
                orch.claim_task("TASK_001.md")

        # Original file should still exist
        assert task_file.exists()
        assert not (vault_path / "In_Progress" / "TASK_001.md").exists()


class TestTaskDetection:
    """Test task type detection from frontmatter"""

    def test_detect_email_task_type(self, vault_path):
        """Test detection of email task type"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "In_Progress" / "EMAIL_001.md"
        task_file.write_text("---\ntype: email\nfrom: test@example.com\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))
        task_type = orch.detect_task_type("EMAIL_001.md")

        assert task_type == "email"

    def test_detect_linkedin_task_type(self, vault_path):
        """Test detection of LinkedIn task type"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "In_Progress" / "LINKEDIN_001.md"
        task_file.write_text("---\ntype: linkedin\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))
        task_type = orch.detect_task_type("LINKEDIN_001.md")

        assert task_type == "linkedin"

    def test_detect_whatsapp_task_type(self, vault_path):
        """Test detection of WhatsApp task type"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "In_Progress" / "WHATSAPP_001.md"
        task_file.write_text("---\ntype: whatsapp\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))
        task_type = orch.detect_task_type("WHATSAPP_001.md")

        assert task_type == "whatsapp"

    def test_detect_file_task_type(self, vault_path):
        """Test detection of file task type"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "In_Progress" / "FILE_001.md"
        task_file.write_text("---\ntype: file\ncategory: invoice\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))
        task_type = orch.detect_task_type("FILE_001.md")

        assert task_type == "file"

    def test_detect_task_type_missing_frontmatter(self, vault_path):
        """Test that missing frontmatter returns None"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "In_Progress" / "INVALID.md"
        task_file.write_text("No frontmatter here")

        orch = Orchestrator(vault_path=str(vault_path))
        task_type = orch.detect_task_type("INVALID.md")

        assert task_type is None

    def test_detect_task_type_invalid_yaml(self, vault_path):
        """Test that invalid YAML returns None"""
        from src.orchestrator.orchestrator import Orchestrator

        task_file = vault_path / "In_Progress" / "INVALID.md"
        task_file.write_text("---\ntype: email\ninvalid yaml: [unclosed\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))
        task_type = orch.detect_task_type("INVALID.md")

        assert task_type is None


class TestSkillLoading:
    """Test loading matching SKILL.md files"""

    def test_load_skill_for_email_task(self, vault_path):
        """Test loading email-processor skill"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create skill file
        skill_dir = vault_path / ".claude" / "skills" / "email-processor"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Email Processor Skill\nProcesses emails")

        orch = Orchestrator(vault_path=str(vault_path))
        skill_content = orch.load_skill("email")

        assert skill_content is not None
        assert "Email Processor Skill" in skill_content

    def test_load_skill_for_linkedin_task(self, vault_path):
        """Test loading linkedin-processor skill"""
        from src.orchestrator.orchestrator import Orchestrator

        skill_dir = vault_path / ".claude" / "skills" / "Linkedin-processor"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# LinkedIn Processor Skill")

        orch = Orchestrator(vault_path=str(vault_path))
        skill_content = orch.load_skill("linkedin")

        assert skill_content is not None
        assert "LinkedIn Processor Skill" in skill_content

    def test_load_skill_nonexistent_returns_none(self, vault_path):
        """Test that loading nonexistent skill returns None"""
        from src.orchestrator.orchestrator import Orchestrator

        orch = Orchestrator(vault_path=str(vault_path))
        skill_content = orch.load_skill("nonexistent")

        assert skill_content is None


class TestApprovalWatching:
    """Test watching Approved and Rejected folders"""

    def test_process_approved_task(self, vault_path):
        """Test processing an approved task"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create approved file
        approved_file = vault_path / "Approved" / "APPROVAL_001.md"
        approved_file.write_text("---\ntype: email\napproval_id: 001\n---\nApproved content")

        orch = Orchestrator(vault_path=str(vault_path))
        with patch.object(orch, 'execute_approved_action') as mock_execute:
            orch.process_approved()
            mock_execute.assert_called_once()

    def test_process_rejected_task(self, vault_path):
        """Test processing a rejected task"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create rejected file
        rejected_file = vault_path / "Rejected" / "APPROVAL_001.md"
        rejected_file.write_text("---\ntype: email\napproval_id: 001\nreason: Not needed\n---\nRejected content")

        orch = Orchestrator(vault_path=str(vault_path))
        orch.process_rejected()

        # Should be moved to Done
        assert not rejected_file.exists()
        assert (vault_path / "Done" / "APPROVAL_001.md").exists()

    def test_process_approved_moves_to_done_after_execution(self, vault_path):
        """Test that approved tasks move to Done after execution"""
        from src.orchestrator.orchestrator import Orchestrator

        approved_file = vault_path / "Approved" / "APPROVAL_002.md"
        approved_file.write_text("---\ntype: email\n---\nContent")

        orch = Orchestrator(vault_path=str(vault_path))
        with patch.object(orch, 'execute_approved_action', return_value=True):
            orch.process_approved()

        assert not approved_file.exists()
        assert (vault_path / "Done" / "APPROVAL_002.md").exists()


class TestLogging:
    """Test logging to both SQLite and JSON"""

    def test_log_action_to_json(self, vault_path):
        """Test that actions are logged to JSON file"""
        from src.orchestrator.orchestrator import Orchestrator

        orch = Orchestrator(vault_path=str(vault_path))
        orch.log_action(
            action_type="task_claimed",
            actor="orchestrator",
            target="EMAIL_001.md",
            result="success"
        )

        # Check JSON log file exists
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"
        assert log_file.exists()

        # Check log content
        with open(log_file, 'r') as f:
            logs = [json.loads(line) for line in f]

        assert len(logs) == 1
        assert logs[0]["action_type"] == "task_claimed"
        assert logs[0]["actor"] == "orchestrator"
        assert logs[0]["target"] == "EMAIL_001.md"
        assert logs[0]["result"] == "success"

    def test_log_action_appends_to_existing_file(self, vault_path):
        """Test that logging appends to existing JSON file"""
        from src.orchestrator.orchestrator import Orchestrator

        orch = Orchestrator(vault_path=str(vault_path))
        orch.log_action(action_type="action1", actor="orch", target="task1", result="success")
        orch.log_action(action_type="action2", actor="orch", target="task2", result="success")

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        with open(log_file, 'r') as f:
            logs = [json.loads(line) for line in f]

        assert len(logs) == 2

    @patch('src.orchestrator.orchestrator.DatabaseManager')
    def test_log_action_to_sqlite(self, mock_db_class, vault_path):
        """Test that actions are logged to SQLite"""
        from src.orchestrator.orchestrator import Orchestrator

        mock_db = Mock()
        mock_db_class.return_value = mock_db

        orch = Orchestrator(vault_path=str(vault_path))
        orch.log_action(
            action_type="task_completed",
            actor="orchestrator",
            target="EMAIL_001.md",
            result="success"
        )

        # Verify database log was called
        mock_db.log_activity.assert_called_once()


class TestDashboardUpdate:
    """Test Dashboard.md updates"""

    def test_update_dashboard_after_cycle(self, vault_path):
        """Test that dashboard is updated after each cycle"""
        from src.orchestrator.orchestrator import Orchestrator

        orch = Orchestrator(vault_path=str(vault_path))
        orch.update_dashboard()

        dashboard = vault_path / "Dashboard.md"
        content = dashboard.read_text()

        assert "Last Updated:" in content
        assert "Tasks in Progress:" in content
        assert "Tasks Completed:" in content

    def test_dashboard_shows_task_counts(self, vault_path):
        """Test that dashboard shows correct task counts"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create some tasks
        (vault_path / "Needs_Action" / "TASK_001.md").write_text("---\ntype: email\n---\n")
        (vault_path / "Needs_Action" / "TASK_002.md").write_text("---\ntype: email\n---\n")
        (vault_path / "In_Progress" / "TASK_003.md").write_text("---\ntype: email\n---\n")
        (vault_path / "Done" / "TASK_004.md").write_text("---\ntype: email\n---\n")

        orch = Orchestrator(vault_path=str(vault_path))
        orch.update_dashboard()

        dashboard = vault_path / "Dashboard.md"
        content = dashboard.read_text()

        assert "Needs Action: 2" in content
        assert "Tasks in Progress: 1" in content


class TestStaleTaskRecovery:
    """Test recovery of stale In_Progress tasks"""

    def test_recover_stale_tasks_on_startup(self, vault_path):
        """Test that stale tasks are recovered on startup"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create a stale task (modified > 1 hour ago)
        stale_task = vault_path / "In_Progress" / "STALE_001.md"
        stale_task.write_text("---\ntype: email\n---\nStale content")

        # Set modification time to 2 hours ago
        two_hours_ago = datetime.now().timestamp() - 7200
        import os
        os.utime(stale_task, (two_hours_ago, two_hours_ago))

        orch = Orchestrator(vault_path=str(vault_path))
        orch.recover_stale_tasks()

        # Should be moved back to Needs_Action
        assert not stale_task.exists()
        assert (vault_path / "Needs_Action" / "STALE_001.md").exists()

    def test_dont_recover_recent_tasks(self, vault_path):
        """Test that recent tasks are not recovered"""
        from src.orchestrator.orchestrator import Orchestrator

        recent_task = vault_path / "In_Progress" / "RECENT_001.md"
        recent_task.write_text("---\ntype: email\n---\nRecent content")

        orch = Orchestrator(vault_path=str(vault_path))
        orch.recover_stale_tasks()

        # Should still be in In_Progress
        assert recent_task.exists()
        assert not (vault_path / "Needs_Action" / "RECENT_001.md").exists()


class TestOrchestratorLifecycle:
    """Test complete orchestrator lifecycle"""

    def test_run_once_processes_single_cycle(self, vault_path):
        """Test that run_once processes one complete cycle"""
        from src.orchestrator.orchestrator import Orchestrator

        # Create a task
        task_file = vault_path / "Needs_Action" / "EMAIL_001.md"
        task_file.write_text("---\ntype: email\n---\nTest")

        # Create skill file so load_skill returns content
        skill_dir = vault_path / ".claude" / "skills" / "email-processor"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Email Processor Skill")

        orch = Orchestrator(vault_path=str(vault_path))
        with patch.object(orch, 'trigger_claude') as mock_trigger:
            orch.run_once()
            mock_trigger.assert_called_once()

        # Task should be claimed
        assert not task_file.exists()
        assert (vault_path / "In_Progress" / "EMAIL_001.md").exists()

    def test_orchestrator_initialization(self, vault_path):
        """Test orchestrator initializes correctly"""
        from src.orchestrator.orchestrator import Orchestrator

        orch = Orchestrator(vault_path=str(vault_path))

        assert orch.vault_path == Path(vault_path)
        assert orch.needs_action_path == vault_path / "Needs_Action"
        assert orch.in_progress_path == vault_path / "In_Progress"
        assert orch.done_path == vault_path / "Done"
        assert orch.approved_path == vault_path / "Approved"
        assert orch.rejected_path == vault_path / "Rejected"
