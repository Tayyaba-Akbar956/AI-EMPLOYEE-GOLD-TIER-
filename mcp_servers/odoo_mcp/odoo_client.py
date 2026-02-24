"""
Odoo Client - Python wrapper for Odoo JSON-RPC API
Used by MCP server and direct Python integration
"""
import os
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


class OdooClient:
    """
    Client for Odoo 19 Community JSON-RPC API
    """

    def __init__(self, url: str, db: str, username: str, password: str, vault_path: Optional[str] = None):
        """Initialize Odoo client"""
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None

        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            self.vault_path = Path(os.environ.get('VAULT_PATH', str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault')))

    def _call(self, service: str, method: str, *args) -> Any:
        """Make JSON-RPC call to Odoo"""
        try:
            response = requests.post(
                f"{self.url}/jsonrpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "service": service,
                        "method": method,
                        "args": args
                    },
                    "id": 1
                },
                timeout=10
            )

            result = response.json()

            if "error" in result:
                return None

            return result.get("result")

        except Exception as e:
            print(f"Odoo call error: {e}")
            return None

    def authenticate(self) -> Optional[int]:
        """
        Authenticate with Odoo and return user ID.
        Returns None on failure.
        """
        try:
            uid = self._call("common", "authenticate", self.db, self.username, self.password, {})
            self.uid = uid
            return uid
        except Exception:
            return None

    def get_invoices(self, date_from: Optional[str] = None, date_to: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get customer invoices by date range and status.
        """
        if self.uid is None:
            return []

        domain = [["move_type", "=", "out_invoice"]]

        if date_from:
            domain.append(["invoice_date", ">=", date_from])
        if date_to:
            domain.append(["invoice_date", "<=", date_to])
        if status:
            domain.append(["state", "=", status])

        fields = ["name", "partner_id", "amount_total", "invoice_date", "state"]

        result = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "account.move",
            "search_read",
            [domain],
            {"fields": fields}
        )

        return result if result else []

    def get_expenses(self, date_from: Optional[str] = None, date_to: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get expenses by date range and category.
        """
        if self.uid is None:
            return []

        domain = []

        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])
        if category:
            domain.append(["product_id.name", "ilike", category])

        fields = ["name", "total_amount", "date", "product_id"]

        result = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "hr.expense",
            "search_read",
            [domain],
            {"fields": fields}
        )

        return result if result else []

    def get_account_balance(self, account_code: str) -> Dict[str, Any]:
        """
        Get current balance for an account.
        """
        if self.uid is None:
            return {}

        domain = [["code", "=", account_code]]
        fields = ["code", "name", "balance", "currency_id"]

        result = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "account.account",
            "search_read",
            [domain],
            {"fields": fields}
        )

        if result and len(result) > 0:
            account = result[0]
            return {
                "code": account["code"],
                "name": account["name"],
                "balance": account["balance"],
                "currency": account["currency_id"][1] if account.get("currency_id") else "USD"
            }

        return {}

    def get_overdue_invoices(self, days_overdue: int = 0) -> List[Dict[str, Any]]:
        """
        Get overdue customer invoices.
        """
        if self.uid is None:
            return []

        today = datetime.now().strftime("%Y-%m-%d")

        domain = [
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
            ["invoice_date_due", "<", today],
            ["amount_residual", ">", 0]
        ]

        fields = ["name", "partner_id", "invoice_date_due", "amount_residual", "state"]

        result = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "account.move",
            "search_read",
            [domain],
            {"fields": fields}
        )

        return result if result else []

    def create_invoice(self, invoice_data: Dict[str, Any], require_approval: bool = True) -> Optional[str]:
        """
        Create a customer invoice.
        If require_approval=True, creates approval file and returns filename.
        Otherwise, creates invoice directly in Odoo.
        """
        if require_approval:
            return self._create_invoice_approval(invoice_data)
        else:
            return self._create_invoice_direct(invoice_data)

    def _create_invoice_approval(self, invoice_data: Dict[str, Any]) -> str:
        """Create approval file for invoice"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_filename = f"ODOO_INVOICE_{timestamp}.md"
        approval_path = self.vault_path / "Pending_Approval" / approval_filename

        # Ensure directory exists
        approval_path.parent.mkdir(parents=True, exist_ok=True)

        partner_name = invoice_data.get("partner_name", "Unknown")
        amount_total = invoice_data.get("amount_total", 0.0)
        invoice_lines = invoice_data.get("invoice_lines", [])

        content = f"""---
type: odoo_invoice
approval_id: {timestamp}
partner: {partner_name}
amount: {amount_total}
currency: USD
---

## Invoice Request

**Customer**: {partner_name}
**Amount**: ${amount_total:,.2f}

### Line Items
"""

        for i, line in enumerate(invoice_lines, 1):
            desc = line.get("description", "Item")
            price = line.get("price_unit", 0.0)
            content += f"{i}. {desc} - ${price:,.2f}\n"

        content += """
## Approval Required

This invoice will be created in Odoo in DRAFT state.
Approve to proceed, reject to cancel.
"""

        approval_path.write_text(content, encoding='utf-8')
        return approval_filename

    def _create_invoice_direct(self, invoice_data: Dict[str, Any]) -> int:
        """Create invoice directly in Odoo (after approval)"""
        if self.uid is None:
            return None

        # Create invoice in Odoo
        invoice_id = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "account.move",
            "create",
            [invoice_data]
        )

        return invoice_id

    def create_expense(self, expense_data: Dict[str, Any]) -> Optional[int]:
        """
        Create an expense (no approval required for draft).
        """
        if self.uid is None:
            return None

        expense_id = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "hr.expense",
            "create",
            [expense_data]
        )

        return expense_id

    def post_journal_entry(self, entry_data: Dict[str, Any], require_approval: bool = True) -> Optional[str]:
        """
        Post a journal entry.
        If require_approval=True, creates approval file and returns filename.
        """
        if require_approval:
            return self._create_journal_approval(entry_data)
        else:
            return self._post_journal_direct(entry_data)

    def _create_journal_approval(self, entry_data: Dict[str, Any]) -> str:
        """Create approval file for journal entry"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_filename = f"ODOO_JOURNAL_{timestamp}.md"
        approval_path = self.vault_path / "Pending_Approval" / approval_filename

        approval_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"""---
type: odoo_journal
approval_id: {timestamp}
journal_id: {entry_data.get('journal_id')}
---

## Journal Entry Request

**Journal ID**: {entry_data.get('journal_id')}

### Lines
"""

        for line in entry_data.get("line_ids", []):
            debit = line.get("debit", 0.0)
            credit = line.get("credit", 0.0)
            account = line.get("account_id", "Unknown")
            content += f"- Account {account}: Debit ${debit:,.2f}, Credit ${credit:,.2f}\n"

        content += """
## Approval Required

This journal entry will be posted to Odoo.
Approve to proceed, reject to cancel.
"""

        approval_path.write_text(content, encoding='utf-8')
        return approval_filename

    def _post_journal_direct(self, entry_data: Dict[str, Any]) -> int:
        """Post journal entry directly in Odoo (after approval)"""
        if self.uid is None:
            return None

        entry_id = self._call(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            "account.move",
            "create",
            [entry_data]
        )

        return entry_id
