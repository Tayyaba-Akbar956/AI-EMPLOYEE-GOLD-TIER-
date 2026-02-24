"""Tests for approval manager - Phase 2 Silver Tier."""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

from src.approvals.approval_manager import ApprovalManager
from src.database.db_manager import DatabaseManager


class TestApprovalDetection:
    """Test approval requirement detection."""

    @pytest.fixture
    def approval_manager(self):
        """Create approval manager with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        with tempfile.TemporaryDirectory() as vault_dir:
            db = DatabaseManager(db_path)
            manager = ApprovalManager(db, vault_dir)
            yield manager

        os.unlink(db_path)

    def test_high_value_invoice_requires_approval(self, approval_manager):
        """Test that invoices >= $1000 require approval."""
        item = {
            'type': 'invoice',
            'amount': 1500.00,
            'category': 'invoice',
            'content': 'Invoice for services'
        }

        result = approval_manager.should_require_approval(item)

        assert result['requires_approval'] is True
        assert 'threshold' in result['reason'].lower()
        assert result['priority'] == 'high'

    def test_low_value_invoice_no_approval(self, approval_manager):
        """Test that invoices < $1000 don't require approval."""
        item = {
            'type': 'invoice',
            'amount': 500.00,
            'category': 'invoice',
            'content': 'Small invoice'
        }

        result = approval_manager.should_require_approval(item)

        assert result['requires_approval'] is False

    def test_contract_always_requires_approval(self, approval_manager):
        """Test that contracts always require approval."""
        item = {
            'type': 'contract',
            'amount': 0,
            'category': 'contract',
            'content': 'Service agreement'
        }

        result = approval_manager.should_require_approval(item)

        assert result['requires_approval'] is True
        assert 'contract' in result['reason'].lower()
        assert result['priority'] == 'high'

    def test_approval_required_keyword(self, approval_manager):
        """Test keyword 'approval required' triggers approval."""
        item = {
            'type': 'email',
            'amount': 0,
            'category': 'email',
            'content': 'This needs approval required before proceeding'
        }

        result = approval_manager.should_require_approval(item)

        assert result['requires_approval'] is True
        assert 'keyword' in result['reason'].lower()

    def test_threshold_exactly_1000(self, approval_manager):
        """Test that exactly $1000 requires approval."""
        item = {
            'type': 'invoice',
            'amount': 1000.00,
            'category': 'invoice',
            'content': 'Invoice'
        }

        result = approval_manager.should_require_approval(item)

        assert result['requires_approval'] is True

    def test_deadline_calculated(self, approval_manager):
        """Test that deadline is 24 hours from now."""
        item = {
            'type': 'invoice',
            'amount': 2000.00,
            'category': 'invoice',
            'content': 'Invoice'
        }

        result = approval_manager.should_require_approval(item)

        assert 'deadline' in result
        # Deadline should be approximately 24 hours from now
        deadline = datetime.fromisoformat(result['deadline'])
        expected = datetime.now() + timedelta(hours=24)
        diff = abs((deadline - expected).total_seconds())
        assert diff < 60  # Within 1 minute


class TestApprovalCardGeneration:
    """Test approval card generation."""

    @pytest.fixture
    def approval_manager(self):
        """Create approval manager with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        with tempfile.TemporaryDirectory() as vault_dir:
            db = DatabaseManager(db_path)
            manager = ApprovalManager(db, vault_dir)
            yield manager

        os.unlink(db_path)

    def test_approval_card_has_header(self, approval_manager):
        """Test approval card has clear header."""
        item = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 1500.00,
            'category': 'invoice',
            'vendor': 'Acme Corp',
            'content': 'Invoice for services',
            'file_path': 'test.md'
        }

        card = approval_manager.generate_approval_card(item)

        assert 'APPROVAL REQUIRED' in card
        assert card.startswith('#')

    def test_approval_card_includes_item_details(self, approval_manager):
        """Test card includes all item details."""
        item = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 2500.00,
            'category': 'invoice',
            'vendor': 'Test Vendor',
            'content': 'Invoice content',
            'file_path': 'test.md'
        }

        card = approval_manager.generate_approval_card(item)

        assert 'invoice' in card.lower()
        assert '2500' in card or '$2,500' in card
        assert 'Test Vendor' in card

    def test_approval_card_includes_deadline(self, approval_manager):
        """Test card includes deadline information."""
        item = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 1500.00,
            'category': 'invoice',
            'content': 'Invoice',
            'file_path': 'test.md'
        }

        card = approval_manager.generate_approval_card(item)

        assert 'deadline' in card.lower() or 'expires' in card.lower()

    def test_approval_card_includes_decision_instructions(self, approval_manager):
        """Test card includes how to approve/reject."""
        item = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 1500.00,
            'category': 'invoice',
            'content': 'Invoice',
            'file_path': 'test.md'
        }

        card = approval_manager.generate_approval_card(item)

        assert 'approve' in card.lower()
        assert 'reject' in card.lower()

    def test_approval_card_has_unique_id(self, approval_manager):
        """Test each card has unique approval ID."""
        item1 = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 1500.00,
            'category': 'invoice',
            'content': 'Invoice 1',
            'file_path': 'test1.md'
        }

        item2 = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 2000.00,
            'category': 'invoice',
            'content': 'Invoice 2',
            'file_path': 'test2.md'
        }

        card1 = approval_manager.generate_approval_card(item1)
        card2 = approval_manager.generate_approval_card(item2)

        # Extract IDs from cards (assuming format like "Approval ID: xxx")
        assert 'approval' in card1.lower()
        assert 'approval' in card2.lower()
        assert card1 != card2


class TestApprovalProcessing:
    """Test approval decision processing."""

    @pytest.fixture
    def setup(self):
        """Create approval manager with temp database and vault."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        vault_dir = tempfile.mkdtemp()

        # Create folder structure
        os.makedirs(os.path.join(vault_dir, 'Pending_Approval', 'high_value'), exist_ok=True)
        os.makedirs(os.path.join(vault_dir, 'Approved'), exist_ok=True)
        os.makedirs(os.path.join(vault_dir, 'Rejected'), exist_ok=True)

        db = DatabaseManager(db_path)
        manager = ApprovalManager(db, vault_dir)

        yield manager, db, vault_dir

        os.unlink(db_path)
        shutil.rmtree(vault_dir)

    def test_approve_moves_file_to_approved(self, setup):
        """Test approving moves file to Approved folder."""
        manager, db, vault_dir = setup

        # Create test item and approval
        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'category': 'invoice',
            'amount': 1500.00,
            'status': 'pending_approval',
            'file_path': 'Pending_Approval/high_value/test_invoice.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        # Create test file
        test_file = os.path.join(vault_dir, 'Pending_Approval', 'high_value', 'test_invoice.md')
        with open(test_file, 'w') as f:
            f.write('Test invoice content')

        # Approve
        result = manager.process_approval(approval_id, 'approved')

        assert result['success'] is True
        assert result['decision'] == 'approved'

        # Check file moved
        approved_file = os.path.join(vault_dir, 'Approved', 'test_invoice.md')
        assert os.path.exists(approved_file)
        assert not os.path.exists(test_file)

    def test_reject_moves_file_to_rejected(self, setup):
        """Test rejecting moves file to Rejected folder."""
        manager, db, vault_dir = setup

        # Create test item and approval
        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'category': 'invoice',
            'amount': 1500.00,
            'status': 'pending_approval',
            'file_path': 'Pending_Approval/high_value/test_invoice.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        # Create test file
        test_file = os.path.join(vault_dir, 'Pending_Approval', 'high_value', 'test_invoice.md')
        with open(test_file, 'w') as f:
            f.write('Test invoice content')

        # Reject
        result = manager.process_approval(approval_id, 'rejected', reason='Too expensive')

        assert result['success'] is True
        assert result['decision'] == 'rejected'

        # Check file moved
        rejected_file = os.path.join(vault_dir, 'Rejected', 'test_invoice.md')
        assert os.path.exists(rejected_file)
        assert not os.path.exists(test_file)

    def test_approval_updates_database(self, setup):
        """Test approval updates database record."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        # Approve
        manager.process_approval(approval_id, 'approved')

        # Check database
        approval = db.get_approval(approval_id)
        assert approval['decision'] == 'approved'
        assert approval['decided_at'] is not None

    def test_rejection_logs_reason(self, setup):
        """Test rejection reason is logged."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        # Reject with reason
        manager.process_approval(approval_id, 'rejected', reason='Budget exceeded')

        # Check reason logged
        approval = db.get_approval(approval_id)
        assert approval['reason'] == 'Budget exceeded'

    def test_duplicate_approval_rejected(self, setup):
        """Test cannot approve already decided item."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        # First approval
        manager.process_approval(approval_id, 'approved')

        # Try to approve again
        result = manager.process_approval(approval_id, 'approved')

        assert result['success'] is False
        assert 'already' in result['error'].lower()


class TestApprovalTimeouts:
    """Test approval timeout and auto-approval."""

    @pytest.fixture
    def setup(self):
        """Create approval manager with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        vault_dir = tempfile.mkdtemp()
        db = DatabaseManager(db_path)
        manager = ApprovalManager(db, vault_dir)

        yield manager, db, vault_dir

        os.unlink(db_path)
        shutil.rmtree(vault_dir)

    def test_check_timeouts_finds_overdue(self, setup):
        """Test timeout checker finds overdue approvals."""
        manager, db, vault_dir = setup

        # Create overdue approval
        item_id = str(uuid4())
        approval_id = str(uuid4())

        past_time = (datetime.now() - timedelta(hours=25)).isoformat()

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': past_time,
            'deadline': past_time,
            'decision': None
        })

        # Check timeouts
        overdue = manager.check_approval_timeouts()

        assert len(overdue) == 1
        assert overdue[0] == approval_id

    def test_auto_approve_on_timeout(self, setup):
        """Test auto-approval when timeout occurs."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        past_time = (datetime.now() - timedelta(hours=25)).isoformat()

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': past_time,
            'deadline': past_time,
            'decision': None
        })

        # Process timeouts
        manager.check_approval_timeouts()

        # Check auto-approved
        approval = db.get_approval(approval_id)
        assert approval['decision'] == 'approved'
        assert approval['auto_decided'] == 1

    def test_no_timeout_for_recent_approvals(self, setup):
        """Test recent approvals not timed out."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat(),
            'decision': None
        })

        # Check timeouts
        overdue = manager.check_approval_timeouts()

        assert len(overdue) == 0


class TestApprovalReminders:
    """Test approval reminder system."""

    @pytest.fixture
    def setup(self):
        """Create approval manager with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        vault_dir = tempfile.mkdtemp()
        db = DatabaseManager(db_path)
        manager = ApprovalManager(db, vault_dir)

        yield manager, db, vault_dir

        os.unlink(db_path)
        shutil.rmtree(vault_dir)

    def test_send_reminder_after_4_hours(self, setup):
        """Test reminder sent after 4 hours."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        # Create approval 5 hours ago
        past_time = (datetime.now() - timedelta(hours=5)).isoformat()

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': past_time,
            'deadline': (datetime.now() + timedelta(hours=19)).isoformat(),
            'decision': None,
            'reminder_sent': 0
        })

        # Send reminders
        reminded = manager.send_approval_reminders()

        assert len(reminded) == 1
        assert reminded[0] == approval_id

        # Check reminder flag set
        approval = db.get_approval(approval_id)
        assert approval['reminder_sent'] == 1

    def test_no_duplicate_reminders(self, setup):
        """Test reminder not sent twice."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        past_time = (datetime.now() - timedelta(hours=5)).isoformat()

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'test.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': past_time,
            'deadline': (datetime.now() + timedelta(hours=19)).isoformat(),
            'decision': None,
            'reminder_sent': 1  # Already sent
        })

        # Try to send reminders
        reminded = manager.send_approval_reminders()

        assert len(reminded) == 0


class TestApprovalErrorHandling:
    """Test error handling in approval manager."""

    @pytest.fixture
    def setup(self):
        """Create approval manager with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        vault_dir = tempfile.mkdtemp()
        db = DatabaseManager(db_path)
        manager = ApprovalManager(db, vault_dir)

        yield manager, db, vault_dir

        os.unlink(db_path)
        shutil.rmtree(vault_dir)

    def test_process_approval_invalid_id(self, setup):
        """Test processing approval with invalid ID."""
        manager, db, vault_dir = setup

        result = manager.process_approval('invalid-id', 'approved')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_process_approval_without_file(self, setup):
        """Test processing approval when file doesn't exist."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': 'nonexistent.md'
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        # Should not crash even if file doesn't exist
        result = manager.process_approval(approval_id, 'approved')

        assert result['success'] is True

    def test_check_timeouts_with_no_overdue(self, setup):
        """Test timeout check with no overdue approvals."""
        manager, db, vault_dir = setup

        overdue = manager.check_approval_timeouts()

        assert overdue == []

    def test_send_reminders_with_no_pending(self, setup):
        """Test reminder sending with no pending approvals."""
        manager, db, vault_dir = setup

        reminded = manager.send_approval_reminders()

        assert reminded == []

    def test_custom_config_overrides(self):
        """Test custom configuration overrides."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        with tempfile.TemporaryDirectory() as vault_dir:
            db = DatabaseManager(db_path)

            custom_config = {
                'approval_threshold': 2000.00,
                'approval_timeout_hours': 48,
                'reminder_hours': 8
            }

            manager = ApprovalManager(db, vault_dir, config=custom_config)

            assert manager.config['approval_threshold'] == 2000.00
            assert manager.config['approval_timeout_hours'] == 48
            assert manager.config['reminder_hours'] == 8

        os.unlink(db_path)

    def test_approval_with_no_amount(self, setup):
        """Test approval detection for items without amount."""
        manager, db, vault_dir = setup

        item = {
            'type': 'document',
            'category': 'document',
            'content': 'Regular document'
        }

        result = manager.should_require_approval(item)

        assert result['requires_approval'] is False

    def test_approval_card_without_amount(self, setup):
        """Test approval card generation without amount."""
        manager, db, vault_dir = setup

        item = {
            'id': str(uuid4()),
            'type': 'contract',
            'category': 'contract',
            'content': 'Service agreement',
            'file_path': 'test.md'
        }

        card = manager.generate_approval_card(item)

        assert 'APPROVAL REQUIRED' in card
        assert 'contract' in card.lower()

    def test_approval_card_with_high_value(self, setup):
        """Test approval card recommendation for high value items."""
        manager, db, vault_dir = setup

        item = {
            'id': str(uuid4()),
            'type': 'invoice',
            'amount': 10000.00,
            'category': 'invoice',
            'content': 'Large invoice',
            'file_path': 'test.md'
        }

        card = manager.generate_approval_card(item)

        assert 'HIGH VALUE' in card or 'high value' in card.lower()

    def test_process_approval_item_without_filepath(self, setup):
        """Test processing approval for item without file path."""
        manager, db, vault_dir = setup

        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'invoice',
            'status': 'pending_approval',
            'file_path': None
        })

        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        result = manager.process_approval(approval_id, 'approved')

        assert result['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
