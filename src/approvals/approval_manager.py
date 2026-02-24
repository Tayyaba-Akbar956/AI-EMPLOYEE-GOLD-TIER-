"""Approval Manager for AI Employee Silver Tier.

Manages approval workflow for high-value items, contracts, and items
requiring explicit user approval.
"""

import os
import shutil
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages approval workflow for high-value items.

    Handles threshold detection, approval card generation, decision processing,
    timeout management, and reminder system.
    """

    def __init__(self, db_manager, vault_path: str, config: Optional[Dict] = None):
        """Initialize approval manager.

        Args:
            db_manager: DatabaseManager instance
            vault_path: Path to AI_Employee_Vault
            config: Optional configuration overrides
        """
        self.db = db_manager
        self.vault_path = Path(vault_path)

        # Default configuration
        self.config = {
            'approval_threshold': 1000.00,
            'approval_timeout_hours': 24,
            'reminder_hours': 4,
            'auto_approve_on_timeout': True
        }

        if config:
            self.config.update(config)

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure required folders exist."""
        folders = [
            'Pending_Approval/high_value',
            'Pending_Approval/workflows',
            'Approved',
            'Rejected',
            'Logs/approvals'
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    def should_require_approval(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if item requires approval.

        Args:
            item: Item dictionary with type, amount, category, content

        Returns:
            Dictionary with:
                - requires_approval: bool
                - reason: str
                - priority: str (high/medium/low)
                - deadline: str (ISO format)
        """
        requires_approval = False
        reason = ""
        priority = "low"

        # Check if contract (always requires approval)
        if item.get('type') == 'contract' or item.get('category') == 'contract':
            requires_approval = True
            reason = "Contract detected - always requires approval"
            priority = "high"

        # Check amount threshold
        elif item.get('amount', 0) >= self.config['approval_threshold']:
            requires_approval = True
            reason = f"Amount ${item['amount']:.2f} exceeds threshold ${self.config['approval_threshold']:.2f}"
            priority = "high"

        # Check for approval keywords
        elif 'content' in item:
            content_lower = item['content'].lower()
            if 'approval required' in content_lower or 'needs approval' in content_lower:
                requires_approval = True
                reason = "Keyword 'approval required' detected in content"
                priority = "medium"

        # Calculate deadline
        deadline = datetime.now() + timedelta(hours=self.config['approval_timeout_hours'])

        return {
            'requires_approval': requires_approval,
            'reason': reason,
            'priority': priority,
            'deadline': deadline.isoformat()
        }

    def generate_approval_card(self, item: Dict[str, Any]) -> str:
        """Generate approval card markdown.

        Args:
            item: Item dictionary with details

        Returns:
            Markdown formatted approval card
        """
        approval_id = str(uuid4())

        # Calculate deadline
        deadline = datetime.now() + timedelta(hours=self.config['approval_timeout_hours'])
        deadline_str = deadline.strftime('%Y-%m-%d %H:%M:%S')

        # Format amount if present
        amount_str = ""
        if 'amount' in item and item['amount']:
            amount_str = f"**Amount:** ${item['amount']:,.2f}\n"

        # Get vendor/sender
        vendor = item.get('vendor', item.get('sender', 'Unknown'))

        # Build card
        card = f"""# APPROVAL REQUIRED

**Approval ID:** {approval_id}
**Item Type:** {item.get('type', 'Unknown')}
**Category:** {item.get('category', 'Unknown')}
{amount_str}**Vendor/Sender:** {vendor}
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Deadline:** {deadline_str} (Auto-approve after {self.config['approval_timeout_hours']} hours)

---

## Item Details

{item.get('content', 'No additional details available.')}

---

## Financial Impact

"""

        if 'amount' in item and item['amount']:
            card += f"- **This Item:** ${item['amount']:,.2f}\n"
            card += f"- **Approval Threshold:** ${self.config['approval_threshold']:,.2f}\n"
        else:
            card += "- No financial amount specified\n"

        card += """
---

## AI Recommendation

"""

        # Simple recommendation logic
        if item.get('type') == 'contract':
            card += "**REVIEW CAREFULLY** - Contract requires legal review before approval.\n"
        elif item.get('amount', 0) > 5000:
            card += "**HIGH VALUE** - Significant financial commitment. Verify vendor and terms.\n"
        else:
            card += "**STANDARD APPROVAL** - Item meets approval criteria. Review and approve if legitimate.\n"

        card += """
---

## How to Decide

### Option 1: Via Obsidian
- **Approve:** Move this file to `Approved/` folder
- **Reject:** Move this file to `Rejected/` folder

### Option 2: Via CLI
```bash
# Approve
python -m ai_employee approve {approval_id}

# Reject with reason
python -m ai_employee reject {approval_id} --reason "Your reason here"
```

---

**Note:** If no decision is made by the deadline, this item will be auto-approved.

*Generated by AI Employee Approval Manager*
"""

        return card.format(approval_id=approval_id)

    def process_approval(self, approval_id: str, decision: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Process approval decision.

        Args:
            approval_id: Unique approval ID
            decision: 'approved' or 'rejected'
            reason: Optional reason for rejection

        Returns:
            Dictionary with success status and details
        """
        try:
            # Get approval record
            approval = self.db.get_approval(approval_id)

            if not approval:
                return {
                    'success': False,
                    'error': f'Approval ID not found: {approval_id}'
                }

            # Check if already decided
            if approval['decision'] is not None:
                return {
                    'success': False,
                    'error': f'Already decided: {approval["decision"]} at {approval["decided_at"]}'
                }

            # Update approval record
            update_data = {
                'decision': decision,
                'decided_at': datetime.now().isoformat(),
                'auto_decided': 0
            }

            if reason:
                update_data['reason'] = reason

            self.db.update_approval(approval_id, update_data)

            # Get item details
            item = self.db.get_item(approval['item_id'])

            if item and item['file_path']:
                # Move file
                source_path = self.vault_path / item['file_path']

                if decision == 'approved':
                    dest_folder = self.vault_path / 'Approved'
                else:
                    dest_folder = self.vault_path / 'Rejected'

                if source_path.exists():
                    dest_path = dest_folder / source_path.name
                    shutil.move(str(source_path), str(dest_path))

                    # Update item file path
                    new_path = str(dest_path.relative_to(self.vault_path))
                    self.db.update_item(approval['item_id'], {
                        'file_path': new_path,
                        'status': decision
                    })

            # Log activity
            self.db.log_activity({
                'level': 'INFO',
                'component': 'approval-manager',
                'action': f'Approval {decision}: {approval_id}',
                'item_id': approval['item_id'],
                'details': reason or 'No reason provided'
            })

            logger.info(f"Approval {approval_id} {decision}")

            return {
                'success': True,
                'decision': decision,
                'approval_id': approval_id
            }

        except Exception as e:
            logger.error(f"Error processing approval {approval_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def check_approval_timeouts(self) -> List[str]:
        """Check for and process timed-out approvals.

        Returns:
            List of approval IDs that were auto-approved
        """
        auto_approved = []

        try:
            # Get overdue approvals
            overdue = self.db.get_overdue_approvals()

            for approval in overdue:
                if self.config['auto_approve_on_timeout']:
                    # Auto-approve
                    approval_id = approval['id']

                    self.db.update_approval(approval_id, {
                        'decision': 'approved',
                        'decided_at': datetime.now().isoformat(),
                        'auto_decided': 1,
                        'reason': f'Auto-approved after {self.config["approval_timeout_hours"]} hour timeout'
                    })

                    # Update item status
                    self.db.update_item(approval['item_id'], {
                        'status': 'approved'
                    })

                    # Log activity
                    self.db.log_activity({
                        'level': 'WARN',
                        'component': 'approval-manager',
                        'action': f'Auto-approved after timeout: {approval_id}',
                        'item_id': approval['item_id']
                    })

                    auto_approved.append(approval_id)
                    logger.warning(f"Auto-approved {approval_id} after timeout")

            return auto_approved

        except Exception as e:
            logger.error(f"Error checking approval timeouts: {e}")
            return []

    def send_approval_reminders(self) -> List[str]:
        """Send reminders for pending approvals.

        Returns:
            List of approval IDs that received reminders
        """
        reminded = []

        try:
            # Get pending approvals
            pending = self.db.get_pending_approvals()

            reminder_threshold = datetime.now() - timedelta(hours=self.config['reminder_hours'])

            for approval in pending:
                # Check if reminder needed
                if approval['reminder_sent']:
                    continue

                requested_at = datetime.fromisoformat(approval['requested_at'])

                if requested_at < reminder_threshold:
                    # Send reminder (update flag)
                    self.db.update_approval(approval['id'], {
                        'reminder_sent': 1
                    })

                    # Log activity
                    self.db.log_activity({
                        'level': 'INFO',
                        'component': 'approval-manager',
                        'action': f'Reminder sent for approval: {approval["id"]}',
                        'item_id': approval['item_id']
                    })

                    reminded.append(approval['id'])
                    logger.info(f"Reminder sent for approval {approval['id']}")

            return reminded

        except Exception as e:
            logger.error(f"Error sending approval reminders: {e}")
            return []
