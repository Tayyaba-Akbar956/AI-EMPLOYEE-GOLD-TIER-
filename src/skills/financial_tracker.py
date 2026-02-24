"""Financial Tracker for AI Employee Silver Tier.

Tracks invoices, expenses, budgets, and generates financial reports.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FinancialTracker:
    """Tracks financial data including invoices, expenses, and budgets.

    Handles invoice tracking, expense categorization, budget monitoring,
    and financial report generation.
    """

    def __init__(self, vault_path: str):
        """Initialize financial tracker.

        Args:
            vault_path: Path to AI_Employee_Vault
        """
        self.vault_path = Path(vault_path)

        # In-memory storage (simulating database)
        self.invoices = {}
        self.expenses = {}
        self.budgets = {
            'monthly_budget': 5000,
            'category_budgets': {}
        }

        # Default categories
        self.categories = [
            'Meals', 'Travel', 'Supplies', 'Software', 'Services',
            'Marketing', 'Utilities', 'Rent', 'Uncategorized'
        ]

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure required folders exist."""
        folders = [
            'Reports/financial',
            'Logs/financial'
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    def add_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add invoice to tracking.

        Args:
            invoice_data: Invoice data dictionary

        Returns:
            Result dictionary with invoice_id
        """
        try:
            invoice_id = str(uuid.uuid4())
            invoice = {
                'invoice_id': invoice_id,
                'amount': invoice_data.get('amount', 0),
                'vendor': invoice_data.get('vendor', 'Unknown'),
                'due_date': invoice_data.get('due_date', ''),
                'description': invoice_data.get('description', ''),
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }

            self.invoices[invoice_id] = invoice
            logger.info(f"Added invoice {invoice_id}: ${invoice['amount']} to {invoice['vendor']}")

            return {
                'success': True,
                'invoice_id': invoice_id
            }

        except Exception as e:
            logger.error(f"Error adding invoice: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice by ID.

        Args:
            invoice_id: Invoice ID

        Returns:
            Invoice dictionary or None
        """
        return self.invoices.get(invoice_id)

    def list_pending_invoices(self) -> List[Dict[str, Any]]:
        """List all pending invoices.

        Returns:
            List of pending invoice dictionaries
        """
        pending = []
        for invoice in self.invoices.values():
            if invoice['status'] == 'pending':
                pending.append(invoice)
        return pending

    def mark_invoice_paid(self, invoice_id: str) -> Dict[str, Any]:
        """Mark invoice as paid.

        Args:
            invoice_id: Invoice ID

        Returns:
            Result dictionary
        """
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return {'success': False, 'error': 'Invoice not found'}

        invoice['status'] = 'paid'
        invoice['paid_at'] = datetime.now().isoformat()
        logger.info(f"Marked invoice {invoice_id} as paid")

        return {'success': True}

    def get_overdue_invoices(self) -> List[Dict[str, Any]]:
        """Get overdue invoices.

        Returns:
            List of overdue invoice dictionaries
        """
        overdue = []
        today = datetime.now().date()

        for invoice in self.invoices.values():
            if invoice['status'] == 'pending' and invoice['due_date']:
                try:
                    due_date = datetime.fromisoformat(invoice['due_date']).date()
                    if due_date < today:
                        overdue.append(invoice)
                except:
                    pass

        return overdue

    def add_expense(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add expense to tracking.

        Args:
            expense_data: Expense data dictionary

        Returns:
            Result dictionary with expense_id
        """
        try:
            expense_id = str(uuid.uuid4())
            category = expense_data.get('category', 'Uncategorized')

            # Validate category
            if category not in self.categories:
                category = 'Uncategorized'

            expense = {
                'expense_id': expense_id,
                'amount': expense_data.get('amount', 0),
                'category': category,
                'payee': expense_data.get('payee', 'Unknown'),
                'date': expense_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'description': expense_data.get('description', ''),
                'created_at': datetime.now().isoformat()
            }

            self.expenses[expense_id] = expense
            logger.info(f"Added expense {expense_id}: ${expense['amount']} - {expense['category']}")

            return {
                'success': True,
                'expense_id': expense_id
            }

        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_expense(self, expense_id: str) -> Optional[Dict[str, Any]]:
        """Get expense by ID.

        Args:
            expense_id: Expense ID

        Returns:
            Expense dictionary or None
        """
        return self.expenses.get(expense_id)

    def list_expenses_by_category(self, category: str) -> List[Dict[str, Any]]:
        """List expenses by category.

        Args:
            category: Category name

        Returns:
            List of expense dictionaries
        """
        expenses = []
        for expense in self.expenses.values():
            if expense['category'] == category:
                expenses.append(expense)
        return expenses

    def calculate_total_expenses(self, category: Optional[str] = None) -> float:
        """Calculate total expenses.

        Args:
            category: Optional category to filter by

        Returns:
            Total expense amount
        """
        total = 0
        for expense in self.expenses.values():
            if category is None or expense['category'] == category:
                total += expense['amount']
        return total

    def set_monthly_budget(self, amount: float) -> Dict[str, Any]:
        """Set monthly budget.

        Args:
            amount: Budget amount

        Returns:
            Result dictionary
        """
        self.budgets['monthly_budget'] = amount
        logger.info(f"Set monthly budget to ${amount}")
        return {'success': True}

    def set_category_budget(self, category: str, amount: float) -> Dict[str, Any]:
        """Set category budget.

        Args:
            category: Category name
            amount: Budget amount

        Returns:
            Result dictionary
        """
        self.budgets['category_budgets'][category] = amount
        logger.info(f"Set {category} budget to ${amount}")
        return {'success': True}

    def get_budget_status(self) -> Dict[str, Any]:
        """Get budget status.

        Returns:
            Budget status dictionary
        """
        total_budget = self.budgets['monthly_budget']
        spent = self.calculate_total_expenses()
        remaining = total_budget - spent
        percentage = int((spent / total_budget) * 100) if total_budget > 0 else 0

        status = {
            'total_budget': total_budget,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'alert': percentage >= 80,
            'exceeded': spent > total_budget
        }

        return status

    def get_categories(self) -> List[str]:
        """Get list of categories.

        Returns:
            List of category names
        """
        return self.categories

    def add_category(self, category: str) -> Dict[str, Any]:
        """Add custom category.

        Args:
            category: Category name

        Returns:
            Result dictionary
        """
        if category not in self.categories:
            self.categories.append(category)
            logger.info(f"Added category: {category}")

        return {'success': True}

    def generate_summary(self) -> Dict[str, Any]:
        """Generate financial summary.

        Returns:
            Summary dictionary
        """
        pending_invoices = self.list_pending_invoices()
        total_expenses = self.calculate_total_expenses()
        budget_status = self.get_budget_status()

        summary = {
            'pending_invoices': len(pending_invoices),
            'pending_amount': sum(inv['amount'] for inv in pending_invoices),
            'total_expenses': total_expenses,
            'budget_status': budget_status,
            'overdue_invoices': len(self.get_overdue_invoices())
        }

        return summary

    def generate_category_breakdown(self) -> Dict[str, float]:
        """Generate expense breakdown by category.

        Returns:
            Dictionary mapping category to total amount
        """
        breakdown = {}
        for category in self.categories:
            total = self.calculate_total_expenses(category)
            if total > 0:
                breakdown[category] = total

        return breakdown
