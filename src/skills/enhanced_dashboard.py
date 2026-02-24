"""Enhanced Dashboard for AI Employee Silver Tier.

Generates real-time dashboard with multi-platform summary, approvals, plans,
workflows, financial tracking, and system status.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class EnhancedDashboard:
    """Generates enhanced real-time dashboard for AI Employee.

    Displays multi-platform summary, pending approvals, active plans,
    workflow status, financial tracking, recent activity, and system status.
    """

    def __init__(self, vault_path: str):
        """Initialize enhanced dashboard.

        Args:
            vault_path: Path to AI_Employee_Vault
        """
        self.vault_path = Path(vault_path)

        # Mock data storage (would use database in production)
        self.mock_approvals = []
        self.mock_plans = []
        self.mock_workflows = []
        self.mock_activities = []

    def generate_dashboard(self) -> Dict[str, Any]:
        """Generate complete dashboard.

        Returns:
            Result dictionary with filepath
        """
        try:
            # Gather all data
            platform_summary = self.get_platform_summary()
            pending_approvals = self.get_pending_approvals()
            active_plans = self.get_active_plans()
            workflow_status = self.get_workflow_status()
            financial_summary = self.get_financial_summary()
            recent_activity = self.get_recent_activity()
            system_status = self.get_system_status()

            # Generate markdown
            markdown = self._generate_dashboard_markdown(
                platform_summary,
                pending_approvals,
                active_plans,
                workflow_status,
                financial_summary,
                recent_activity,
                system_status
            )

            # Save dashboard
            filepath = self.vault_path / 'Dashboard.md'
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)

            logger.info(f"Generated dashboard: {filepath}")

            return {
                'success': True,
                'filepath': str(filepath)
            }

        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_dashboard_markdown(
        self,
        platform_summary: Dict[str, int],
        pending_approvals: List[Dict],
        active_plans: List[Dict],
        workflow_status: List[Dict],
        financial_summary: Dict,
        recent_activity: List[Dict],
        system_status: Dict
    ) -> str:
        """Generate dashboard markdown.

        Args:
            platform_summary: Platform counts
            pending_approvals: Pending approval items
            active_plans: Active plan items
            workflow_status: Workflow status items
            financial_summary: Financial summary data
            recent_activity: Recent activity items
            system_status: System status data

        Returns:
            Markdown string
        """
        markdown = f"# AI Employee Dashboard\n\n"
        markdown += f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown += "---\n\n"

        # Multi-Platform Summary
        markdown += "## Multi-Platform Summary\n\n"
        markdown += "| Platform | Items |\n"
        markdown += "|----------|-------|\n"
        for platform, count in platform_summary.items():
            markdown += f"| {platform.title()} | {count} |\n"
        markdown += "\n"

        # Pending Approvals
        markdown += "## Pending Approvals\n\n"
        if pending_approvals:
            markdown += "| Item | Type | Amount | Priority | Deadline |\n"
            markdown += "|------|------|--------|----------|----------|\n"
            for approval in pending_approvals[:5]:  # Show top 5
                item_id = approval.get('item_id', 'N/A')
                item_type = approval.get('type', 'N/A')
                amount = f"${approval.get('amount', 0):,.2f}" if 'amount' in approval else 'N/A'
                priority = approval.get('priority', 'normal')
                deadline = approval.get('deadline', 'N/A')
                markdown += f"| {item_id} | {item_type} | {amount} | {priority} | {deadline} |\n"
        else:
            markdown += "*No pending approvals*\n"
        markdown += "\n"

        # Active Plans
        markdown += "## Active Plans\n\n"
        if active_plans:
            markdown += "| Plan | Progress | Status |\n"
            markdown += "|------|----------|--------|\n"
            for plan in active_plans[:5]:  # Show top 5
                title = plan.get('title', 'Untitled')
                if 'progress' in plan:
                    progress = f"{plan['progress']}%"
                elif 'completed_steps' in plan and 'total_steps' in plan:
                    pct = int((plan['completed_steps'] / plan['total_steps']) * 100)
                    progress = f"{pct}%"
                else:
                    progress = "N/A"
                status = plan.get('status', 'active')
                markdown += f"| {title} | {progress} | {status} |\n"
        else:
            markdown += "*No active plans*\n"
        markdown += "\n"

        # Workflow Status
        markdown += "## Workflow Status\n\n"
        if workflow_status:
            markdown += "| Workflow | Type | State | Step |\n"
            markdown += "|----------|------|-------|------|\n"
            for workflow in workflow_status[:5]:  # Show top 5
                wf_id = workflow.get('workflow_id', 'N/A')
                wf_type = workflow.get('type', 'N/A')
                state = workflow.get('state', 'unknown')
                step = workflow.get('current_step', 'N/A')
                markdown += f"| {wf_id} | {wf_type} | {state} | {step} |\n"
        else:
            markdown += "*No active workflows*\n"
        markdown += "\n"

        # Financial Tracking
        markdown += "## Financial Tracking\n\n"
        markdown += f"- **Pending Invoices:** {financial_summary.get('pending_invoices', 0)}\n"
        markdown += f"- **Paid Invoices:** {financial_summary.get('paid_invoices', 0)}\n"
        markdown += f"- **Total Expenses:** ${financial_summary.get('total_expenses', 0):,.2f}\n"

        if 'budget_status' in financial_summary:
            budget = financial_summary['budget_status']
            markdown += f"- **Budget:** ${budget.get('total_budget', 0):,.2f}\n"
            markdown += f"- **Spent:** ${budget.get('spent', 0):,.2f} ({budget.get('percentage', 0)}%)\n"
            markdown += f"- **Remaining:** ${budget.get('remaining', 0):,.2f}\n"
        markdown += "\n"

        # Recent Activity
        markdown += "## Recent Activity\n\n"
        if recent_activity:
            for activity in recent_activity[:10]:  # Show last 10
                timestamp = activity.get('timestamp', '')
                action = activity.get('action', 'Unknown action')
                markdown += f"- **{timestamp}** - {action}\n"
        else:
            markdown += "*No recent activity*\n"
        markdown += "\n"

        # System Status
        markdown += "## System Status\n\n"
        if 'watchers' in system_status:
            markdown += "**Watchers:**\n"
            for watcher, status in system_status['watchers'].items():
                markdown += f"- {watcher}: {status}\n"
        elif 'email_watcher' in system_status:
            markdown += f"- Email Watcher: {system_status.get('email_watcher', 'unknown')}\n"
            markdown += f"- WhatsApp Watcher: {system_status.get('whatsapp_watcher', 'unknown')}\n"
            markdown += f"- LinkedIn Watcher: {system_status.get('linkedin_watcher', 'unknown')}\n"
            markdown += f"- File Watcher: {system_status.get('file_watcher', 'unknown')}\n"

        markdown += f"\n**Database:** {system_status.get('database', 'unknown')}\n"
        markdown += f"**Last Backup:** {system_status.get('last_backup', 'N/A')}\n"
        markdown += "\n"

        markdown += "---\n\n"
        markdown += "*Generated by AI Employee Silver Tier*\n"

        return markdown

    def get_platform_summary(self) -> Dict[str, int]:
        """Get multi-platform summary counts.

        Returns:
            Dictionary mapping platform to count
        """
        # Placeholder - would query database in production
        return {
            'email': 0,
            'whatsapp': 0,
            'linkedin': 0,
            'files': 0
        }

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending approvals.

        Returns:
            List of pending approval dictionaries
        """
        # Return mock data for testing
        return self.mock_approvals

    def get_active_plans(self) -> List[Dict[str, Any]]:
        """Get active plans.

        Returns:
            List of active plan dictionaries
        """
        # Return mock data for testing
        return self.mock_plans

    def get_workflow_status(self) -> List[Dict[str, Any]]:
        """Get workflow status.

        Returns:
            List of workflow status dictionaries
        """
        # Return mock data for testing
        return self.mock_workflows

    def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary.

        Returns:
            Financial summary dictionary
        """
        # Placeholder - would query database in production
        return {
            'pending_invoices': 0,
            'paid_invoices': 0,
            'total_expenses': 0,
            'budget_status': {
                'total_budget': 5000,
                'spent': 0,
                'remaining': 5000,
                'percentage': 0
            }
        }

    def get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent activity (last 10 items).

        Returns:
            List of activity dictionaries
        """
        # Return last 10 activities
        return self.mock_activities[-10:]

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status.

        Returns:
            System status dictionary
        """
        # Placeholder - would check actual system status in production
        return {
            'watchers': {
                'email': 'running',
                'whatsapp': 'running',
                'linkedin': 'running',
                'files': 'running'
            },
            'database': 'connected',
            'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def update_on_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update dashboard on event.

        Args:
            event_type: Type of event
            event_data: Event data

        Returns:
            Result dictionary
        """
        try:
            # Log activity
            self._add_mock_activity({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'action': f"{event_type}: {event_data.get('source', 'unknown')}"
            })

            # Regenerate dashboard
            return self.generate_dashboard()

        except Exception as e:
            logger.error(f"Error updating dashboard on event: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def scheduled_update(self) -> Dict[str, Any]:
        """Scheduled dashboard update (every 60s).

        Returns:
            Result dictionary
        """
        return self.generate_dashboard()

    # Mock data methods for testing
    def _add_mock_approval(self, approval: Dict[str, Any]):
        """Add mock approval for testing."""
        self.mock_approvals.append(approval)

    def _add_mock_plan(self, plan: Dict[str, Any]):
        """Add mock plan for testing."""
        self.mock_plans.append(plan)

    def _add_mock_workflow(self, workflow: Dict[str, Any]):
        """Add mock workflow for testing."""
        self.mock_workflows.append(workflow)

    def _add_mock_activity(self, activity: Dict[str, Any]):
        """Add mock activity for testing."""
        self.mock_activities.append(activity)
