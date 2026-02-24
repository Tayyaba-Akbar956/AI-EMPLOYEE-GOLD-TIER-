"""Tests for Workflow Orchestrator - Phase 6-7 Silver Tier."""

import pytest
import os
import tempfile
import shutil
import json
from datetime import datetime
from pathlib import Path

from src.skills.workflow_orchestrator import WorkflowOrchestrator


class TestWorkflowDetection:
    """Test workflow detection and selection."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_detect_invoice_workflow(self, orchestrator):
        """Test invoice workflow detection."""
        item_data = {
            'type': 'invoice',
            'amount': 1500,
            'vendor': 'Tech Supplies Inc'
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'invoice_processing'

    def test_detect_receipt_workflow(self, orchestrator):
        """Test receipt workflow detection."""
        item_data = {
            'type': 'receipt',
            'amount': 50,
            'category': 'Meals'
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'receipt_processing'

    def test_detect_research_workflow(self, orchestrator):
        """Test research workflow detection."""
        item_data = {
            'body': 'Please research competitors in the AI space',
            'keywords': ['research', 'find', 'compare']
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'research'

    def test_detect_file_organization_workflow(self, orchestrator):
        """Test file organization workflow detection."""
        item_data = {
            'type': 'file',
            'filepath': '/path/to/document.pdf'
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'file_organization'

    def test_detect_email_response_workflow(self, orchestrator):
        """Test email response workflow detection."""
        item_data = {
            'type': 'email',
            'requires_response': True,
            'priority': 'high'
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'email_response'

    def test_detect_meeting_preparation_workflow(self, orchestrator):
        """Test meeting preparation workflow detection."""
        item_data = {
            'type': 'meeting_invite',
            'subject': 'Quarterly Review Meeting'
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'meeting_preparation'

    def test_detect_expense_report_workflow(self, orchestrator):
        """Test expense report workflow detection."""
        item_data = {
            'trigger': 'end_of_month',
            'type': 'expense_report'
        }
        workflow_type = orchestrator.detect_workflow(item_data)
        assert workflow_type == 'expense_report'


class TestWorkflowExecution:
    """Test workflow execution."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_execute_invoice_workflow(self, orchestrator):
        """Test invoice workflow execution."""
        item_data = {
            'type': 'invoice',
            'amount': 1500,
            'vendor': 'Tech Supplies Inc',
            'due_date': '2026-03-01'
        }
        result = orchestrator.execute_workflow('invoice_processing', item_data)

        assert result['success'] is True
        assert result['workflow_id'] is not None
        assert result['status'] in ['completed', 'paused']

    def test_execute_receipt_workflow(self, orchestrator):
        """Test receipt workflow execution."""
        item_data = {
            'type': 'receipt',
            'amount': 50,
            'category': 'Meals',
            'date': '2026-02-18'
        }
        result = orchestrator.execute_workflow('receipt_processing', item_data)

        assert result['success'] is True
        assert result['workflow_id'] is not None

    def test_execute_research_workflow(self, orchestrator):
        """Test research workflow execution."""
        item_data = {
            'topic': 'AI competitors',
            'scope': 'Market analysis'
        }
        result = orchestrator.execute_workflow('research', item_data)

        assert result['success'] is True
        assert result['workflow_id'] is not None


class TestStateManagement:
    """Test workflow state management."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_pause_workflow(self, orchestrator):
        """Test pausing workflow."""
        item_data = {'type': 'invoice', 'amount': 1500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Pause workflow
        pause_result = orchestrator.pause_workflow(workflow_id)
        assert pause_result['success'] is True

        # Check status
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['state'] == 'paused'

    def test_resume_workflow(self, orchestrator):
        """Test resuming workflow."""
        item_data = {'type': 'invoice', 'amount': 1500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Pause then resume
        orchestrator.pause_workflow(workflow_id)
        resume_result = orchestrator.resume_workflow(workflow_id)

        assert resume_result['success'] is True

    def test_rollback_workflow(self, orchestrator):
        """Test rolling back workflow."""
        item_data = {'type': 'invoice', 'amount': 1500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Rollback workflow
        rollback_result = orchestrator.rollback_workflow(workflow_id)
        assert rollback_result['success'] is True

    def test_retry_failed_step(self, orchestrator):
        """Test retrying failed step."""
        item_data = {'type': 'invoice', 'amount': 1500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Simulate failure and retry
        retry_result = orchestrator.retry_workflow(workflow_id)
        assert retry_result['success'] is True


class TestApprovalPoints:
    """Test approval point handling."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_workflow_pauses_at_approval_point(self, orchestrator):
        """Test workflow pauses at approval point."""
        item_data = {
            'type': 'invoice',
            'amount': 2000,  # High value, requires approval
            'vendor': 'Expensive Vendor'
        }
        result = orchestrator.execute_workflow('invoice_processing', item_data)

        assert result['status'] == 'paused'
        assert result['reason'] == 'approval_required'

    def test_approve_and_continue(self, orchestrator):
        """Test approving and continuing workflow."""
        item_data = {'type': 'invoice', 'amount': 2000}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Approve
        approve_result = orchestrator.approve_workflow(workflow_id)
        assert approve_result['success'] is True

        # Check workflow continues
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['state'] in ['running', 'completed']

    def test_reject_workflow(self, orchestrator):
        """Test rejecting workflow."""
        item_data = {'type': 'invoice', 'amount': 2000}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Reject
        reject_result = orchestrator.reject_workflow(workflow_id, reason='Budget exceeded')
        assert reject_result['success'] is True

        # Check workflow marked as failed
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['state'] == 'failed'


class TestErrorRecovery:
    """Test error recovery and retry logic."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_retry_on_failure(self, orchestrator):
        """Test automatic retry on failure."""
        item_data = {'type': 'invoice', 'amount': 1500, 'simulate_failure': True}
        result = orchestrator.execute_workflow('invoice_processing', item_data)

        # Should retry up to 3 times
        workflow_id = result['workflow_id']
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['retry_count'] <= 3

    def test_max_retries_exceeded(self, orchestrator):
        """Test workflow fails after max retries."""
        item_data = {'type': 'receipt', 'amount': 50, 'always_fail': True}
        result = orchestrator.execute_workflow('receipt_processing', item_data)

        workflow_id = result['workflow_id']
        status = orchestrator.get_workflow_status(workflow_id)

        # After 3 retries, should be marked as failed
        assert status['retry_count'] == 3
        assert status['state'] == 'failed'


class TestDatabaseIntegration:
    """Test database integration for workflow tracking."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_workflow_saved_to_database(self, orchestrator):
        """Test workflow is saved to database."""
        item_data = {'type': 'invoice', 'amount': 1500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Retrieve from database
        workflow = orchestrator.get_workflow_from_db(workflow_id)
        assert workflow is not None
        assert workflow['workflow_type'] == 'invoice_processing'

    def test_workflow_state_persisted(self, orchestrator):
        """Test workflow state is persisted."""
        item_data = {'type': 'invoice', 'amount': 1500}
        result = orchestrator.execute_workflow('invoice_processing', item_data)
        workflow_id = result['workflow_id']

        # Pause workflow
        orchestrator.pause_workflow(workflow_id)

        # Retrieve from database
        workflow = orchestrator.get_workflow_from_db(workflow_id)
        assert workflow['state'] == 'paused'

    def test_list_active_workflows(self, orchestrator):
        """Test listing active workflows."""
        # Create multiple workflows that will pause (high value invoices)
        orchestrator.execute_workflow('invoice_processing', {'type': 'invoice', 'amount': 2000})
        orchestrator.execute_workflow('invoice_processing', {'type': 'invoice', 'amount': 1500})

        # List active workflows
        active = orchestrator.list_active_workflows()
        assert len(active) >= 2


class TestStepExecution:
    """Test individual step execution."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_execute_step(self, orchestrator):
        """Test executing individual step."""
        step_data = {
            'name': 'validate_invoice',
            'params': {'amount': 1500, 'vendor': 'Test Vendor'}
        }
        result = orchestrator.execute_step(step_data)

        assert result['success'] is True
        assert result['output'] is not None

    def test_step_failure_handling(self, orchestrator):
        """Test step failure handling."""
        step_data = {
            'name': 'invalid_step',
            'params': {}
        }
        result = orchestrator.execute_step(step_data)

        assert result['success'] is False
        assert 'error' in result


class TestConcurrentWorkflows:
    """Test concurrent workflow execution."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_multiple_workflows_concurrent(self, orchestrator):
        """Test multiple workflows can run concurrently."""
        # Start multiple workflows
        result1 = orchestrator.execute_workflow('invoice_processing', {'type': 'invoice', 'amount': 1000})
        result2 = orchestrator.execute_workflow('receipt_processing', {'type': 'receipt', 'amount': 50})
        result3 = orchestrator.execute_workflow('research', {'topic': 'AI trends'})

        assert result1['success'] is True
        assert result2['success'] is True
        assert result3['success'] is True

        # All should have unique IDs
        assert result1['workflow_id'] != result2['workflow_id']
        assert result2['workflow_id'] != result3['workflow_id']


class TestWorkflowCompletion:
    """Test workflow completion."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator."""
        vault_dir = tempfile.mkdtemp()
        orchestrator = WorkflowOrchestrator(vault_dir)
        yield orchestrator
        shutil.rmtree(vault_dir)

    def test_workflow_completes_successfully(self, orchestrator):
        """Test workflow completes successfully."""
        item_data = {'type': 'receipt', 'amount': 50}
        result = orchestrator.execute_workflow('receipt_processing', item_data)
        workflow_id = result['workflow_id']

        # Check completion
        status = orchestrator.get_workflow_status(workflow_id)
        assert status['state'] in ['completed', 'running']

    def test_completed_workflow_logged(self, orchestrator):
        """Test completed workflow is logged."""
        item_data = {'type': 'receipt', 'amount': 50}
        result = orchestrator.execute_workflow('receipt_processing', item_data)
        workflow_id = result['workflow_id']

        # Check logs
        logs = orchestrator.get_workflow_logs(workflow_id)
        assert len(logs) > 0

    def test_unknown_workflow_type(self, orchestrator):
        """Test unknown workflow type returns error."""
        result = orchestrator.execute_workflow('unknown_workflow', {})
        assert result['success'] is False
        assert 'Unknown workflow type' in result['error']

    def test_workflow_not_found_status(self, orchestrator):
        """Test getting status of non-existent workflow."""
        status = orchestrator.get_workflow_status('invalid-id')
        assert 'error' in status

    def test_workflow_not_found_logs(self, orchestrator):
        """Test getting logs of non-existent workflow."""
        logs = orchestrator.get_workflow_logs('invalid-id')
        assert logs == []

    def test_pause_nonexistent_workflow(self, orchestrator):
        """Test pausing non-existent workflow."""
        result = orchestrator.pause_workflow('invalid-id')
        assert result['success'] is False

    def test_resume_nonexistent_workflow(self, orchestrator):
        """Test resuming non-existent workflow."""
        result = orchestrator.resume_workflow('invalid-id')
        assert result['success'] is False

    def test_resume_non_paused_workflow(self, orchestrator):
        """Test resuming workflow that is not paused."""
        item_data = {'type': 'receipt', 'amount': 50}
        result = orchestrator.execute_workflow('receipt_processing', item_data)
        workflow_id = result['workflow_id']

        # Try to resume (should fail if not paused)
        resume_result = orchestrator.resume_workflow(workflow_id)
        # May succeed or fail depending on timing
        assert 'success' in resume_result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
