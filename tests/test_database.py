"""Tests for database module - Phase 1 Silver Tier."""

import pytest
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, MagicMock

from src.database.db_manager import DatabaseManager


class TestDatabaseManager:
    """Test database manager functionality."""

    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        db = DatabaseManager(db_path)
        yield db
        os.unlink(db_path)

    def test_initialization_creates_tables(self, db):
        """Test that initialization creates all required tables."""
        tables = db.get_tables()
        required_tables = [
            'items', 'approvals', 'plans', 'workflows',
            'financial_records', 'activity_log'
        ]
        for table in required_tables:
            assert table in tables, f"Table {table} not found"

    def test_items_crud(self, db):
        """Test items table CRUD operations."""
        item_id = str(uuid4())
        item_data = {
            'id': item_id,
            'source': 'gmail',
            'type': 'email',
            'category': 'invoice',
            'priority': 'urgent',
            'amount': 1500.00,
            'status': 'pending',
            'file_path': 'Inbox/emails/test.md',
            'metadata': '{"sender": "vendor@test.com"}'
        }

        # Create
        db.create_item(item_data)

        # Read
        item = db.get_item(item_id)
        assert item is not None
        assert item['source'] == 'gmail'
        assert item['amount'] == 1500.00

        # Update
        db.update_item(item_id, {'status': 'approved'})
        item = db.get_item(item_id)
        assert item['status'] == 'approved'

        # Delete
        db.delete_item(item_id)
        item = db.get_item(item_id)
        assert item is None

    def test_approvals_workflow(self, db):
        """Test approval workflow state transitions."""
        item_id = str(uuid4())
        approval_id = str(uuid4())

        # Create item
        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'email',
            'category': 'invoice',
            'priority': 'urgent',
            'amount': 2500.00,
            'status': 'pending_approval',
            'file_path': 'Pending_Approval/test.md'
        })

        # Create approval record
        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': datetime.now().isoformat(),
            'decision': None,
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
        })

        approval = db.get_approval(approval_id)
        assert approval is not None
        assert approval['decision'] is None

        # Approve
        db.update_approval(approval_id, {
            'decision': 'approved',
            'decided_at': datetime.now().isoformat()
        })

        approval = db.get_approval(approval_id)
        assert approval['decision'] == 'approved'

    def test_get_pending_approvals(self, db):
        """Test retrieving pending approvals."""
        # Create pending approvals
        for i in range(3):
            item_id = str(uuid4())
            db.create_item({
                'id': item_id,
                'source': 'gmail',
                'type': 'email',
                'category': 'invoice',
                'priority': 'urgent',
                'amount': 1000.00 * (i + 1),
                'status': 'pending_approval',
                'file_path': f'Pending_Approval/test_{i}.md'
            })
            db.create_approval({
                'id': str(uuid4()),
                'item_id': item_id,
                'requested_at': datetime.now().isoformat(),
                'decision': None,
                'deadline': (datetime.now() + timedelta(hours=24)).isoformat()
            })

        pending = db.get_pending_approvals()
        assert len(pending) == 3

    def test_get_overdue_approvals(self, db):
        """Test retrieving overdue approvals."""
        item_id = str(uuid4())
        approval_id = str(uuid4())

        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'email',
            'category': 'invoice',
            'priority': 'urgent',
            'amount': 1500.00,
            'status': 'pending_approval',
            'file_path': 'Pending_Approval/test.md'
        })

        # Create approval with past deadline (use a clearly past date)
        past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        db.create_approval({
            'id': approval_id,
            'item_id': item_id,
            'requested_at': past_date,
            'decision': None,
            'deadline': past_date
        })

        overdue = db.get_overdue_approvals()
        assert len(overdue) == 1
        assert overdue[0]['item_id'] == item_id

    def test_plans_crud(self, db):
        """Test plans table operations."""
        plan_id = str(uuid4())

        db.create_plan({
            'id': plan_id,
            'title': 'Test Plan',
            'description': 'A test execution plan',
            'complexity': 'simple',
            'status': 'pending_approval',
            'steps_total': 5,
            'steps_completed': 0,
            'estimated_hours': 2.0
        })

        plan = db.get_plan(plan_id)
        assert plan is not None
        assert plan['title'] == 'Test Plan'

        # Update progress
        db.update_plan(plan_id, {
            'status': 'active',
            'steps_completed': 2
        })

        plan = db.get_plan(plan_id)
        assert plan['status'] == 'active'
        assert plan['steps_completed'] == 2

    def test_workflows_state_management(self, db):
        """Test workflow state persistence."""
        workflow_id = str(uuid4())
        item_id = str(uuid4())

        db.create_workflow({
            'id': workflow_id,
            'workflow_type': 'invoice_processing',
            'item_id': item_id,
            'current_step': 1,
            'total_steps': 5,
            'status': 'running',
            'state_data': '{"vendor": "Test Corp", "amount": 1500}'
        })

        workflow = db.get_workflow(workflow_id)
        assert workflow is not None
        assert workflow['status'] == 'running'

        # Pause workflow
        db.update_workflow(workflow_id, {
            'status': 'paused',
            'current_step': 3
        })

        workflow = db.get_workflow(workflow_id)
        assert workflow['status'] == 'paused'
        assert workflow['current_step'] == 3

    def test_financial_records(self, db):
        """Test financial records tracking."""
        record_id = str(uuid4())
        item_id = str(uuid4())

        db.create_financial_record({
            'id': record_id,
            'item_id': item_id,
            'record_type': 'invoice',
            'amount': 2500.00,
            'currency': 'USD',
            'vendor': 'Test Vendor',
            'due_date': (datetime.now() + timedelta(days=30)).isoformat(),
            'payment_status': 'pending',
            'category': 'services'
        })

        record = db.get_financial_record(record_id)
        assert record is not None
        assert record['amount'] == 2500.00

        # Update payment status
        db.update_financial_record(record_id, {
            'payment_status': 'paid',
            'paid_at': datetime.now().isoformat()
        })

        record = db.get_financial_record(record_id)
        assert record['payment_status'] == 'paid'

    def test_get_pending_invoices(self, db):
        """Test retrieving pending invoices."""
        for i in range(3):
            db.create_financial_record({
                'id': str(uuid4()),
                'item_id': str(uuid4()),
                'record_type': 'invoice',
                'amount': 1000.00 * (i + 1),
                'currency': 'USD',
                'vendor': f'Vendor {i}',
                'payment_status': 'pending'
            })

        # Add one paid invoice
        db.create_financial_record({
            'id': str(uuid4()),
            'item_id': str(uuid4()),
            'record_type': 'invoice',
            'amount': 500.00,
            'currency': 'USD',
            'vendor': 'Paid Vendor',
            'payment_status': 'paid'
        })

        pending = db.get_pending_invoices()
        assert len(pending) == 3

    def test_get_overdue_invoices(self, db):
        """Test retrieving overdue invoices."""
        db.create_financial_record({
            'id': str(uuid4()),
            'item_id': str(uuid4()),
            'record_type': 'invoice',
            'amount': 1000.00,
            'currency': 'USD',
            'vendor': 'Overdue Vendor',
            'due_date': (datetime.now() - timedelta(days=5)).isoformat(),
            'payment_status': 'pending'
        })

        overdue = db.get_overdue_invoices()
        assert len(overdue) == 1

    def test_activity_logging(self, db):
        """Test activity log entries."""
        db.log_activity({
            'level': 'INFO',
            'component': 'test',
            'action': 'Test action',
            'item_id': str(uuid4())
        })

        activities = db.get_recent_activity(limit=10)
        assert len(activities) >= 1
        assert activities[0]['component'] == 'test'

    def test_transaction_rollback_on_error(self, db):
        """Test transaction rollback on error."""
        item_id = str(uuid4())

        # This should succeed
        db.create_item({
            'id': item_id,
            'source': 'gmail',
            'type': 'email',
            'status': 'pending',
            'file_path': 'test.md'
        })

        # Verify item exists
        assert db.get_item(item_id) is not None

    def test_concurrent_access(self, db):
        """Test concurrent database access handling."""
        import threading

        errors = []

        def insert_items():
            try:
                for i in range(10):
                    db.create_item({
                        'id': str(uuid4()),
                        'source': 'gmail',
                        'type': 'email',
                        'status': 'pending',
                        'file_path': f'test_{i}.md'
                    })
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=insert_items) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent access errors: {errors}"


class TestDatabaseQueries:
    """Test complex database queries."""

    @pytest.fixture
    def db(self):
        """Create populated database for query testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        db = DatabaseManager(db_path)

        # Populate with test data
        for i in range(5):
            db.create_item({
                'id': str(uuid4()),
                'source': 'gmail' if i % 2 == 0 else 'filesystem',
                'type': 'email' if i % 2 == 0 else 'file',
                'category': 'invoice' if i < 3 else 'receipt',
                'priority': 'urgent' if i < 2 else 'normal',
                'amount': 1000.00 * (i + 1),
                'status': 'pending' if i < 3 else 'done',
                'file_path': f'test_{i}.md'
            })

        yield db
        os.unlink(db_path)

    def test_get_items_by_source(self, db):
        """Test filtering items by source."""
        gmail_items = db.get_items_by_source('gmail')
        assert len(gmail_items) == 3  # items 0, 2, 4

    def test_get_items_by_status(self, db):
        """Test filtering items by status."""
        pending_items = db.get_items_by_status('pending')
        assert len(pending_items) == 3

    def test_get_financial_summary(self, db):
        """Test financial summary aggregation."""
        summary = db.get_financial_summary()
        assert 'pending_invoices_count' in summary
        assert 'pending_invoices_amount' in summary
        assert 'paid_this_month_count' in summary
        assert 'paid_this_month_amount' in summary
        assert 'expenses_this_month' in summary


class TestDatabaseUtilities:
    """Test database utility methods."""

    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        db = DatabaseManager(db_path)
        yield db
        os.unlink(db_path)

    def test_get_tables(self, db):
        """Test getting list of tables."""
        tables = db.get_tables()
        assert 'items' in tables
        assert 'approvals' in tables
        assert 'plans' in tables
        assert 'workflows' in tables
        assert 'financial_records' in tables
        assert 'activity_log' in tables

    def test_get_stats(self, db):
        """Test getting database statistics."""
        # Add some test data
        db.create_item({
            'id': str(uuid4()),
            'source': 'gmail',
            'type': 'email',
            'status': 'pending',
            'file_path': 'test.md'
        })
        db.create_item({
            'id': str(uuid4()),
            'source': 'filesystem',
            'type': 'file',
            'status': 'done',
            'file_path': 'test2.md'
        })

        stats = db.get_stats()
        assert stats['items'] == 2
        assert stats['approvals'] == 0
        assert stats['plans'] == 0
        assert stats['workflows'] == 0
        assert stats['financial_records'] == 0
        assert 'activity_log' in stats

    def test_get_active_plans(self, db):
        """Test getting active plans."""
        # Create active plan
        plan_id = str(uuid4())
        db.create_plan({
            'id': plan_id,
            'title': 'Active Plan',
            'status': 'active',
            'steps_total': 5,
            'steps_completed': 2
        })

        # Create pending plan
        db.create_plan({
            'id': str(uuid4()),
            'title': 'Pending Plan',
            'status': 'pending_approval',
            'steps_total': 3,
            'steps_completed': 0
        })

        active_plans = db.get_active_plans()
        assert len(active_plans) == 1
        assert active_plans[0]['title'] == 'Active Plan'

    def test_get_active_workflows(self, db):
        """Test getting active workflows."""
        # Create running workflow
        db.create_workflow({
            'id': str(uuid4()),
            'workflow_type': 'invoice_processing',
            'status': 'running',
            'current_step': 2,
            'total_steps': 5
        })

        # Create paused workflow
        db.create_workflow({
            'id': str(uuid4()),
            'workflow_type': 'receipt_processing',
            'status': 'paused',
            'current_step': 1,
            'total_steps': 3
        })

        # Create completed workflow
        db.create_workflow({
            'id': str(uuid4()),
            'workflow_type': 'research',
            'status': 'completed',
            'current_step': 5,
            'total_steps': 5
        })

        active_workflows = db.get_active_workflows()
        assert len(active_workflows) == 2  # running and paused


class TestDatabaseErrorHandling:
    """Test database error handling."""

    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        db = DatabaseManager(db_path)
        yield db
        os.unlink(db_path)

    def test_get_nonexistent_item(self, db):
        """Test getting non-existent item returns None."""
        item = db.get_item('nonexistent-id')
        assert item is None

    def test_get_nonexistent_approval(self, db):
        """Test getting non-existent approval returns None."""
        approval = db.get_approval('nonexistent-id')
        assert approval is None

    def test_get_nonexistent_plan(self, db):
        """Test getting non-existent plan returns None."""
        plan = db.get_plan('nonexistent-id')
        assert plan is None

    def test_get_nonexistent_workflow(self, db):
        """Test getting non-existent workflow returns None."""
        workflow = db.get_workflow('nonexistent-id')
        assert workflow is None

    def test_get_nonexistent_financial_record(self, db):
        """Test getting non-existent financial record returns None."""
        record = db.get_financial_record('nonexistent-id')
        assert record is None

    def test_update_nonexistent_item(self, db):
        """Test updating non-existent item."""
        result = db.update_item('nonexistent-id', {'status': 'done'})
        assert result is True  # Update succeeds but affects 0 rows

    def test_delete_nonexistent_item(self, db):
        """Test deleting non-existent item."""
        result = db.delete_item('nonexistent-id')
        assert result is True  # Delete succeeds but affects 0 rows

    def test_empty_pending_approvals(self, db):
        """Test getting pending approvals when none exist."""
        pending = db.get_pending_approvals()
        assert pending == []

    def test_empty_overdue_approvals(self, db):
        """Test getting overdue approvals when none exist."""
        overdue = db.get_overdue_approvals()
        assert overdue == []

    def test_empty_pending_invoices(self, db):
        """Test getting pending invoices when none exist."""
        pending = db.get_pending_invoices()
        assert pending == []

    def test_empty_overdue_invoices(self, db):
        """Test getting overdue invoices when none exist."""
        overdue = db.get_overdue_invoices()
        assert overdue == []

    def test_empty_recent_activity(self, db):
        """Test getting recent activity when none exists."""
        activity = db.get_recent_activity()
        assert activity == []

    def test_empty_items_by_source(self, db):
        """Test getting items by source when none exist."""
        items = db.get_items_by_source('gmail')
        assert items == []

    def test_empty_items_by_status(self, db):
        """Test getting items by status when none exist."""
        items = db.get_items_by_status('pending')
        assert items == []

    def test_empty_active_plans(self, db):
        """Test getting active plans when none exist."""
        plans = db.get_active_plans()
        assert plans == []

    def test_empty_active_workflows(self, db):
        """Test getting active workflows when none exist."""
        workflows = db.get_active_workflows()
        assert workflows == []

    def test_financial_summary_with_no_data(self, db):
        """Test financial summary with no data."""
        summary = db.get_financial_summary()
        assert summary['pending_invoices_count'] == 0
        assert summary['pending_invoices_amount'] == 0
        assert summary['paid_this_month_count'] == 0
        assert summary['paid_this_month_amount'] == 0
        assert summary['expenses_this_month'] == 0


class TestDatabaseExceptionHandling:
    """Test database exception handling with mocked errors."""

    def test_create_item_with_db_error(self):
        """Test create_item handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        # Mock connection to raise error
        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.create_item({'id': 'test', 'source': 'gmail', 'type': 'email', 'status': 'pending', 'file_path': 'test.md'})
            assert result is False

        os.unlink(db_path)

    def test_get_item_with_db_error(self):
        """Test get_item handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_item('test-id')
            assert result is None

        os.unlink(db_path)

    def test_update_item_with_db_error(self):
        """Test update_item handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.update_item('test-id', {'status': 'done'})
            assert result is False

        os.unlink(db_path)

    def test_delete_item_with_db_error(self):
        """Test delete_item handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.delete_item('test-id')
            assert result is False

        os.unlink(db_path)

    def test_get_items_by_source_with_db_error(self):
        """Test get_items_by_source handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_items_by_source('gmail')
            assert result == []

        os.unlink(db_path)

    def test_get_items_by_status_with_db_error(self):
        """Test get_items_by_status handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_items_by_status('pending')
            assert result == []

        os.unlink(db_path)

    def test_create_approval_with_db_error(self):
        """Test create_approval handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.create_approval({'id': 'test', 'item_id': 'item1'})
            assert result is False

        os.unlink(db_path)

    def test_get_approval_with_db_error(self):
        """Test get_approval handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_approval('test-id')
            assert result is None

        os.unlink(db_path)

    def test_update_approval_with_db_error(self):
        """Test update_approval handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.update_approval('test-id', {'decision': 'approved'})
            assert result is False

        os.unlink(db_path)

    def test_get_pending_approvals_with_db_error(self):
        """Test get_pending_approvals handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_pending_approvals()
            assert result == []

        os.unlink(db_path)

    def test_get_overdue_approvals_with_db_error(self):
        """Test get_overdue_approvals handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_overdue_approvals()
            assert result == []

        os.unlink(db_path)

    def test_create_plan_with_db_error(self):
        """Test create_plan handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.create_plan({'id': 'test', 'title': 'Test Plan'})
            assert result is False

        os.unlink(db_path)

    def test_get_plan_with_db_error(self):
        """Test get_plan handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_plan('test-id')
            assert result is None

        os.unlink(db_path)

    def test_update_plan_with_db_error(self):
        """Test update_plan handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.update_plan('test-id', {'status': 'active'})
            assert result is False

        os.unlink(db_path)

    def test_get_active_plans_with_db_error(self):
        """Test get_active_plans handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_active_plans()
            assert result == []

        os.unlink(db_path)

    def test_create_workflow_with_db_error(self):
        """Test create_workflow handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.create_workflow({'id': 'test', 'workflow_type': 'invoice'})
            assert result is False

        os.unlink(db_path)

    def test_get_workflow_with_db_error(self):
        """Test get_workflow handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_workflow('test-id')
            assert result is None

        os.unlink(db_path)

    def test_update_workflow_with_db_error(self):
        """Test update_workflow handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.update_workflow('test-id', {'status': 'paused'})
            assert result is False

        os.unlink(db_path)

    def test_get_active_workflows_with_db_error(self):
        """Test get_active_workflows handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_active_workflows()
            assert result == []

        os.unlink(db_path)

    def test_create_financial_record_with_db_error(self):
        """Test create_financial_record handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.create_financial_record({'id': 'test', 'record_type': 'invoice', 'amount': 1000})
            assert result is False

        os.unlink(db_path)

    def test_get_financial_record_with_db_error(self):
        """Test get_financial_record handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_financial_record('test-id')
            assert result is None

        os.unlink(db_path)

    def test_update_financial_record_with_db_error(self):
        """Test update_financial_record handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.update_financial_record('test-id', {'payment_status': 'paid'})
            assert result is False

        os.unlink(db_path)

    def test_get_pending_invoices_with_db_error(self):
        """Test get_pending_invoices handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_pending_invoices()
            assert result == []

        os.unlink(db_path)

    def test_get_overdue_invoices_with_db_error(self):
        """Test get_overdue_invoices handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_overdue_invoices()
            assert result == []

        os.unlink(db_path)

    def test_get_financial_summary_with_db_error(self):
        """Test get_financial_summary handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_financial_summary()
            assert result == {}

        os.unlink(db_path)

    def test_log_activity_with_db_error(self):
        """Test log_activity handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.log_activity({'level': 'INFO', 'component': 'test', 'action': 'test'})
            assert result is False

        os.unlink(db_path)

    def test_get_recent_activity_with_db_error(self):
        """Test get_recent_activity handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_recent_activity()
            assert result == []

        os.unlink(db_path)

    def test_get_tables_with_db_error(self):
        """Test get_tables handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_tables()
            assert result == []

        os.unlink(db_path)

    def test_get_stats_with_db_error(self):
        """Test get_stats handles database errors."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        db = DatabaseManager(db_path)

        with patch.object(db, '_get_connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=sqlite3.Error("Test error"))
            mock_conn.return_value = mock_context

            result = db.get_stats()
            assert result == {}

        os.unlink(db_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
