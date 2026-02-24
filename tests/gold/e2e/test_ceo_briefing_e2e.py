"""
E2E test for CEO briefing workflow
Tests: Scheduled trigger → Data collection → Briefing generation → Approval suggestions
"""
import pytest
from pathlib import Path
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
    (vault / "Done").mkdir()
    (vault / "Logs").mkdir()
    (vault / "Briefings").mkdir()
    (vault / "Database").mkdir()
    (vault / ".claude" / "skills" / "ceo-briefing").mkdir(parents=True)

    # Create skill file
    skill_content = """# CEO Briefing Skill
Generate Monday morning executive briefings."""
    (vault / ".claude" / "skills" / "ceo-briefing" / "SKILL.md").write_text(skill_content)

    # Create sample log files
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = vault / "Logs" / f"{today}.json"

    sample_logs = [
        {"timestamp": "2026-02-24T09:00:00Z", "action_type": "email_send", "actor": "orchestrator", "target": "client@example.com", "result": "success"},
        {"timestamp": "2026-02-24T10:00:00Z", "action_type": "facebook_post", "actor": "orchestrator", "target": "facebook", "result": "success"},
        {"timestamp": "2026-02-24T10:30:00Z", "action_type": "linkedin_post", "actor": "orchestrator", "target": "linkedin", "result": "success"},
        {"timestamp": "2026-02-24T11:00:00Z", "action_type": "task_completed", "actor": "orchestrator", "target": "EMAIL_001.md", "result": "success"},
    ]

    with open(log_file, 'w', encoding='utf-8') as f:
        for log in sample_logs:
            f.write(json.dumps(log) + '\n')

    return vault


class TestCEOBriefingFlowE2E:
    """Test complete CEO briefing workflow end-to-end"""

    def test_monday_briefing_generation(self, vault_path, monkeypatch):
        """Test complete Monday briefing generation"""
        from src.briefing.ceo_briefing import CEOBriefing

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Generate briefing
        briefing = CEOBriefing(vault_path=str(vault_path))

        # Mock Odoo data
        def mock_get_revenue():
            return 45000.0

        def mock_get_expenses():
            return 12000.0

        def mock_get_balance():
            return 33000.0

        briefing._get_revenue_from_odoo = mock_get_revenue
        briefing._get_expenses_from_odoo = mock_get_expenses
        briefing._get_balance_from_odoo = mock_get_balance

        # Generate briefing
        briefing_filename = briefing.generate()

        # Verify briefing file created
        assert briefing_filename is not None
        briefing_file = vault_path / "Briefings" / briefing_filename
        assert briefing_file.exists()

        # Read content
        briefing_content = briefing_file.read_text(encoding='utf-8')

        # Should contain key sections
        assert "# Monday Morning CEO Briefing" in briefing_content
        assert "## Executive Summary" in briefing_content
        assert "## Revenue" in briefing_content
        assert "## Expenses" in briefing_content
        assert "## Task Completion" in briefing_content or "## Tasks" in briefing_content
        assert "## Social Media Activity" in briefing_content or "## Social" in briefing_content

        # Should contain data
        assert "$45,000" in briefing_content or "45000" in briefing_content or "45,000" in briefing_content
        assert "$12,000" in content or "12000" in content

    def test_briefing_with_odoo_unavailable(self, vault_path, monkeypatch):
        """Test briefing generation when Odoo is down"""
        from src.briefing.ceo_briefing import CEOBriefing

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        briefing = CEOBriefing(vault_path=str(vault_path))

        # Mock Odoo failure
        def mock_odoo_failure():
            return None

        briefing._get_revenue_from_odoo = mock_odoo_failure
        briefing._get_expenses_from_odoo = mock_odoo_failure
        briefing._get_balance_from_odoo = mock_odoo_failure

        # Generate briefing
        briefing_filename = briefing.generate()

        # Verify briefing still created
        assert briefing_filename is not None
        briefing_file = vault_path / "Briefings" / briefing_filename
        assert briefing_file.exists()

        # Read content
        briefing_content = briefing_file.read_text(encoding='utf-8')

        # Verify warning message
        assert "WARNING" in briefing_content or "unavailable" in briefing_content.lower()

    def test_briefing_with_proactive_suggestions(self, vault_path, monkeypatch):
        """Test briefing generates proactive suggestions with approval files"""
        from src.briefing.ceo_briefing import CEOBriefing

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create overdue invoice scenario
        briefing = CEOBriefing(vault_path=str(vault_path))

        def mock_get_overdue():
            return [
                {"partner_name": "ABC Corp", "amount": 5000.0, "days_overdue": 15},
                {"partner_name": "XYZ Inc", "amount": 3000.0, "days_overdue": 30}
            ]

        briefing._get_overdue_invoices = mock_get_overdue

        # Generate briefing
        briefing_filename = briefing.generate()

        # Verify briefing mentions overdue invoices
        assert briefing_filename is not None
        briefing_file = vault_path / "Briefings" / briefing_filename
        assert briefing_file.exists()

        briefing_content = briefing_file.read_text(encoding='utf-8')
        assert "overdue" in briefing_content.lower() or "outstanding" in briefing_content.lower()

    def test_briefing_social_media_summary(self, vault_path, monkeypatch):
        """Test briefing includes social media activity summary"""
        from src.briefing.ceo_briefing import CEOBriefing

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Add more social media logs
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        additional_logs = [
            {"timestamp": "2026-02-24T12:00:00Z", "action_type": "twitter_post", "actor": "orchestrator", "target": "twitter", "result": "success"},
            {"timestamp": "2026-02-24T13:00:00Z", "action_type": "instagram_post", "actor": "orchestrator", "target": "instagram", "result": "success"},
        ]

        with open(log_file, 'a', encoding='utf-8') as f:
            for log in additional_logs:
                f.write(json.dumps(log) + '\n')

        # Generate briefing
        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_filename = briefing.generate()

        # Verify social media section
        assert briefing_filename is not None
        briefing_file = vault_path / "Briefings" / briefing_filename
        assert briefing_file.exists()

        briefing_content = briefing_file.read_text(encoding='utf-8')
        assert "Social Media" in briefing_content or "Social" in briefing_content

        # Should mention platforms
        platforms_mentioned = sum([
            "facebook" in briefing_content.lower(),
            "twitter" in briefing_content.lower(),
            "instagram" in briefing_content.lower(),
            "linkedin" in briefing_content.lower()
        ])

        assert platforms_mentioned >= 2  # At least 2 platforms mentioned

    def test_briefing_task_completion_stats(self, vault_path, monkeypatch):
        """Test briefing includes task completion statistics"""
        from src.briefing.ceo_briefing import CEOBriefing

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Add task completion logs
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"

        task_logs = [
            {"timestamp": "2026-02-24T14:00:00Z", "action_type": "task_completed", "actor": "orchestrator", "target": "EMAIL_002.md", "result": "success"},
            {"timestamp": "2026-02-24T15:00:00Z", "action_type": "task_completed", "actor": "orchestrator", "target": "SOCIAL_FB_001.md", "result": "success"},
            {"timestamp": "2026-02-24T16:00:00Z", "action_type": "task_completed", "actor": "orchestrator", "target": "ODOO_INV_001.md", "result": "success"},
        ]

        with open(log_file, 'a', encoding='utf-8') as f:
            for log in task_logs:
                f.write(json.dumps(log) + '\n')

        # Generate briefing
        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_filename = briefing.generate()

        # Verify task stats
        assert briefing_filename is not None
        briefing_file = vault_path / "Briefings" / briefing_filename
        assert briefing_file.exists()

        briefing_content = briefing_file.read_text(encoding='utf-8')
        assert "Task Completion" in briefing_content or "Tasks" in briefing_content

        # Should show some count
        assert any(str(i) in briefing_content for i in range(1, 10))

    def test_briefing_scheduled_trigger(self, vault_path, monkeypatch):
        """Test briefing can be triggered via orchestrator"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create briefing task
        task_content = """---
type: ceo_briefing
scheduled: true
day: monday
time: 07:00
---

Generate Monday morning CEO briefing
"""
        task_file = vault_path / "Needs_Action" / "BRIEFING_MONDAY.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Simulate Claude generating briefing
            from src.briefing.ceo_briefing import CEOBriefing
            briefing = CEOBriefing(vault_path=str(vault_path))

            # Mock Odoo
            briefing_content = briefing.generate(odoo_data={
                "revenue": 50000.0,
                "expenses": 15000.0,
                "balance": 35000.0
            })

            # Save briefing to file
            today = datetime.now().strftime("%Y-%m-%d")
            briefing_file = vault_path / "Briefings" / f"{today}_Monday_Briefing.md"
            briefing_file.write_text(briefing_content, encoding='utf-8')

            # Move task to Done
            done_file = vault_path / "Done" / task_filename
            task_path = vault_path / "In_Progress" / task_filename
            if task_path.exists():
                import shutil
                shutil.move(str(task_path), str(done_file))

            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify briefing generated
        briefing_files = list((vault_path / "Briefings").glob("*.md"))
        assert len(briefing_files) >= 1

        # Verify task completed
        assert (vault_path / "Done" / "BRIEFING_MONDAY.md").exists()
