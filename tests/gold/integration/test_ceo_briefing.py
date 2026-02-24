"""
Integration tests for CEO Briefing (Feature 8)
Tests Odoo integration, social media summaries, proactive suggestions
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()
    (vault / "Briefings").mkdir()
    (vault / "Pending_Approval").mkdir()
    (vault / "Logs").mkdir()
    (vault / "Database").mkdir()
    return vault


@pytest.fixture
def mock_odoo_data():
    """Mock Odoo financial data"""
    return {
        "invoices": [
            {"id": 1, "name": "INV/2026/0001", "partner_id": [42, "Acme Corp"], "amount_total": 5000.0, "state": "posted"},
            {"id": 2, "name": "INV/2026/0002", "partner_id": [43, "Tech Inc"], "amount_total": 3000.0, "state": "posted"}
        ],
        "overdue_invoices": [
            {"id": 3, "name": "INV/2026/0003", "partner_id": [44, "Late Client"], "amount_residual": 2000.0, "invoice_date_due": "2026-02-10"}
        ],
        "expenses": [
            {"id": 1, "name": "Office Supplies", "total_amount": 150.0, "product_id": [10, "Office Supplies"]},
            {"id": 2, "name": "Software License", "total_amount": 500.0, "product_id": [11, "Software"]}
        ],
        "account_balance": {"balance": 25000.0, "currency": "USD"}
    }


@pytest.fixture
def mock_social_logs(vault_path):
    """Create mock social media logs"""
    today = datetime.now()
    log_file = vault_path / "Logs" / f"{today.strftime('%Y-%m-%d')}.json"

    logs = [
        {"timestamp": today.isoformat(), "action_type": "linkedin_post", "result": "success"},
        {"timestamp": today.isoformat(), "action_type": "facebook_post", "result": "success"},
        {"timestamp": today.isoformat(), "action_type": "instagram_post", "result": "success"},
        {"timestamp": today.isoformat(), "action_type": "twitter_post", "result": "success"}
    ]

    with open(log_file, 'w') as f:
        for log in logs:
            f.write(json.dumps(log) + '\n')

    return log_file


class TestBriefingGeneration:
    """Test briefing generation"""

    def test_generate_briefing_with_odoo_data(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test that briefing is generated with Odoo data"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)

        assert briefing_file is not None
        briefing_path = vault_path / "Briefings" / briefing_file
        assert briefing_path.exists()

        content = briefing_path.read_text()
        assert "Monday Morning CEO Briefing" in content
        assert "Revenue" in content
        assert "Expenses" in content
        assert "Social Media Activity" in content

    def test_briefing_contains_revenue_data(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test briefing contains revenue information"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)
        content = (vault_path / "Briefings" / briefing_file).read_text()

        assert "Acme Corp" in content
        assert "5000" in content or "5,000" in content
        assert "Tech Inc" in content

    def test_briefing_contains_expense_data(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test briefing contains expense information"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)
        content = (vault_path / "Briefings" / briefing_file).read_text(encoding='utf-8')

        assert "Office Supplies" in content
        assert "Software" in content  # Category name from product_id
        assert "650" in content  # Total expenses

    def test_briefing_contains_social_media_summary(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test briefing contains social media activity"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)
        content = (vault_path / "Briefings" / briefing_file).read_text()

        assert "Social Media Activity" in content
        assert "LinkedIn" in content
        assert "Facebook" in content
        assert "Instagram" in content
        assert "Twitter" in content


class TestGracefulDegradation:
    """Test graceful degradation when Odoo unavailable"""

    def test_briefing_without_odoo_shows_warning(self, vault_path, mock_social_logs):
        """Test briefing shows warning when Odoo unavailable"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=None)  # Odoo unavailable

        content = (vault_path / "Briefings" / briefing_file).read_text(encoding='utf-8')
        assert "Odoo unavailable" in content or "data may be stale" in content

    def test_briefing_without_odoo_still_includes_social(self, vault_path, mock_social_logs):
        """Test briefing still includes social media when Odoo down"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=None)

        content = (vault_path / "Briefings" / briefing_file).read_text(encoding='utf-8')
        assert "Social Media Activity" in content


class TestProactiveSuggestions:
    """Test proactive suggestion generation"""

    def test_overdue_invoice_creates_approval_file(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test that overdue invoices create follow-up approval files"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)

        # Check for approval file
        approval_files = list((vault_path / "Pending_Approval").glob("EMAIL_followup_*.md"))
        assert len(approval_files) > 0

        # Check approval file content
        approval_content = approval_files[0].read_text()
        assert "Late Client" in approval_content
        assert "2000" in approval_content or "2,000" in approval_content

    def test_briefing_lists_proactive_suggestions(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test briefing lists proactive suggestions"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)
        content = (vault_path / "Briefings" / briefing_file).read_text()

        assert "Proactive Suggestions" in content
        assert "Follow up" in content or "overdue" in content


class TestBriefingFormat:
    """Test briefing markdown formatting"""

    def test_briefing_has_correct_structure(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test briefing has all required sections"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)
        content = (vault_path / "Briefings" / briefing_file).read_text()

        required_sections = [
            "Executive Summary",
            "Revenue",
            "Expenses",
            "Cash Position",
            "Social Media Activity",
            "Proactive Suggestions"
        ]

        for section in required_sections:
            assert section in content

    def test_briefing_filename_format(self, vault_path, mock_odoo_data, mock_social_logs):
        """Test briefing filename follows correct format"""
        from src.briefing.ceo_briefing import CEOBriefing

        briefing = CEOBriefing(vault_path=str(vault_path))
        briefing_file = briefing.generate(odoo_data=mock_odoo_data)

        # Should be YYYY-MM-DD_Monday_Briefing.md
        assert "_Monday_Briefing.md" in briefing_file or "_Briefing.md" in briefing_file
        assert briefing_file.startswith("2026-")
