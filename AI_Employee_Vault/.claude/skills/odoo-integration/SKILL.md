---
name: odoo-integration
description: Integrate with Odoo 19 Community for accounting, invoicing, and expense tracking via JSON-RPC MCP server
version: 1.0.0
trigger: Financial tasks, invoice requests, expense logging, account balance queries
---

# Odoo Integration Skill

## Purpose

Provides full accounting integration with Odoo 19 Community Edition via a custom MCP server. Handles invoices, expenses, payments, journal entries, and financial reporting.

## MCP Server Tools

The Odoo MCP server exposes 7 tools via JSON-RPC:

### Read-Only Tools (No Approval Required)

1. **get_invoices**
   - List customer invoices by date range and status
   - Parameters: `date_from`, `date_to`, `status` (draft/posted/paid/cancel)
   - Returns: Array of invoice objects with id, partner, amount, date, state

2. **get_expenses**
   - List expenses by category and date range
   - Parameters: `date_from`, `date_to`, `category`
   - Returns: Array of expense objects with id, description, amount, date, category

3. **get_account_balance**
   - Get current balance from chart of accounts
   - Parameters: `account_code` (e.g., "100000" for bank account)
   - Returns: Current balance, currency, last_update

4. **get_overdue_invoices**
   - List all overdue customer invoices
   - Parameters: `days_overdue` (optional, default: 0)
   - Returns: Array of overdue invoices with days_overdue calculated

### Write Tools (Approval Required)

5. **create_invoice**
   - Create a new customer invoice
   - Parameters: `partner_id`, `invoice_lines` (array), `payment_term_id`
   - **ALWAYS requires approval** - creates approval file first
   - Returns: Invoice ID and draft state

6. **create_expense**
   - Log a business expense
   - Parameters: `description`, `amount`, `category`, `date`
   - No approval required for draft expenses
   - Returns: Expense ID

7. **post_journal_entry**
   - Post an accounting journal entry
   - Parameters: `journal_id`, `line_ids` (debit/credit lines)
   - **ALWAYS requires approval** - creates approval file first
   - Returns: Journal entry ID

## Odoo Connection

**Protocol**: JSON-RPC 2.0 over HTTP
**Endpoint**: `http://localhost:8069/jsonrpc`
**Authentication**: Email + Password (stored in .env)

```javascript
// Example JSON-RPC call
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "service": "object",
    "method": "execute_kw",
    "args": [
      "ai_employee",           // database
      uid,                     // user id from authenticate
      "password",              // password
      "account.move",          // model
      "search_read",           // method
      [["move_type", "=", "out_invoice"]], // domain
      {"fields": ["name", "partner_id", "amount_total"]}
    ]
  },
  "id": 1
}
```

## Approval Workflow

For `create_invoice` and `post_journal_entry`:

1. MCP server receives request
2. Creates approval file: `/Pending_Approval/ODOO_INVOICE_<timestamp>.md`
3. Returns pending status to Claude
4. Claude exits, Ralph Wiggum blocks
5. Human approves via CLI
6. Orchestrator detects approval, executes MCP action
7. Invoice created in Odoo, task moves to `/Done/`

## Invoice Creation Example

```markdown
---
type: odoo_invoice
approval_id: ODOO_INV_001
partner: Acme Corp
amount: 5000.00
currency: USD
due_date: 2026-03-15
---

## Invoice Request

**Customer**: Acme Corp (partner_id: 42)
**Amount**: $5,000.00
**Due Date**: March 15, 2026

### Line Items
1. Consulting Services - $3,500.00
2. Software License - $1,500.00

**Payment Terms**: Net 30

## Approval Required

This invoice will be created in Odoo in DRAFT state.
Approve to proceed, reject to cancel.
```

## Error Handling

If Odoo is unavailable:
1. MCP server returns error
2. Orchestrator logs to `SYSTEM_ALERT_ODOO_*.md`
3. Falls back to SQLite data for read operations
4. Write operations fail gracefully with alert

## Environment Variables

```env
ODOO_URL=http://localhost:8069
ODOO_DB=ai_employee
ODOO_USERNAME=falihaarain48@gmail.com
ODOO_PASSWORD=<set>
```

## Docker Setup

```bash
# Create network
docker network create odoo-network

# Start PostgreSQL
docker run -d \
  --name postgres-odoo \
  --network odoo-network \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD=odoo \
  -e POSTGRES_DB=postgres \
  postgres:15

# Start Odoo
docker run -d \
  --name odoo-ai-employee \
  --network odoo-network \
  -p 8069:8069 \
  -e HOST=postgres-odoo \
  -e USER=odoo \
  -e PASSWORD=odoo \
  odoo:19
```

## MCP Server Installation

```bash
cd mcp_servers/odoo_mcp
npm install
node index.js --test  # Test connection
```

## Integration with Orchestrator

When orchestrator detects task type `odoo` or `financial`:

1. Loads this SKILL.md
2. Triggers Claude Code with task + skill
3. Claude uses MCP tools to query/create in Odoo
4. For write operations, creates approval file
5. Ralph Wiggum blocks until approved
6. Orchestrator executes approved action via MCP
7. Logs to SQLite + JSON

## Testing

Unit tests verify:
- MCP server connects to Odoo
- All 7 tools work correctly
- Approval workflow for write operations
- Error handling when Odoo down
- JSON-RPC request/response format

Integration tests verify:
- End-to-end invoice creation flow
- Expense logging and retrieval
- Account balance queries
- Overdue invoice detection

## CEO Briefing Integration

The CEO briefing (Feature 8) will use these tools:
- `get_invoices` - Revenue this week/month
- `get_expenses` - Spending by category
- `get_account_balance` - Current cash position
- `get_overdue_invoices` - Collections needed

## Notes

- Odoo 19 Community is free and open-source
- All invoices created in DRAFT state - human must post/send
- Expenses logged as draft - human must submit/approve in Odoo
- Journal entries require approval before posting
- MCP server runs as separate Node.js process
- Registered in `~/.claude/claude_code_config.json`
