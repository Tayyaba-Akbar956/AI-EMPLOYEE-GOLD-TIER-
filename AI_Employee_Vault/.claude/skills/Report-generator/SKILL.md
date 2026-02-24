---
name: report-generator
description: Generate automated weekly and monthly reports. Use on schedule (Monday for weekly, 1st of month for monthly) or on-demand. Queries database for date ranges, aggregates activity by source and category, generates markdown reports, exports to CSV for financial reports, and saves to Reports/ folder.
---

# Report Generator Skill

## Purpose
Generate comprehensive activity summaries and financial reports automatically on schedule or on-demand for productivity tracking, financial oversight, and compliance.

## When to Use
- Every Monday at 9:00 AM (weekly report)
- 1st of every month at 9:00 AM (monthly report)
- User explicitly requests custom report
- Milestone reached (e.g., 100 items processed, $10K expenses)

## Core Capabilities

### query_date_range(start_date, end_date, filters=None) -> list
Fetches data from database for period:
- Queries items table with date filter
- Applies optional filters (source, category, status)
- Joins with approvals, financials, workflows as needed
- Returns: List of matching database records

### aggregate_activity(records) -> dict
Summarizes activity data:
- Counts by source (Gmail, Files, WhatsApp, LinkedIn)
- Counts by category (invoice, receipt, contract, etc.)
- Calculates approval metrics (approved vs rejected)
- Identifies top categories and sources
- Returns: Aggregated statistics dictionary

### calculate_financial_totals(records) -> dict
Financial summary for period:
- Total invoices received (count and sum)
- Total invoices paid (count and sum)
- Total expenses by category
- Budget vs actual comparison
- Largest transactions (top 5)
- Spending trends vs previous period
- Returns: Financial summary dictionary

### generate_weekly_report() -> str
Creates weekly activity summary:
- Items processed by source
- Top categories handled
- Approvals processed (approved/rejected counts)
- Plans created and completed
- Workflows executed (breakdown by type)
- Time saved estimate
- Notable items (largest invoices, etc.)
- Returns: Markdown formatted report

### generate_monthly_report() -> str
Creates comprehensive monthly summary:
- All weekly report content
- Financial deep-dive section
- Spending trends (vs previous months)
- Budget analysis (by category)
- Compliance items (audit trail summary)
- Recommendations for next month
- Returns: Markdown + triggers CSV export

### export_to_csv(financial_data, filename) -> str
Exports financial records to CSV:
- Creates CSV with proper headers
- Includes all financial transactions
- Formats amounts with 2 decimal places
- Includes categories and vendors
- Saves to Reports/ folder alongside markdown
- Returns: CSV file path

### save_report(content, report_type, date) -> str
Stores report in vault:
- Determines folder (weekly/monthly/custom)
- Generates filename: YYYY-MM-DD-{type}.md
- Writes markdown file
- Optionally exports CSV (for monthly financial)
- Logs report generation to activity log
- Updates dashboard with report link
- Returns: Report file path

## Report Types

**Weekly Report:**
- **Filename:** Reports/weekly/2026-02-17-weekly.md
- **Content:** 7-day activity summary
- **Sections:** Activity by source, approvals, plans, workflows, highlights
- **Format:** Markdown only

**Monthly Report:**
- **Filename:** Reports/monthly/2026-02-monthly-report.md
- **Content:** Full month analysis + financials
- **Includes:** CSV export (2026-02-financial-data.csv)
- **Sections:** Activity, financial deep-dive, trends, budget, recommendations
- **Format:** Markdown + CSV

**Custom Report:**
- **Filename:** Reports/custom/2026-02-15-custom-{description}.md
- **Content:** User-specified date range and filters
- **Format:** Markdown (CSV optional)

## Scheduling

Uses system scheduler (cron or similar):
```
# Weekly: Every Monday at 9 AM
0 9 * * 1 python -m ai_employee generate-report --type weekly

# Monthly: 1st of month at 9 AM
0 9 1 * * python -m ai_employee generate-report --type monthly
```

## Report Content Examples

**Weekly Report Structure:**
```markdown
# Weekly Activity Report
**Week of:** February 10-16, 2026
**Generated:** February 17, 2026 09:00 AM

## Summary
- **Total Items:** 47
- **Approvals:** 3 approved, 1 rejected
- **Plans Created:** 2
- **Workflows Completed:** 15

## Activity by Source
- Gmail: 23 items (49%)
- Filesystem: 12 items (26%)
- WhatsApp: 8 items (17%)
- LinkedIn: 4 items (8%)

## Top Categories
1. Invoices: 12 items
2. Receipts: 10 items
3. Emails: 8 items
...
```

**Monthly Report Structure:**
```markdown
# Monthly Activity & Financial Report
**Month:** February 2026
**Generated:** March 1, 2026 09:00 AM

[Activity sections similar to weekly]

## Financial Summary
**Invoices:**
- Received: $23,450 (15 invoices)
- Paid: $18,200 (12 invoices)
- Pending: $5,250 (3 invoices)

**Expenses:**
- Total: $4,320
- By category:
  - Meals: $450
  - Travel: $1,200
  - Software: $800
  ...

**Budget Analysis:**
- Budget: $5,000
- Spent: $4,320 (86%)
- Remaining: $680

**Largest Transactions:**
1. Acme Corp - $5,000 (services)
2. XYZ Vendor - $3,200 (equipment)
...

## Recommendations
- Consider negotiating rates with Acme Corp (largest vendor)
- Travel expenses 20% over budget - review travel policy
...

[See attached CSV for complete transaction details]
```

## Integration

**Called by:**
- Scheduler (automated on schedule)
- CLI (user command for custom reports)

**Queries:**
- Database (all tables for comprehensive data)

**Calls:**
- vault-management (save report files)
- Optional: Email service (deliver reports)

**Updates:**
- Dashboard (adds report link to recent activity)

## Testing Requirements

- Date range queries (correct filtering)
- Aggregation accuracy (counts and sums correct)
- Financial calculations (exact amounts)
- Report generation (all types)
- CSV export (proper format, all data)
- Scheduled execution (triggers on time)
- File creation (reports saved correctly)

---

**Status:** Silver Skill  
**Dependencies:** database, vault-management  
**Priority:** Medium  
**Test Coverage Required:** >80%