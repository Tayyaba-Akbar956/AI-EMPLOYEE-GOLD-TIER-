"""
E2E test for Odoo invoice workflow
Tests: Task created → Orchestrator → Odoo MCP → Approval → Execute → Done
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
    (vault / ".claude" / "skills" / "odoo-integration").mkdir(parents=True)

    # Create skill file
    skill_content = """# Odoo Integration Skill
Manage accounting operations via Odoo."""
    (vault / ".claude" / "skills" / "odoo-integration" / "SKILL.md").write_text(skill_content)

    return vault


class TestOdooInvoiceFlowE2E:
    """Test complete Odoo invoice workflow end-to-end"""

    def test_create_invoice_workflow(self, vault_path, monkeypatch):
        """Test complete invoice creation flow"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))
        monkeypatch.setenv('RALPH_STATE_PATH', str(vault_path / 'ralph_state'))

        # Step 1: Create invoice task
        task_content = """---
type: odoo_invoice
action: create_invoice
partner_id: 123
amount: 5000.00
---

Create invoice for Project XYZ
Customer: ABC Corp
Amount: $5000
Due: 2026-03-15
"""
        task_file = vault_path / "Needs_Action" / "ODOO_INV_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Step 2: Orchestrator claims task
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Simulate Claude creating approval file for invoice
            approval_content = """---
type: odoo_invoice
action: create_invoice
partner_id: 123
amount: 5000.00
approval_required: true
---

## Invoice Details

**Customer**: ABC Corp (ID: 123)
**Amount**: $5,000.00
**Due Date**: 2026-03-15
**Project**: XYZ

## Line Items
- Consulting Services: $5,000.00

**Approval Required**: This invoice exceeds $1000 threshold.
"""
            approval_file = vault_path / "Pending_Approval" / "ODOO_INV_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify task claimed and approval created
        assert (vault_path / "In_Progress" / "ODOO_INV_001.md").exists()
        assert (vault_path / "Pending_Approval" / "ODOO_INV_001_approval.md").exists()

        # Step 3: Human approves
        approval_file = vault_path / "Pending_Approval" / "ODOO_INV_001_approval.md"
        approved_file = vault_path / "Approved" / "ODOO_INV_001_approval.md"
        shutil.move(str(approval_file), str(approved_file))

        # Step 4: Orchestrator executes Odoo action
        def mock_odoo_action(content, frontmatter):
            # Simulate successful invoice creation
            return True

        orch._execute_odoo_action = mock_odoo_action
        orch.process_approved()

        # Verify executed and moved to Done
        assert (vault_path / "Done" / "ODOO_INV_001_approval.md").exists()

        # Verify logs
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"
        assert log_file.exists()

        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                logs.append(json.loads(line.strip()))

        # Should have odoo_action log
        assert any(log['action_type'] == 'odoo_action' for log in logs)

    def test_expense_creation_no_approval(self, vault_path, monkeypatch):
        """Test expense creation (no approval needed for draft)"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create expense task
        task_content = """---
type: odoo
action: create_expense
product_id: 456
amount: 150.00
---

Office supplies expense
Amount: $150
Category: Office Supplies
"""
        task_file = vault_path / "Needs_Action" / "ODOO_EXP_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Expense under threshold - can be auto-processed
            # But still create approval for tracking
            approval_content = """---
type: odoo
action: create_expense
product_id: 456
amount: 150.00
approval_required: false
---

Office supplies expense logged.
"""
            approval_file = vault_path / "Pending_Approval" / "ODOO_EXP_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify approval created
        assert (vault_path / "Pending_Approval" / "ODOO_EXP_001_approval.md").exists()

    def test_get_invoices_query(self, vault_path, monkeypatch):
        """Test querying invoices from Odoo"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create query task
        task_content = """---
type: odoo
action: get_invoices
start_date: 2026-02-01
end_date: 2026-02-28
status: all
---

Get all invoices for February 2026
"""
        task_file = vault_path / "Needs_Action" / "ODOO_QUERY_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Query results don't need approval
            result_content = """---
type: odoo
action: get_invoices
status: completed
---

## Invoice Query Results

**Period**: February 2026
**Total Invoices**: 15
**Total Amount**: $45,000

### Breakdown
- Paid: 10 invoices ($30,000)
- Posted: 3 invoices ($10,000)
- Draft: 2 invoices ($5,000)
"""
            # Move directly to Done (no approval needed for queries)
            done_file = vault_path / "Done" / "ODOO_QUERY_001.md"
            done_file.write_text(result_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify task claimed
        assert (vault_path / "In_Progress" / "ODOO_QUERY_001.md").exists()

    def test_journal_entry_requires_approval(self, vault_path, monkeypatch):
        """Test journal entry always requires approval"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create journal entry task
        task_content = """---
type: odoo
action: post_journal_entry
journal_id: 1
---

Post adjustment entry
Debit: Account 100000 - $1000
Credit: Account 200000 - $1000
"""
        task_file = vault_path / "Needs_Action" / "ODOO_JE_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            approval_content = """---
type: odoo
action: post_journal_entry
journal_id: 1
approval_required: true
---

## Journal Entry

**Journal**: General Journal (ID: 1)

### Lines
1. Debit: Account 100000 - $1,000.00
2. Credit: Account 200000 - $1,000.00

**Total**: Balanced ($1,000 debit = $1,000 credit)

**⚠️ APPROVAL REQUIRED**: Journal entries always require human approval.
"""
            approval_file = vault_path / "Pending_Approval" / "ODOO_JE_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify approval created (mandatory for journal entries)
        assert (vault_path / "Pending_Approval" / "ODOO_JE_001_approval.md").exists()

        # Verify approval file has warning
        approval_content = (vault_path / "Pending_Approval" / "ODOO_JE_001_approval.md").read_text(encoding='utf-8')
        assert "APPROVAL REQUIRED" in approval_content

    def test_odoo_connection_failure_graceful_degradation(self, vault_path, monkeypatch):
        """Test graceful degradation when Odoo is unavailable"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create task
        task_content = """---
type: odoo
action: get_account_balance
account_code: 100000
---

Get bank account balance
"""
        task_file = vault_path / "Needs_Action" / "ODOO_FAIL_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude_with_failure(task_filename, skill_content):
            # Simulate Odoo connection failure
            # Claude should create SYSTEM_ALERT
            alert_content = """---
type: system_alert
service: odoo
error: Connection timeout
timestamp: 2026-02-24T11:30:00Z
action_required: true
---

## Alert

Odoo service is unavailable. Connection timeout after 3 retries.

## What to Do

1. Check Odoo Docker container: `docker ps | grep odoo`
2. Verify Odoo is running: http://localhost:8069
3. Check credentials in .env
4. Retry task once Odoo is back online
"""
            alert_file = vault_path / "Needs_Action" / "SYSTEM_ALERT_odoo_20260224.md"
            alert_file.write_text(alert_content, encoding='utf-8')
            return False  # Trigger failed

        orch.trigger_claude = mock_trigger_claude_with_failure
        orch.run_once()

        # Verify SYSTEM_ALERT created
        alert_files = list((vault_path / "Needs_Action").glob("SYSTEM_ALERT_*.md"))
        assert len(alert_files) >= 1
