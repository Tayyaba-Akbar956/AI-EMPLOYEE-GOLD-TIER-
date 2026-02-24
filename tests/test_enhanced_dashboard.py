"""Tests for Enhanced Dashboard - Phase 9 Silver Tier."""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from src.skills.enhanced_dashboard import EnhancedDashboard


class TestDashboardGeneration:
    """Test dashboard generation."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_generate_dashboard(self, dashboard):
        """Test generating dashboard."""
        result = dashboard.generate_dashboard()

        assert result['success'] is True
        assert result['filepath'] is not None

    def test_dashboard_file_exists(self, dashboard):
        """Test dashboard file is created."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        assert os.path.exists(filepath)
        assert filepath.endswith('Dashboard.md')

    def test_dashboard_content_structure(self, dashboard):
        """Test dashboard has required sections."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert '# AI Employee Dashboard' in content
        assert 'Multi-Platform Summary' in content
        assert 'Pending Approvals' in content
        assert 'Active Plans' in content
        assert 'Workflow Status' in content
        assert 'Financial Tracking' in content
        assert 'Recent Activity' in content
        assert 'System Status' in content


class TestMultiPlatformSummary:
    """Test multi-platform summary."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_platform_summary(self, dashboard):
        """Test getting platform summary."""
        summary = dashboard.get_platform_summary()

        assert isinstance(summary, dict)
        assert 'email' in summary
        assert 'whatsapp' in summary
        assert 'linkedin' in summary
        assert 'files' in summary

    def test_platform_counts(self, dashboard):
        """Test platform counts are integers."""
        summary = dashboard.get_platform_summary()

        for platform, count in summary.items():
            assert isinstance(count, int)
            assert count >= 0


class TestPendingApprovals:
    """Test pending approvals section."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_pending_approvals(self, dashboard):
        """Test getting pending approvals."""
        approvals = dashboard.get_pending_approvals()

        assert isinstance(approvals, list)

    def test_approval_structure(self, dashboard):
        """Test approval item structure."""
        # Add mock approval
        dashboard._add_mock_approval({
            'item_id': 'test-123',
            'type': 'invoice',
            'amount': 1500,
            'priority': 'high',
            'deadline': '2026-02-20'
        })

        approvals = dashboard.get_pending_approvals()
        if approvals:
            approval = approvals[0]
            assert 'item_id' in approval
            assert 'type' in approval
            assert 'amount' in approval or 'priority' in approval


class TestActivePlans:
    """Test active plans section."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_active_plans(self, dashboard):
        """Test getting active plans."""
        plans = dashboard.get_active_plans()

        assert isinstance(plans, list)

    def test_plan_progress(self, dashboard):
        """Test plan progress calculation."""
        # Add mock plan
        dashboard._add_mock_plan({
            'plan_id': 'plan-123',
            'title': 'Test Plan',
            'total_steps': 10,
            'completed_steps': 5
        })

        plans = dashboard.get_active_plans()
        if plans:
            plan = plans[0]
            assert 'progress' in plan or 'completed_steps' in plan


class TestWorkflowStatus:
    """Test workflow status section."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_workflow_status(self, dashboard):
        """Test getting workflow status."""
        workflows = dashboard.get_workflow_status()

        assert isinstance(workflows, list)

    def test_workflow_structure(self, dashboard):
        """Test workflow item structure."""
        # Add mock workflow
        dashboard._add_mock_workflow({
            'workflow_id': 'wf-123',
            'type': 'invoice_processing',
            'state': 'running',
            'current_step': 2
        })

        workflows = dashboard.get_workflow_status()
        if workflows:
            workflow = workflows[0]
            assert 'workflow_id' in workflow or 'type' in workflow


class TestFinancialTracking:
    """Test financial tracking section."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_financial_summary(self, dashboard):
        """Test getting financial summary."""
        summary = dashboard.get_financial_summary()

        assert isinstance(summary, dict)
        assert 'pending_invoices' in summary or 'total_expenses' in summary

    def test_budget_status(self, dashboard):
        """Test budget status in financial summary."""
        summary = dashboard.get_financial_summary()

        if 'budget_status' in summary:
            budget = summary['budget_status']
            assert 'total_budget' in budget or 'spent' in budget


class TestRecentActivity:
    """Test recent activity section."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_recent_activity(self, dashboard):
        """Test getting recent activity."""
        activity = dashboard.get_recent_activity()

        assert isinstance(activity, list)

    def test_activity_limit(self, dashboard):
        """Test activity limited to 10 items."""
        # Add 15 mock activities
        for i in range(15):
            dashboard._add_mock_activity({
                'timestamp': datetime.now().isoformat(),
                'action': f'Test action {i}'
            })

        activity = dashboard.get_recent_activity()
        assert len(activity) <= 10


class TestSystemStatus:
    """Test system status section."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_get_system_status(self, dashboard):
        """Test getting system status."""
        status = dashboard.get_system_status()

        assert isinstance(status, dict)

    def test_watcher_status(self, dashboard):
        """Test watcher status in system status."""
        status = dashboard.get_system_status()

        assert 'watchers' in status or 'email_watcher' in status


class TestRealTimeUpdates:
    """Test real-time update functionality."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_update_on_event(self, dashboard):
        """Test dashboard updates on event."""
        result = dashboard.update_on_event('new_item', {'source': 'email'})

        assert result['success'] is True

    def test_scheduled_update(self, dashboard):
        """Test scheduled dashboard update."""
        result = dashboard.scheduled_update()

        assert result['success'] is True

    def test_on_demand_update(self, dashboard):
        """Test on-demand dashboard update."""
        result = dashboard.generate_dashboard()

        assert result['success'] is True


class TestDashboardFormatting:
    """Test dashboard formatting."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)
        yield dashboard
        shutil.rmtree(vault_dir)

    def test_markdown_table_format(self, dashboard):
        """Test markdown table formatting."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for table elements
        assert '|' in content
        assert '---' in content or '|-' in content

    def test_timestamp_format(self, dashboard):
        """Test timestamp formatting."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for timestamp
        assert 'Last Updated' in content or 'Generated' in content


class TestDashboardWithData:
    """Test dashboard generation with populated data."""

    @pytest.fixture
    def dashboard(self):
        """Create enhanced dashboard with mock data."""
        vault_dir = tempfile.mkdtemp()
        dashboard = EnhancedDashboard(vault_dir)

        # Add mock data
        dashboard._add_mock_approval({
            'item_id': 'INV-001',
            'type': 'invoice',
            'amount': 2500,
            'priority': 'high',
            'deadline': '2026-02-20'
        })

        dashboard._add_mock_plan({
            'plan_id': 'PLAN-001',
            'title': 'Q1 Marketing Campaign',
            'total_steps': 10,
            'completed_steps': 7,
            'status': 'active'
        })

        dashboard._add_mock_workflow({
            'workflow_id': 'WF-001',
            'type': 'invoice_processing',
            'state': 'running',
            'current_step': 3
        })

        for i in range(5):
            dashboard._add_mock_activity({
                'timestamp': '2026-02-18 10:00:00',
                'action': f'Processed item {i}'
            })

        yield dashboard
        shutil.rmtree(vault_dir)

    def test_dashboard_with_approvals(self, dashboard):
        """Test dashboard displays approval data."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'INV-001' in content
        assert 'invoice' in content
        assert '$2,500.00' in content

    def test_dashboard_with_plans(self, dashboard):
        """Test dashboard displays plan data."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Q1 Marketing Campaign' in content
        assert '70%' in content

    def test_dashboard_with_workflows(self, dashboard):
        """Test dashboard displays workflow data."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'WF-001' in content
        assert 'invoice_processing' in content
        assert 'running' in content

    def test_dashboard_with_activity(self, dashboard):
        """Test dashboard displays activity data."""
        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Processed item' in content

    def test_plan_with_progress_percentage(self, dashboard):
        """Test plan with progress field."""
        dashboard._add_mock_plan({
            'plan_id': 'PLAN-002',
            'title': 'Test Plan',
            'progress': 85,
            'status': 'active'
        })

        result = dashboard.generate_dashboard()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert '85%' in content


class TestErrorHandling:
    """Test error handling."""

    def test_generate_dashboard_error(self):
        """Test dashboard generation with invalid path."""
        # Use invalid path
        dashboard = EnhancedDashboard('/invalid/path/that/does/not/exist')
        result = dashboard.generate_dashboard()

        assert result['success'] is False
        assert 'error' in result

    def test_update_on_event_error(self):
        """Test update on event with invalid path."""
        dashboard = EnhancedDashboard('/invalid/path/that/does/not/exist')
        result = dashboard.update_on_event('test', {})

        assert result['success'] is False
        assert 'error' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
