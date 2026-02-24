"""Integration Tests - Phase 8-10 Silver Tier.

Tests integration across all Silver Tier Phase 8-10 components:
- Financial tracking + Report generation
- Workflow orchestration + Financial tracking
- Enhanced dashboard + All data sources
- End-to-end scenarios
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from src.skills.financial_tracker import FinancialTracker
from src.skills.report_generator import ReportGenerator
from src.skills.workflow_orchestrator import WorkflowOrchestrator
from src.skills.enhanced_dashboard import EnhancedDashboard


class TestFinancialIntegration:
    """Test financial tracker + report generator integration."""

    @pytest.fixture
    def vault_dir(self):
        """Create temporary vault."""
        vault_dir = tempfile.mkdtemp()
        yield vault_dir
        shutil.rmtree(vault_dir)

    def test_expense_tracking_to_report(self, vault_dir):
        """Test expense tracking flows into reports."""
        tracker = FinancialTracker(vault_dir)
        generator = ReportGenerator(vault_dir)

        # Add expenses
        tracker.add_expense({
            'amount': 100,
            'category': 'Meals',
            'payee': 'Restaurant',
            'date': '2026-02-18'
        })
        tracker.add_expense({
            'amount': 200,
            'category': 'Travel',
            'payee': 'Airline',
            'date': '2026-02-18'
        })

        # Generate report
        result = generator.generate_weekly_report()

        assert result['success'] is True
        assert os.path.exists(result['filepath'])

    def test_invoice_tracking_to_monthly_report(self, vault_dir):
        """Test invoice tracking flows into monthly reports."""
        tracker = FinancialTracker(vault_dir)
        generator = ReportGenerator(vault_dir)

        # Add invoices
        tracker.add_invoice({
            'amount': 1500,
            'vendor': 'Vendor A',
            'due_date': '2026-03-01'
        })
        tracker.add_invoice({
            'amount': 2000,
            'vendor': 'Vendor B',
            'due_date': '2026-03-15'
        })

        # Generate monthly report
        result = generator.generate_monthly_report()

        assert result['success'] is True
        assert os.path.exists(result['filepath'])
        assert os.path.exists(result['csv_path'])

    def test_budget_tracking_integration(self, vault_dir):
        """Test budget tracking across components."""
        tracker = FinancialTracker(vault_dir)

        # Set budget
        tracker.set_monthly_budget(1000)

        # Add expenses
        tracker.add_expense({'amount': 500, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})
        tracker.add_expense({'amount': 300, 'category': 'Travel', 'payee': 'Airline', 'date': '2026-02-18'})

        # Check budget status
        status = tracker.get_budget_status()

        assert status['total_budget'] == 1000
        assert status['spent'] == 800
        assert status['remaining'] == 200
        assert status['percentage'] == 80
        assert status['alert'] is True


class TestWorkflowIntegration:
    """Test workflow orchestrator integration."""

    @pytest.fixture
    def vault_dir(self):
        """Create temporary vault."""
        vault_dir = tempfile.mkdtemp()
        yield vault_dir
        shutil.rmtree(vault_dir)

    def test_invoice_workflow_with_approval(self, vault_dir):
        """Test invoice workflow with approval threshold."""
        orchestrator = WorkflowOrchestrator(vault_dir)

        # Execute high-value invoice workflow
        item_data = {
            'type': 'invoice',
            'amount': 2500,
            'vendor': 'Tech Supplies Inc',
            'due_date': '2026-03-01'
        }

        result = orchestrator.execute_workflow('invoice_processing', item_data)

        assert result['success'] is True
        workflow_id = result['workflow_id']

        # Check workflow paused for approval
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['state'] == 'paused'

    def test_receipt_workflow_auto_process(self, vault_dir):
        """Test receipt workflow auto-processes without approval."""
        orchestrator = WorkflowOrchestrator(vault_dir)

        # Execute receipt workflow
        item_data = {
            'type': 'receipt',
            'amount': 50,
            'payee': 'Coffee Shop',
            'date': '2026-02-18'
        }

        result = orchestrator.execute_workflow('receipt_processing', item_data)

        assert result['success'] is True
        workflow_id = result['workflow_id']

        # Check workflow completed
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['state'] == 'completed'

    def test_workflow_resume_after_approval(self, vault_dir):
        """Test workflow resumes after approval."""
        orchestrator = WorkflowOrchestrator(vault_dir)

        # Execute workflow that pauses
        item_data = {'type': 'invoice', 'amount': 2500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Resume workflow
        resume_result = orchestrator.resume_workflow(workflow_id)

        assert resume_result['success'] is True


class TestDashboardIntegration:
    """Test enhanced dashboard integration."""

    @pytest.fixture
    def vault_dir(self):
        """Create temporary vault."""
        vault_dir = tempfile.mkdtemp()
        yield vault_dir
        shutil.rmtree(vault_dir)

    def test_dashboard_displays_financial_data(self, vault_dir):
        """Test dashboard displays financial tracking data."""
        tracker = FinancialTracker(vault_dir)
        dashboard = EnhancedDashboard(vault_dir)

        # Add financial data
        tracker.add_invoice({'amount': 1500, 'vendor': 'Vendor A', 'due_date': '2026-03-01'})
        tracker.add_expense({'amount': 100, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})

        # Generate dashboard
        result = dashboard.generate_dashboard()

        assert result['success'] is True
        assert os.path.exists(result['filepath'])

        # Verify content
        with open(result['filepath'], 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Financial Tracking' in content

    def test_dashboard_updates_on_event(self, vault_dir):
        """Test dashboard updates when events occur."""
        dashboard = EnhancedDashboard(vault_dir)

        # Trigger update on event
        result = dashboard.update_on_event('new_item', {'source': 'email'})

        assert result['success'] is True
        assert os.path.exists(result['filepath'])

    def test_dashboard_shows_workflow_status(self, vault_dir):
        """Test dashboard shows workflow status."""
        orchestrator = WorkflowOrchestrator(vault_dir)
        dashboard = EnhancedDashboard(vault_dir)

        # Start workflow
        orchestrator.execute_workflow('invoice_processing', {'type': 'invoice', 'amount': 2500})

        # Generate dashboard
        result = dashboard.generate_dashboard()

        assert result['success'] is True


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    @pytest.fixture
    def vault_dir(self):
        """Create temporary vault."""
        vault_dir = tempfile.mkdtemp()
        yield vault_dir
        shutil.rmtree(vault_dir)

    def test_invoice_processing_complete_flow(self, vault_dir):
        """Test complete invoice processing flow."""
        tracker = FinancialTracker(vault_dir)
        orchestrator = WorkflowOrchestrator(vault_dir)
        dashboard = EnhancedDashboard(vault_dir)

        # 1. Receive invoice
        invoice_data = {
            'type': 'invoice',
            'amount': 2500,
            'vendor': 'Tech Supplies Inc',
            'due_date': '2026-03-01'
        }

        # 2. Execute workflow
        workflow_result = orchestrator.execute_workflow('invoice_processing', invoice_data)
        assert workflow_result['success'] is True

        # 3. Track in financial system
        tracker_result = tracker.add_invoice(invoice_data)
        assert tracker_result['success'] is True

        # 4. Update dashboard
        dashboard_result = dashboard.update_on_event('invoice_received', invoice_data)
        assert dashboard_result['success'] is True

    def test_expense_report_generation_flow(self, vault_dir):
        """Test complete expense report generation flow."""
        tracker = FinancialTracker(vault_dir)
        generator = ReportGenerator(vault_dir)
        dashboard = EnhancedDashboard(vault_dir)

        # 1. Add multiple expenses
        expenses = [
            {'amount': 50, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'},
            {'amount': 100, 'category': 'Travel', 'payee': 'Airline', 'date': '2026-02-18'},
            {'amount': 30, 'category': 'Supplies', 'payee': 'Office Store', 'date': '2026-02-18'}
        ]

        for expense in expenses:
            result = tracker.add_expense(expense)
            assert result['success'] is True

        # 2. Generate weekly report
        report_result = generator.generate_weekly_report()
        assert report_result['success'] is True

        # 3. Update dashboard
        dashboard_result = dashboard.generate_dashboard()
        assert dashboard_result['success'] is True

    def test_budget_alert_flow(self, vault_dir):
        """Test budget alert flow."""
        tracker = FinancialTracker(vault_dir)
        dashboard = EnhancedDashboard(vault_dir)

        # 1. Set budget
        tracker.set_monthly_budget(1000)

        # 2. Add expenses approaching limit
        tracker.add_expense({'amount': 850, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})

        # 3. Check budget status
        status = tracker.get_budget_status()
        assert status['alert'] is True
        assert status['percentage'] >= 80

        # 4. Update dashboard
        dashboard_result = dashboard.generate_dashboard()
        assert dashboard_result['success'] is True

    def test_multi_workflow_concurrent_execution(self, vault_dir):
        """Test multiple workflows executing concurrently."""
        orchestrator = WorkflowOrchestrator(vault_dir)

        # Start multiple workflows
        wf1 = orchestrator.execute_workflow('invoice_processing', {'type': 'invoice', 'amount': 2500})
        wf2 = orchestrator.execute_workflow('receipt_processing', {'type': 'receipt', 'amount': 50})
        wf3 = orchestrator.execute_workflow('research', {'topic': 'Market Analysis'})

        assert wf1['success'] is True
        assert wf2['success'] is True
        assert wf3['success'] is True

        # Check all workflows tracked
        active = orchestrator.list_active_workflows()
        assert len(active) >= 1  # At least one should be active (paused or running)


class TestDataConsistency:
    """Test data consistency across components."""

    @pytest.fixture
    def vault_dir(self):
        """Create temporary vault."""
        vault_dir = tempfile.mkdtemp()
        yield vault_dir
        shutil.rmtree(vault_dir)

    def test_financial_data_consistency(self, vault_dir):
        """Test financial data remains consistent."""
        tracker = FinancialTracker(vault_dir)

        # Add invoice
        invoice_result = tracker.add_invoice({
            'amount': 1500,
            'vendor': 'Vendor A',
            'due_date': '2026-03-01'
        })
        invoice_id = invoice_result['invoice_id']

        # Retrieve and verify
        invoice = tracker.get_invoice(invoice_id)
        assert invoice is not None
        assert invoice['amount'] == 1500
        assert invoice['vendor'] == 'Vendor A'

    def test_workflow_state_consistency(self, vault_dir):
        """Test workflow state remains consistent."""
        orchestrator = WorkflowOrchestrator(vault_dir)

        # Start workflow
        result = orchestrator.execute_workflow('invoice_processing', {'type': 'invoice', 'amount': 2500})
        workflow_id = result['workflow_id']

        # Check state
        status1 = orchestrator.get_workflow_status(workflow_id)
        status2 = orchestrator.get_workflow_status(workflow_id)

        assert status1['state'] == status2['state']
        assert status1['current_step'] == status2['current_step']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
