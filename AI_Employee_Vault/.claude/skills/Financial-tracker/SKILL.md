---
name: financial-tracker
description: Track invoices, payments, and expenses. Use when invoice, receipt, or payment-related items detected. Extracts amounts from documents, categorizes financial items, tracks payment status, monitors budgets, generates financial summaries, and alerts on overdue items.
---

# Financial Tracker Skill

## Purpose
Track all money flowing in and out, categorize expenses, monitor budgets, and provide financial oversight to prevent overspending and missed payments.

## When to Use
- Invoice detected (any source)
- Receipt processed (any source)
- Payment mentioned in content
- Financial transaction keywords present
- Budget monitoring requested

## Core Capabilities

### extract_amount(document_text) -> float
Parses financial amounts from text:
- Finds dollar amounts ($X,XXX.XX format)
- Handles multiple currencies (USD, EUR, GBP, etc.)
- Validates extracted amounts (sanity checks)
- Handles edge cases (ranges, estimates)
- Returns: Normalized amount in USD

### categorize_expense(item) -> str
Assigns expense category:
- Predefined: Meals, Travel, Supplies, Software, Services, Marketing, Utilities
- Uses keywords and patterns
- References Company_Handbook.md for custom categories
- Machine learning from past categorizations
- Returns: Category name

### track_payment_status(invoice_id) -> str
Monitors invoice payment state:
- pending: Invoice received, awaiting payment
- paid: Payment completed and confirmed
- overdue: Past due date, not paid
- cancelled: Invoice voided or cancelled
- Returns: Current status

### calculate_budget_usage(category=None, month=None) -> dict
Computes spending against budget:
- Total spent (overall or by category)
- Budget allocated (from Company_Handbook.md)
- Remaining budget
- Percentage used
- Projection to month end
- Returns: Budget analysis dictionary

### check_overdue_items() -> list
Finds payments past due:
- Queries financial_records for unpaid invoices
- Filters to items past due_date
- Calculates days overdue
- Sorts by urgency (most overdue first)
- Returns: List of overdue invoice records

### generate_financial_summary(start_date, end_date) -> dict
Aggregates financial data for period:
- Total invoices received (count and amount)
- Total payments made (count and amount)
- Total expenses by category
- Budget vs actual comparison
- Largest transactions
- Returns: Comprehensive financial summary

## Database Schema

Stores in financial_records table:

```sql
CREATE TABLE financial_records (
    id INTEGER PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    type TEXT,  -- invoice/payment/receipt/expense
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    category TEXT,
    vendor TEXT,
    date DATE,
    due_date DATE,
    paid_date DATE,
    status TEXT,  -- pending/paid/overdue/cancelled
    notes TEXT
);
```

## Budget Monitoring

Configuration in Company_Handbook.md:

```markdown
## Budget Configuration

### Monthly Budget
monthly_budget: 5000  # USD

### Category Budgets
category_budgets:
  meals: 500
  travel: 1000
  supplies: 300
  software: 800
  services: 1500
  marketing: 900

### Alert Thresholds
budget_alert_threshold: 80  # Warn at 80%
budget_critical_threshold: 95  # Critical at 95%
```

Monitoring:
- Calculates spending vs budget continuously
- Warns when approaching limits
- Flags in dashboard when exceeded
- Factors into approval decisions

## Integration

**Called by:**
- email-processor (invoices/receipts in emails)
- file-organizer (financial documents)
- whatsapp-processor (invoice images)
- workflow-orchestrator (invoice/receipt/expense workflows)

**Calls:**
- database (store/query financial records)
- enhanced-dashboard (display financial metrics)
- approval-manager (for high-value items)

**Updates:**
- Dashboard financial section
- Monthly expense reports

## Testing Requirements

- Amount extraction accuracy (various formats)
- Category assignment correctness
- Budget calculations (totals, percentages)
- Overdue detection (date logic)
- Summary generation (aggregations)
- Multi-currency handling
- Edge cases (zero amounts, negative amounts, missing data)

---

**Status:** Core Silver Skill  
**Dependencies:** database, enhanced-dashboard  
**Priority:** High (financial accuracy critical)  
**Test Coverage Required:** >90%