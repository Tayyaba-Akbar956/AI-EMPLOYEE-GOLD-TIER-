# AI Employee Database

**Version:** 1.0.0
**Created:** 2026-02-18
**Tier:** Silver

---

## Overview

This directory contains the SQLite database for the AI Employee Silver Tier system. The database provides centralized storage for all items, approvals, plans, workflows, financial records, and activity logs.

## Database File

- **File:** `ai_employee.db`
- **Type:** SQLite 3
- **Location:** `AI_Employee_Vault/Database/`
- **Size:** ~96KB (initial)

## Schema

### Tables

1. **items** - All processed items from all sources
   - Tracks emails, files, messages, posts
   - Stores metadata, amounts, status, priority
   - Links to approvals, workflows, financial records

2. **approvals** - Approval workflow tracking
   - Manages high-value item approvals
   - Tracks deadlines, decisions, reminders
   - Links to items table

3. **plans** - AI-generated execution plans
   - Stores plan details, complexity, status
   - Tracks progress (steps completed/total)
   - Manages estimated vs actual hours

4. **workflows** - Workflow execution state
   - Tracks 7 automated workflows
   - Manages current step, status (running/paused/completed)
   - Stores workflow-specific state data as JSON

5. **financial_records** - Money tracking
   - Invoices, payments, receipts, expenses
   - Tracks amounts, vendors, due dates, payment status
   - Supports budget tracking and reporting

6. **activity_log** - Audit trail
   - Logs all system actions
   - Tracks component, action, timestamp
   - Links to related items

### Indexes

Optimized indexes on:
- `items.status`, `items.source`, `items.category`
- `approvals.decision`, `approvals.deadline`
- `workflows.status`
- `financial_records.payment_status`, `financial_records.due_date`
- `activity_log.timestamp`

## Usage

### Python API

```python
from src.database.db_manager import DatabaseManager

# Initialize (uses default path)
db = DatabaseManager()

# Or specify custom path
db = DatabaseManager('/path/to/custom.db')

# Create item
db.create_item({
    'id': 'unique-id',
    'source': 'gmail',
    'type': 'email',
    'category': 'invoice',
    'amount': 1500.00,
    'status': 'pending',
    'file_path': 'Inbox/emails/invoice.md'
})

# Get item
item = db.get_item('unique-id')

# Update item
db.update_item('unique-id', {'status': 'approved'})

# Query items
pending_items = db.get_items_by_status('pending')
gmail_items = db.get_items_by_source('gmail')

# Approvals
pending_approvals = db.get_pending_approvals()
overdue_approvals = db.get_overdue_approvals()

# Financial
pending_invoices = db.get_pending_invoices()
overdue_invoices = db.get_overdue_invoices()
summary = db.get_financial_summary()

# Activity
db.log_activity({
    'level': 'INFO',
    'component': 'email-processor',
    'action': 'Processed invoice',
    'item_id': 'unique-id'
})
recent = db.get_recent_activity(limit=10)

# Statistics
stats = db.get_stats()
tables = db.get_tables()
```

## Features

### Connection Management
- Context manager for automatic cleanup
- Connection pooling support
- Thread-safe operations
- Automatic rollback on errors

### Transaction Support
- ACID compliance
- Automatic commit/rollback
- Error handling with logging

### Error Handling
- All operations return success/failure
- Graceful degradation on errors
- Comprehensive logging
- Returns None/empty list on query failures

### Performance
- Indexed queries for fast lookups
- Optimized for common access patterns
- Minimal overhead for reads
- Batch operations supported

## Testing

### Test Coverage: 98%

- **66 unit tests** covering all operations
- **CRUD operations** for all tables
- **Complex queries** and joins
- **Error handling** and edge cases
- **Concurrent access** testing
- **Transaction rollback** verification

### Run Tests

```bash
# Run all database tests
pytest tests/test_database.py -v

# Check coverage
pytest tests/test_database.py --cov=src.database --cov-report=term-missing

# Run verification script
python verify_database.py
```

## Maintenance

### Backup

```bash
# Manual backup
cp AI_Employee_Vault/Database/ai_employee.db AI_Employee_Vault/Database/ai_employee_backup_$(date +%Y%m%d).db

# Automated backups (recommended)
# Add to cron or scheduled task
```

### Vacuum

```bash
# Optimize database (reclaim space)
sqlite3 AI_Employee_Vault/Database/ai_employee.db "VACUUM;"
```

### Integrity Check

```bash
# Check database integrity
sqlite3 AI_Employee_Vault/Database/ai_employee.db "PRAGMA integrity_check;"
```

## Migration

If schema changes are needed:

1. Backup current database
2. Update schema in `db_manager.py`
3. Run migration script (create if needed)
4. Verify with tests
5. Update version number

## Security

- Database file permissions: 644 (read/write owner, read others)
- No sensitive data stored in plain text
- Use environment variables for credentials
- Regular backups recommended
- Audit trail via activity_log table

## Troubleshooting

### Database Locked
- Check for long-running transactions
- Ensure proper connection cleanup
- Use context managers

### Slow Queries
- Check indexes are created
- Run ANALYZE to update statistics
- Consider VACUUM if database is large

### Corruption
- Run integrity check
- Restore from backup if needed
- Check disk space and permissions

## Integration

The database integrates with:

- **4 Watchers:** Gmail, Filesystem, WhatsApp, LinkedIn
- **12 Skills:** All Bronze + Silver skills
- **7 Workflows:** Invoice, Receipt, Research, File Org, Email Response, Meeting Prep, Expense Report
- **Dashboard:** Real-time statistics and summaries
- **Reports:** Weekly and monthly automated reports

## Version History

- **1.0.0** (2026-02-18) - Initial Silver Tier database setup
  - 6 tables created
  - 66 tests passing
  - 98% code coverage
  - Full CRUD operations
  - Transaction support
  - Error handling

---

*For questions or issues, see PROJECT_KICKOFF_SILVER.md or CLAUDE.md*
