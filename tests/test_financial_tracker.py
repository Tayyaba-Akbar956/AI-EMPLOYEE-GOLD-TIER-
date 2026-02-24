"""Tests for Financial Tracker - Phase 8 Silver Tier."""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from src.skills.financial_tracker import FinancialTracker


class TestInvoiceTracking:
    """Test invoice tracking."""

    @pytest.fixture
    def tracker(self):
        """Create financial tracker."""
        vault_dir = tempfile.mkdtemp()
        tracker = FinancialTracker(vault_dir)
        yield tracker
        shutil.rmtree(vault_dir)

    def test_add_invoice(self, tracker):
        """Test adding invoice."""
        invoice_data = {
            'amount': 1500,
            'vendor': 'Tech Supplies Inc',
            'due_date': '2026-03-01',
            'description': 'Office equipment'
        }
        result = tracker.add_invoice(invoice_data)

        assert result['success'] is True
        assert result['invoice_id'] is not None

    def test_get_invoice(self, tracker):
        """Test retrieving invoice."""
        invoice_data = {'amount': 1500, 'vendor': 'Tech Supplies Inc', 'due_date': '2026-03-01'}
        result = tracker.add_invoice(invoice_data)
        invoice_id = result['invoice_id']

        invoice = tracker.get_invoice(invoice_id)
        assert invoice is not None
        assert invoice['amount'] == 1500
        assert invoice['vendor'] == 'Tech Supplies Inc'

    def test_list_pending_invoices(self, tracker):
        """Test listing pending invoices."""
        tracker.add_invoice({'amount': 1500, 'vendor': 'Vendor A', 'due_date': '2026-03-01'})
        tracker.add_invoice({'amount': 2000, 'vendor': 'Vendor B', 'due_date': '2026-03-15'})

        pending = tracker.list_pending_invoices()
        assert len(pending) == 2

    def test_mark_invoice_paid(self, tracker):
        """Test marking invoice as paid."""
        result = tracker.add_invoice({'amount': 1500, 'vendor': 'Vendor A', 'due_date': '2026-03-01'})
        invoice_id = result['invoice_id']

        pay_result = tracker.mark_invoice_paid(invoice_id)
        assert pay_result['success'] is True

        invoice = tracker.get_invoice(invoice_id)
        assert invoice['status'] == 'paid'

    def test_detect_overdue_invoices(self, tracker):
        """Test detecting overdue invoices."""
        # Add invoice with past due date
        past_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        tracker.add_invoice({'amount': 1500, 'vendor': 'Vendor A', 'due_date': past_date})

        overdue = tracker.get_overdue_invoices()
        assert len(overdue) >= 1


class TestExpenseTracking:
    """Test expense tracking."""

    @pytest.fixture
    def tracker(self):
        """Create financial tracker."""
        vault_dir = tempfile.mkdtemp()
        tracker = FinancialTracker(vault_dir)
        yield tracker
        shutil.rmtree(vault_dir)

    def test_add_expense(self, tracker):
        """Test adding expense."""
        expense_data = {
            'amount': 50,
            'category': 'Meals',
            'payee': 'Restaurant',
            'date': '2026-02-18',
            'description': 'Team lunch'
        }
        result = tracker.add_expense(expense_data)

        assert result['success'] is True
        assert result['expense_id'] is not None

    def test_categorize_expense(self, tracker):
        """Test expense categorization."""
        expense_data = {'amount': 50, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'}
        result = tracker.add_expense(expense_data)

        expense = tracker.get_expense(result['expense_id'])
        assert expense['category'] == 'Meals'

    def test_list_expenses_by_category(self, tracker):
        """Test listing expenses by category."""
        tracker.add_expense({'amount': 50, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})
        tracker.add_expense({'amount': 30, 'category': 'Meals', 'payee': 'Cafe', 'date': '2026-02-18'})
        tracker.add_expense({'amount': 100, 'category': 'Travel', 'payee': 'Airline', 'date': '2026-02-18'})

        meals = tracker.list_expenses_by_category('Meals')
        assert len(meals) == 2

    def test_calculate_total_expenses(self, tracker):
        """Test calculating total expenses."""
        tracker.add_expense({'amount': 50, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})
        tracker.add_expense({'amount': 30, 'category': 'Meals', 'payee': 'Cafe', 'date': '2026-02-18'})

        total = tracker.calculate_total_expenses()
        assert total == 80


class TestBudgetTracking:
    """Test budget tracking."""

    @pytest.fixture
    def tracker(self):
        """Create financial tracker."""
        vault_dir = tempfile.mkdtemp()
        tracker = FinancialTracker(vault_dir)
        yield tracker
        shutil.rmtree(vault_dir)

    def test_set_monthly_budget(self, tracker):
        """Test setting monthly budget."""
        result = tracker.set_monthly_budget(5000)
        assert result['success'] is True

    def test_set_category_budget(self, tracker):
        """Test setting category budget."""
        result = tracker.set_category_budget('Meals', 500)
        assert result['success'] is True

    def test_check_budget_status(self, tracker):
        """Test checking budget status."""
        tracker.set_monthly_budget(5000)
        tracker.add_expense({'amount': 1000, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})

        status = tracker.get_budget_status()
        assert status['total_budget'] == 5000
        assert status['spent'] == 1000
        assert status['remaining'] == 4000
        assert status['percentage'] == 20

    def test_budget_alert_threshold(self, tracker):
        """Test budget alert at 80% threshold."""
        tracker.set_monthly_budget(1000)
        tracker.add_expense({'amount': 850, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})

        status = tracker.get_budget_status()
        assert status['alert'] is True
        assert status['percentage'] >= 80

    def test_budget_exceeded(self, tracker):
        """Test budget exceeded detection."""
        tracker.set_monthly_budget(1000)
        tracker.add_expense({'amount': 1100, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})

        status = tracker.get_budget_status()
        assert status['exceeded'] is True


class TestCategories:
    """Test expense categories."""

    @pytest.fixture
    def tracker(self):
        """Create financial tracker."""
        vault_dir = tempfile.mkdtemp()
        tracker = FinancialTracker(vault_dir)
        yield tracker
        shutil.rmtree(vault_dir)

    def test_default_categories(self, tracker):
        """Test default categories exist."""
        categories = tracker.get_categories()
        assert 'Meals' in categories
        assert 'Travel' in categories
        assert 'Supplies' in categories
        assert 'Software' in categories

    def test_add_custom_category(self, tracker):
        """Test adding custom category."""
        result = tracker.add_category('Marketing')
        assert result['success'] is True

        categories = tracker.get_categories()
        assert 'Marketing' in categories

    def test_uncategorized_expense(self, tracker):
        """Test uncategorized expense handling."""
        expense_data = {'amount': 50, 'category': 'Unknown', 'payee': 'Vendor', 'date': '2026-02-18'}
        result = tracker.add_expense(expense_data)

        expense = tracker.get_expense(result['expense_id'])
        assert expense['category'] == 'Uncategorized'


class TestFinancialReports:
    """Test financial report generation."""

    @pytest.fixture
    def tracker(self):
        """Create financial tracker."""
        vault_dir = tempfile.mkdtemp()
        tracker = FinancialTracker(vault_dir)
        yield tracker
        shutil.rmtree(vault_dir)

    def test_generate_summary(self, tracker):
        """Test generating financial summary."""
        tracker.add_invoice({'amount': 1500, 'vendor': 'Vendor A', 'due_date': '2026-03-01'})
        tracker.add_expense({'amount': 50, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})

        summary = tracker.generate_summary()
        assert 'pending_invoices' in summary
        assert 'total_expenses' in summary

    def test_generate_category_breakdown(self, tracker):
        """Test generating category breakdown."""
        tracker.add_expense({'amount': 50, 'category': 'Meals', 'payee': 'Restaurant', 'date': '2026-02-18'})
        tracker.add_expense({'amount': 100, 'category': 'Travel', 'payee': 'Airline', 'date': '2026-02-18'})

        breakdown = tracker.generate_category_breakdown()
        assert 'Meals' in breakdown
        assert breakdown['Meals'] == 50
        assert breakdown['Travel'] == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
