"""
Unit tests for Odoo MCP Server (Feature 3)
Tests JSON-RPC connection, all 7 tools, approval workflow, error handling
"""
import pytest
import json
import responses
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def odoo_config():
    """Odoo configuration for testing"""
    return {
        "url": "http://localhost:8069",
        "db": "ai_employee",
        "username": "test@example.com",
        "password": "testpass"
    }


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()
    (vault / "Pending_Approval").mkdir()
    return vault


class TestOdooConnection:
    """Test Odoo JSON-RPC connection"""

    @responses.activate
    def test_authenticate_success(self, odoo_config):
        """Test successful authentication with Odoo"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        # Mock authentication response
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={"result": 1},  # user id
            status=200
        )

        client = OdooClient(**odoo_config)
        uid = client.authenticate()

        assert uid == 1

    @responses.activate
    def test_authenticate_failure(self, odoo_config):
        """Test authentication failure"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        # Mock authentication error
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={"error": {"message": "Invalid credentials"}},
            status=200
        )

        client = OdooClient(**odoo_config)
        uid = client.authenticate()

        assert uid is None

    @responses.activate
    def test_connection_timeout(self, odoo_config):
        """Test connection timeout handling"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient
        import requests

        # Mock timeout
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            body=requests.exceptions.Timeout()
        )

        client = OdooClient(**odoo_config)
        uid = client.authenticate()

        # Should return None on timeout, not raise exception
        assert uid is None


class TestGetInvoices:
    """Test get_invoices tool"""

    @responses.activate
    def test_get_invoices_success(self, odoo_config):
        """Test retrieving invoices"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        # Mock authentication
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={"result": 1},
            status=200
        )

        # Mock search_read for invoices
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={
                "result": [
                    {
                        "id": 1,
                        "name": "INV/2026/0001",
                        "partner_id": [42, "Acme Corp"],
                        "amount_total": 5000.0,
                        "invoice_date": "2026-02-01",
                        "state": "posted"
                    }
                ]
            },
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()
        invoices = client.get_invoices(date_from="2026-02-01", date_to="2026-02-28")

        assert len(invoices) == 1
        assert invoices[0]["name"] == "INV/2026/0001"
        assert invoices[0]["amount_total"] == 5000.0

    @responses.activate
    def test_get_invoices_by_status(self, odoo_config):
        """Test filtering invoices by status"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(responses.POST, f"{odoo_config['url']}/jsonrpc", json={"result": 1})
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={"result": [{"id": 1, "state": "draft"}]},
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()
        invoices = client.get_invoices(status="draft")

        assert len(invoices) == 1
        assert invoices[0]["state"] == "draft"


class TestGetExpenses:
    """Test get_expenses tool"""

    @responses.activate
    def test_get_expenses_success(self, odoo_config):
        """Test retrieving expenses"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(responses.POST, f"{odoo_config['url']}/jsonrpc", json={"result": 1})
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={
                "result": [
                    {
                        "id": 1,
                        "name": "Office Supplies",
                        "total_amount": 150.0,
                        "date": "2026-02-15",
                        "product_id": [10, "Office Supplies"]
                    }
                ]
            },
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()
        expenses = client.get_expenses(date_from="2026-02-01", date_to="2026-02-28")

        assert len(expenses) == 1
        assert expenses[0]["total_amount"] == 150.0

    @responses.activate
    def test_get_expenses_by_category(self, odoo_config):
        """Test filtering expenses by category"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(responses.POST, f"{odoo_config['url']}/jsonrpc", json={"result": 1})
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={"result": [{"id": 1, "product_id": [10, "Travel"]}]},
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()
        expenses = client.get_expenses(category="Travel")

        assert len(expenses) == 1


class TestGetAccountBalance:
    """Test get_account_balance tool"""

    @responses.activate
    def test_get_account_balance_success(self, odoo_config):
        """Test retrieving account balance"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(responses.POST, f"{odoo_config['url']}/jsonrpc", json={"result": 1})
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={
                "result": [
                    {
                        "id": 1,
                        "code": "100000",
                        "name": "Bank Account",
                        "balance": 25000.0,
                        "currency_id": [1, "USD"]
                    }
                ]
            },
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()
        balance = client.get_account_balance(account_code="100000")

        assert balance["balance"] == 25000.0
        assert balance["currency"] == "USD"


class TestGetOverdueInvoices:
    """Test get_overdue_invoices tool"""

    @responses.activate
    def test_get_overdue_invoices_success(self, odoo_config):
        """Test retrieving overdue invoices"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(responses.POST, f"{odoo_config['url']}/jsonrpc", json={"result": 1})
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={
                "result": [
                    {
                        "id": 1,
                        "name": "INV/2026/0001",
                        "invoice_date_due": "2026-01-15",
                        "amount_residual": 5000.0,
                        "state": "posted"
                    }
                ]
            },
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()
        overdue = client.get_overdue_invoices()

        assert len(overdue) == 1
        assert overdue[0]["amount_residual"] == 5000.0


class TestCreateInvoice:
    """Test create_invoice tool (requires approval)"""

    def test_create_invoice_creates_approval_file(self, odoo_config, vault_path):
        """Test that create_invoice creates approval file"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        client = OdooClient(**odoo_config, vault_path=str(vault_path))

        invoice_data = {
            "partner_id": 42,
            "invoice_lines": [
                {"product_id": 1, "quantity": 1, "price_unit": 5000.0}
            ]
        }

        approval_file = client.create_invoice(invoice_data, require_approval=True)

        assert approval_file is not None
        assert (vault_path / "Pending_Approval" / approval_file).exists()

    def test_create_invoice_approval_content(self, odoo_config, vault_path):
        """Test approval file contains correct information"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        client = OdooClient(**odoo_config, vault_path=str(vault_path))

        invoice_data = {
            "partner_id": 42,
            "partner_name": "Acme Corp",
            "amount_total": 5000.0,
            "invoice_lines": [
                {"description": "Consulting", "price_unit": 5000.0}
            ]
        }

        approval_file = client.create_invoice(invoice_data, require_approval=True)

        content = (vault_path / "Pending_Approval" / approval_file).read_text()
        assert "Acme Corp" in content
        assert "5000.0" in content
        assert "Consulting" in content


class TestCreateExpense:
    """Test create_expense tool (no approval required)"""

    @responses.activate
    def test_create_expense_success(self, odoo_config):
        """Test creating expense without approval"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(responses.POST, f"{odoo_config['url']}/jsonrpc", json={"result": 1})
        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            json={"result": 123},  # expense id
            status=200
        )

        client = OdooClient(**odoo_config)
        client.authenticate()

        expense_data = {
            "name": "Office Supplies",
            "total_amount": 150.0,
            "date": "2026-02-24"
        }

        expense_id = client.create_expense(expense_data)

        assert expense_id == 123


class TestPostJournalEntry:
    """Test post_journal_entry tool (requires approval)"""

    def test_post_journal_entry_creates_approval_file(self, odoo_config, vault_path):
        """Test that post_journal_entry creates approval file"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        client = OdooClient(**odoo_config, vault_path=str(vault_path))

        entry_data = {
            "journal_id": 1,
            "line_ids": [
                {"account_id": 100, "debit": 1000.0, "credit": 0.0},
                {"account_id": 200, "debit": 0.0, "credit": 1000.0}
            ]
        }

        approval_file = client.post_journal_entry(entry_data, require_approval=True)

        assert approval_file is not None
        assert (vault_path / "Pending_Approval" / approval_file).exists()


class TestErrorHandling:
    """Test error handling and graceful degradation"""

    def test_odoo_unavailable_returns_none(self, odoo_config):
        """Test that unavailable Odoo returns None gracefully"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        # Don't mock any responses - connection will fail
        client = OdooClient(**odoo_config)
        uid = client.authenticate()

        assert uid is None

    @responses.activate
    def test_invalid_response_handled(self, odoo_config):
        """Test handling of invalid JSON response"""
        from mcp_servers.odoo_mcp.odoo_client import OdooClient

        responses.add(
            responses.POST,
            f"{odoo_config['url']}/jsonrpc",
            body="Invalid JSON",
            status=200
        )

        client = OdooClient(**odoo_config)
        uid = client.authenticate()

        assert uid is None
