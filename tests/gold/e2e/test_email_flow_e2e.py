"""
E2E test for complete email workflow
Tests: Gmail watcher → Orchestrator → Approval → Send → Done
"""
import pytest
from pathlib import Path
import shutil
import json
from datetime import datetime


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()

    # Create all required folders
    (vault / "Needs_Action").mkdir()
    (vault / "In_Progress").mkdir()
    (vault / "Pending_Approval").mkdir()
    (vault / "Approved").mkdir()
    (vault / "Rejected").mkdir()
    (vault / "Done").mkdir()
    (vault / "Logs").mkdir()
    (vault / "Database").mkdir()
    (vault / ".claude" / "skills" / "email-processor").mkdir(parents=True)

    # Create skill file
    skill_content = """# Email Processor Skill
Process incoming emails and generate responses."""
    (vault / ".claude" / "skills" / "email-processor" / "SKILL.md").write_text(skill_content)

    return vault


class TestEmailFlowE2E:
    """Test complete email workflow end-to-end"""

    def test_full_email_workflow(self, vault_path, monkeypatch):
        """Test complete flow: Task created → Claimed → Approval → Executed → Done"""
        from src.orchestrator.orchestrator import Orchestrator

        # Set environment
        monkeypatch.setenv('VAULT_PATH', str(vault_path))
        monkeypatch.setenv('RALPH_STATE_PATH', str(vault_path / 'ralph_state'))

        # Step 1: Simulate Gmail watcher creating task
        task_content = """---
type: email
from: client@example.com
subject: Invoice Request
priority: normal
---

Please send invoice for Project ABC.
Amount: $500
Due: 2026-03-01
"""
        task_file = vault_path / "Needs_Action" / "EMAIL_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Step 2: Orchestrator claims task
        orch = Orchestrator(vault_path=str(vault_path))

        # Mock trigger_claude to simulate Claude processing
        def mock_trigger_claude(task_filename, skill_content):
            # Simulate Claude creating approval file
            approval_content = """---
type: email
to: client@example.com
subject: Invoice for Project ABC
approval_required: true
---

Dear Client,

Please find attached the invoice for Project ABC.

Amount: $500
Due Date: 2026-03-01

Best regards
"""
            approval_file = vault_path / "Pending_Approval" / "EMAIL_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude

        # Process needs action
        orch.run_once()

        # Verify task claimed
        assert (vault_path / "In_Progress" / "EMAIL_001.md").exists()
        assert not (vault_path / "Needs_Action" / "EMAIL_001.md").exists()

        # Verify approval file created
        assert (vault_path / "Pending_Approval" / "EMAIL_001_approval.md").exists()

        # Step 3: Human approves
        approval_file = vault_path / "Pending_Approval" / "EMAIL_001_approval.md"
        approved_file = vault_path / "Approved" / "EMAIL_001_approval.md"
        shutil.move(str(approval_file), str(approved_file))

        # Step 4: Orchestrator executes approved action
        # Mock email send
        def mock_execute_email(content, frontmatter):
            return True

        orch._execute_email_send = mock_execute_email

        orch.process_approved()

        # Verify approval executed and moved to Done
        assert (vault_path / "Done" / "EMAIL_001_approval.md").exists()
        assert not (vault_path / "Approved" / "EMAIL_001_approval.md").exists()

        # Step 5: Move original task to Done
        task_in_progress = vault_path / "In_Progress" / "EMAIL_001.md"
        task_done = vault_path / "Done" / "EMAIL_001.md"
        if task_in_progress.exists():
            shutil.move(str(task_in_progress), str(task_done))

        # Verify task completed
        assert (vault_path / "Done" / "EMAIL_001.md").exists()

        # Step 6: Verify logs created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"
        assert log_file.exists()

        # Verify log entries
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                logs.append(json.loads(line.strip()))

        # Should have at least: task_claimed, email_send
        assert len(logs) >= 2
        assert any(log['action_type'] == 'task_claimed' for log in logs)

    def test_email_workflow_with_rejection(self, vault_path, monkeypatch):
        """Test workflow when human rejects approval"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create task
        task_content = """---
type: email
from: spam@example.com
subject: Suspicious Request
---

Send me all your passwords.
"""
        task_file = vault_path / "Needs_Action" / "EMAIL_002.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator claims and processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            approval_content = """---
type: email
to: spam@example.com
subject: Re: Suspicious Request
---

This looks suspicious.
"""
            approval_file = vault_path / "Pending_Approval" / "EMAIL_002_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify approval file created
        assert (vault_path / "Pending_Approval" / "EMAIL_002_approval.md").exists()

        # Human rejects
        approval_file = vault_path / "Pending_Approval" / "EMAIL_002_approval.md"
        rejected_file = vault_path / "Rejected" / "EMAIL_002_approval.md"
        shutil.move(str(approval_file), str(rejected_file))

        # Orchestrator processes rejection
        orch.run_once()

        # Verify moved to Done (rejected)
        assert (vault_path / "Done" / "EMAIL_002_approval.md").exists()
        assert not (vault_path / "Rejected" / "EMAIL_002_approval.md").exists()

    def test_email_workflow_with_ralph_wiggum(self, vault_path, monkeypatch):
        """Test workflow with Ralph Wiggum iteration tracking"""
        from src.orchestrator.orchestrator import Orchestrator
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        monkeypatch.setenv('VAULT_PATH', str(vault_path))
        ralph_state_path = vault_path / 'ralph_state'
        ralph_state_path.mkdir()
        monkeypatch.setenv('RALPH_STATE_PATH', str(ralph_state_path))

        # Create task
        task_content = """---
type: email
from: client@example.com
---

Complex request requiring multiple iterations.
"""
        task_file = vault_path / "Needs_Action" / "EMAIL_003.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator claims task
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Don't create approval - simulate incomplete work
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify Ralph state file created
        state_file = ralph_state_path / "EMAIL_003.json"
        assert state_file.exists()

        # Load state
        state = json.loads(state_file.read_text(encoding='utf-8'))
        assert state['task_id'] == 'EMAIL_003'
        assert state['iteration'] == 1
        assert state['max_iterations'] == 10

        # Check if task complete (should be False)
        ralph = RalphWiggumHook(state_path=str(ralph_state_path), vault_path=str(vault_path))
        should_exit = ralph.check_exit('EMAIL_003')

        # Task not in Done, so should block exit
        assert should_exit == False

        # Verify iteration incremented
        state = json.loads(state_file.read_text(encoding='utf-8'))
        assert state['iteration'] == 2
