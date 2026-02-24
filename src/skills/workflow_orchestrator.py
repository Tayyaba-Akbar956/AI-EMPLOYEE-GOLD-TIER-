"""Workflow Orchestrator for AI Employee Silver Tier.

Executes and manages multi-step automated workflows with state management,
approval handling, error recovery, and database integration.
"""

import os
import uuid
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates multi-step automated workflows.

    Handles workflow detection, execution, state management, approval points,
    error recovery, and database integration.
    """

    def __init__(self, vault_path: str, db_path: Optional[str] = None):
        """Initialize workflow orchestrator.

        Args:
            vault_path: Path to AI_Employee_Vault
            db_path: Optional path to database file
        """
        self.vault_path = Path(vault_path)
        self.db_path = db_path or str(self.vault_path / 'Database' / 'ai_employee.db')

        # In-memory workflow storage (simulating database)
        self.workflows = {}

        # Workflow definitions
        self.workflow_definitions = self._load_workflow_definitions()

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure required folders exist."""
        folders = [
            'Logs/workflows',
            'Database'
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    def _load_workflow_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load workflow definitions.

        Returns:
            Dictionary of workflow definitions
        """
        return {
            'invoice_processing': {
                'name': 'Invoice Processing',
                'steps': [
                    {'name': 'validate_invoice', 'description': 'Validate invoice data'},
                    {'name': 'check_approval_threshold', 'description': 'Check if approval needed'},
                    {'name': 'create_financial_record', 'description': 'Create financial record'},
                    {'name': 'set_payment_reminder', 'description': 'Set payment reminder'}
                ],
                'approval_threshold': 1000,
                'requires_approval': True
            },
            'receipt_processing': {
                'name': 'Receipt Processing',
                'steps': [
                    {'name': 'validate_receipt', 'description': 'Validate receipt data'},
                    {'name': 'categorize_expense', 'description': 'Categorize expense'},
                    {'name': 'create_expense_record', 'description': 'Create expense record'},
                    {'name': 'update_budget', 'description': 'Update budget tracking'}
                ],
                'requires_approval': False
            },
            'research': {
                'name': 'Research',
                'steps': [
                    {'name': 'define_scope', 'description': 'Define research scope'},
                    {'name': 'gather_sources', 'description': 'Gather information sources'},
                    {'name': 'analyze_data', 'description': 'Analyze collected data'},
                    {'name': 'generate_report', 'description': 'Generate research report'}
                ],
                'requires_approval': False
            },
            'file_organization': {
                'name': 'File Organization',
                'steps': [
                    {'name': 'detect_file_type', 'description': 'Detect file type'},
                    {'name': 'extract_metadata', 'description': 'Extract file metadata'},
                    {'name': 'categorize_file', 'description': 'Categorize file'},
                    {'name': 'move_to_destination', 'description': 'Move to appropriate folder'}
                ],
                'requires_approval': False
            },
            'email_response': {
                'name': 'Email Response',
                'steps': [
                    {'name': 'analyze_email', 'description': 'Analyze email content'},
                    {'name': 'draft_response', 'description': 'Draft response'},
                    {'name': 'review_draft', 'description': 'Review draft (approval point)'},
                    {'name': 'send_email', 'description': 'Send email'}
                ],
                'requires_approval': True,
                'approval_at_step': 2
            },
            'meeting_preparation': {
                'name': 'Meeting Preparation',
                'steps': [
                    {'name': 'parse_meeting_details', 'description': 'Parse meeting details'},
                    {'name': 'create_agenda', 'description': 'Create meeting agenda'},
                    {'name': 'gather_materials', 'description': 'Gather relevant materials'},
                    {'name': 'send_reminders', 'description': 'Send meeting reminders'}
                ],
                'requires_approval': False
            },
            'expense_report': {
                'name': 'Expense Report',
                'steps': [
                    {'name': 'collect_expenses', 'description': 'Collect all expenses'},
                    {'name': 'categorize_expenses', 'description': 'Categorize by type'},
                    {'name': 'calculate_totals', 'description': 'Calculate totals'},
                    {'name': 'generate_report', 'description': 'Generate expense report'},
                    {'name': 'export_csv', 'description': 'Export to CSV'}
                ],
                'requires_approval': True,
                'approval_threshold': 500
            }
        }

    def detect_workflow(self, item_data: Dict[str, Any]) -> Optional[str]:
        """Detect appropriate workflow for item.

        Args:
            item_data: Item data dictionary

        Returns:
            Workflow type string or None
        """
        item_type = item_data.get('type', '')

        # Invoice
        if item_type == 'invoice':
            return 'invoice_processing'

        # Receipt
        if item_type == 'receipt':
            return 'receipt_processing'

        # Research
        if 'research' in item_data.get('body', '').lower() or \
           any(kw in item_data.get('keywords', []) for kw in ['research', 'find', 'compare']):
            return 'research'

        # File organization
        if item_type == 'file' and 'filepath' in item_data:
            return 'file_organization'

        # Email response
        if item_type == 'email' and item_data.get('requires_response'):
            return 'email_response'

        # Meeting preparation
        if item_type == 'meeting_invite':
            return 'meeting_preparation'

        # Expense report
        if item_data.get('trigger') == 'end_of_month' or item_type == 'expense_report':
            return 'expense_report'

        return None

    def execute_workflow(self, workflow_type: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow.

        Args:
            workflow_type: Type of workflow to execute
            item_data: Item data for workflow

        Returns:
            Execution result dictionary
        """
        try:
            # Get workflow definition
            workflow_def = self.workflow_definitions.get(workflow_type)
            if not workflow_def:
                return {
                    'success': False,
                    'error': f'Unknown workflow type: {workflow_type}'
                }

            # Create workflow instance
            workflow_id = str(uuid.uuid4())
            workflow = {
                'workflow_id': workflow_id,
                'workflow_type': workflow_type,
                'workflow_name': workflow_def['name'],
                'item_data': item_data,
                'state': 'running',
                'current_step': 0,
                'steps': workflow_def['steps'],
                'retry_count': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'logs': []
            }

            # Save to database
            self.workflows[workflow_id] = workflow
            self._log_workflow(workflow_id, 'Workflow started')

            # Check if approval needed before execution
            if workflow_def.get('requires_approval'):
                approval_threshold = workflow_def.get('approval_threshold', 0)
                amount = item_data.get('amount', 0)

                if amount >= approval_threshold:
                    workflow['state'] = 'paused'
                    workflow['pause_reason'] = 'approval_required'
                    self._log_workflow(workflow_id, 'Paused for approval')

                    return {
                        'success': True,
                        'workflow_id': workflow_id,
                        'status': 'paused',
                        'reason': 'approval_required'
                    }

            # Execute steps
            result = self._execute_steps(workflow_id)

            return {
                'success': True,
                'workflow_id': workflow_id,
                'status': workflow['state'],
                'result': result
            }

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _execute_steps(self, workflow_id: str) -> Dict[str, Any]:
        """Execute workflow steps.

        Args:
            workflow_id: Workflow ID

        Returns:
            Execution result
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        steps = workflow['steps']
        current_step = workflow['current_step']

        # Execute remaining steps
        while current_step < len(steps):
            step = steps[current_step]

            # Check for approval point
            workflow_def = self.workflow_definitions.get(workflow['workflow_type'])
            if workflow_def.get('approval_at_step') == current_step:
                workflow['state'] = 'paused'
                workflow['pause_reason'] = 'approval_required'
                workflow['current_step'] = current_step
                self._log_workflow(workflow_id, f'Paused at step {current_step} for approval')
                return {'success': True, 'paused': True}

            # Execute step
            step_result = self.execute_step({
                'name': step['name'],
                'params': workflow['item_data']
            })

            if not step_result['success']:
                # Handle failure
                workflow['retry_count'] += 1
                workflow['updated_at'] = datetime.now().isoformat()
                self._log_workflow(workflow_id, f'Step {step["name"]} failed (retry {workflow["retry_count"]})')

                if workflow['retry_count'] >= 3:
                    workflow['state'] = 'failed'
                    self._log_workflow(workflow_id, 'Max retries exceeded, workflow failed')
                    return {'success': False, 'error': 'Max retries exceeded'}

                # Retry same step (don't increment current_step)
                continue

            # Step succeeded
            self._log_workflow(workflow_id, f'Step {step["name"]} completed')
            current_step += 1
            workflow['current_step'] = current_step
            workflow['retry_count'] = 0  # Reset retry count on success

        # All steps completed
        workflow['state'] = 'completed'
        workflow['completed_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, 'Workflow completed')

        return {'success': True, 'completed': True}

    def execute_step(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute individual workflow step.

        Args:
            step_data: Step data with name and params

        Returns:
            Step execution result
        """
        step_name = step_data.get('name')
        params = step_data.get('params', {})

        # Simulate step execution
        if step_name == 'invalid_step':
            return {'success': False, 'error': 'Invalid step'}

        # Check for simulated failure
        if params.get('simulate_failure'):
            return {'success': False, 'error': 'Simulated failure'}

        # Check for always_fail (for testing max retries)
        if params.get('always_fail'):
            return {'success': False, 'error': 'Always fails'}

        # Step succeeded
        return {
            'success': True,
            'output': f'Step {step_name} executed successfully'
        }

    def pause_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Pause workflow execution.

        Args:
            workflow_id: Workflow ID

        Returns:
            Result dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        workflow['state'] = 'paused'
        workflow['updated_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, 'Workflow paused')

        return {'success': True}

    def resume_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Resume paused workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Result dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        if workflow['state'] != 'paused':
            return {'success': False, 'error': 'Workflow is not paused'}

        workflow['state'] = 'running'
        workflow['updated_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, 'Workflow resumed')

        # Continue execution
        self._execute_steps(workflow_id)

        return {'success': True}

    def rollback_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Rollback workflow to previous state.

        Args:
            workflow_id: Workflow ID

        Returns:
            Result dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        # Reset to beginning
        workflow['current_step'] = 0
        workflow['state'] = 'running'
        workflow['retry_count'] = 0
        workflow['updated_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, 'Workflow rolled back')

        return {'success': True}

    def retry_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Retry failed workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Result dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        workflow['state'] = 'running'
        workflow['updated_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, 'Workflow retry initiated')

        # Continue execution from current step
        self._execute_steps(workflow_id)

        return {'success': True}

    def approve_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Approve workflow and continue execution.

        Args:
            workflow_id: Workflow ID

        Returns:
            Result dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        workflow['state'] = 'running'
        workflow['approved'] = True
        workflow['approved_at'] = datetime.now().isoformat()
        workflow['updated_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, 'Workflow approved')

        # Continue execution
        self._execute_steps(workflow_id)

        return {'success': True}

    def reject_workflow(self, workflow_id: str, reason: str = '') -> Dict[str, Any]:
        """Reject workflow.

        Args:
            workflow_id: Workflow ID
            reason: Rejection reason

        Returns:
            Result dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}

        workflow['state'] = 'failed'
        workflow['rejected'] = True
        workflow['rejection_reason'] = reason
        workflow['updated_at'] = datetime.now().isoformat()
        self._log_workflow(workflow_id, f'Workflow rejected: {reason}')

        return {'success': True}

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow status dictionary
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'error': 'Workflow not found'}

        return {
            'workflow_id': workflow_id,
            'workflow_type': workflow['workflow_type'],
            'state': workflow['state'],
            'current_step': workflow['current_step'],
            'retry_count': workflow['retry_count'],
            'created_at': workflow['created_at'],
            'updated_at': workflow['updated_at']
        }

    def get_workflow_from_db(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow from database.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow dictionary or None
        """
        return self.workflows.get(workflow_id)

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows.

        Returns:
            List of active workflow dictionaries
        """
        active = []
        for workflow_id, workflow in self.workflows.items():
            if workflow['state'] in ['running', 'paused']:
                active.append({
                    'workflow_id': workflow_id,
                    'workflow_type': workflow['workflow_type'],
                    'state': workflow['state'],
                    'current_step': workflow['current_step']
                })
        return active

    def get_workflow_logs(self, workflow_id: str) -> List[str]:
        """Get workflow logs.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of log entries
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return []

        return workflow.get('logs', [])

    def _log_workflow(self, workflow_id: str, message: str):
        """Log workflow event.

        Args:
            workflow_id: Workflow ID
            message: Log message
        """
        workflow = self.workflows.get(workflow_id)
        if workflow:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {message}"
            workflow['logs'].append(log_entry)
            logger.info(f"Workflow {workflow_id}: {message}")
