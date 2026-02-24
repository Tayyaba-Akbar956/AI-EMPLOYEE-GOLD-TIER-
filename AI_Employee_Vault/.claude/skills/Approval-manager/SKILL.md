---
name: approval-manager
description: Manage approval workflow for high-value items. Use when items exceed threshold ($1000+), contracts detected, or explicit approval required. Handles approval card generation, timeout logic, reminders, and decision processing for financial and legal oversight.
---

# Approval Manager Skill

## Purpose
Prevent costly mistakes by ensuring human oversight for significant financial decisions and legal commitments.

## When to Use
- Invoice amount >= $1000 (configurable in Company_Handbook.md)
- Any contract or legal document detected
- Items with "approval required" keyword in content
- Workflow steps requiring explicit user approval

## Core Capabilities

### 1. should_require_approval(item) -> dict
Determines if item needs approval based on:
- Item type (contracts always require approval)
- Amount extracted (if financial item)
- Comparison against threshold from Company_Handbook.md
- Keywords in content ("approval required")

Returns dictionary with:
- requires_approval: bool
- reason: str (why approval needed)
- priority: str (high/medium/low)
- deadline: datetime (when auto-approve occurs)

### 2. generate_approval_card(item) -> str
Creates detailed markdown approval card with:
- Clear "APPROVAL REQUIRED" header
- Item details (type, amount, sender, date)
- Financial impact (current budget usage, this item's impact, remaining)
- AI recommendation (approve/reject with reasoning)
- Decision instructions (how to approve via Obsidian or CLI)
- Deadline timestamp with countdown
- Unique approval ID for tracking

### 3. process_approval(approval_id, decision, reason=None) -> dict
Handles user's approval or rejection decision:
- Retrieves approval record from database
- Validates decision is still pending
- Updates database with decision and timestamp
- Moves file from Pending_Approval/ to Approved/ or Rejected/
- Triggers associated workflow if approved
- Logs reason if rejected
- Updates dashboard counts
- Writes to audit trail

### 4. check_approval_timeouts() -> list
Auto-processes approvals that exceed timeout period:
- Queries database for pending approvals
- Calculates time elapsed since creation
- Compares against timeout from Company_Handbook.md (default: 24 hours)
- Auto-approves if configured (with auto_decided flag set)
- Logs all auto-approvals with reasoning
- Updates dashboard
- Returns list of auto-processed approval IDs

### 5. send_approval_reminders() -> list
Sends reminders for approvals approaching deadline:
- Finds pending approvals created >4 hours ago
- Filters to those without reminder_sent flag
- Updates approval card with "REMINDER" prefix
- Refreshes Dashboard.md with urgent indicator
- Marks reminder_sent=True in database
- Optional: Sends email notification if configured
- Returns list of approval IDs that received reminders

### 6. log_approval_decision(approval_id, decision, reason, auto_decided)
Logs approval decision to audit trail:
- Writes to database approvals table
- Writes to Logs/approvals/YYYY-MM-DD-approvals.log
- Updates Dashboard.md recent activity
- Records who made decision (user or auto)
- Preserves rejection reasons for compliance

## Approval Methods

**Method 1: Via Obsidian**
1. Open Pending_Approval/ folder in Obsidian
2. Review approval card
3. Drag file to Approved/ folder (to approve)
4. OR drag file to Rejected/ folder (to reject)
5. Filesystem watcher detects move and processes

**Method 2: Via CLI**
```bash
# In project directory
python -m ai_employee approve invoice-12345

python -m ai_employee reject contract-abc --reason "Needs legal review"
```

## Configuration (Company_Handbook.md)

All settings under "Approval Workflow" section:

```markdown
## Approval Workflow Configuration

### Thresholds
- Invoice approval threshold: $1000
- Contract approval: Always required
- Keyword trigger: "approval required"

### Timeouts
- Approval timeout: 24 hours
- Reminder schedule: 4 hours after creation
- Auto-approve on timeout: Yes

### Notifications
- Email reminders: No (Optional)
- Dashboard alerts: Yes
```

## Database Schema

Approval records stored in `approvals` table:

```sql
CREATE TABLE approvals (
    id INTEGER PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    item_id INTEGER REFERENCES items(id),
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMP,
    decision TEXT,  -- approved/rejected/expired
    reason TEXT,
    auto_decided BOOLEAN DEFAULT 0,
    reminder_sent BOOLEAN DEFAULT 0,
    reminder_sent_at TIMESTAMP
);
```

## Integration with Other Skills

**Receives items from:**
- email-processor (high-value invoices from emails)
- file-organizer (contracts, invoices from files)
- whatsapp-processor (business decisions from WhatsApp)
- linkedin-processor (job offers, contracts from LinkedIn)

**Calls:**
- vault-management (file operations)
- database (record approvals)
- enhanced-dashboard (update approval queue)

**Triggers:**
- workflow-orchestrator (executes workflow after approval)

## Example Workflow

### Example 1: High-Value Invoice
```
1. Email arrives with $5,000 invoice
2. email-processor extracts amount
3. approval-manager.should_require_approval() → True (>$1000)
4. approval-manager.generate_approval_card() creates card
5. File moved to Pending_Approval/high_value/
6. Dashboard shows "1 item pending approval"
7. User reviews in Obsidian
8. User approves via CLI: approve invoice-12345
9. File moves to Approved/
10. Invoice workflow executes
11. Financial tracker records $5,000
```

### Example 2: Timeout Auto-Approval
```
1. Invoice for $2000 arrives at 9:00 AM Day 1
2. Approval card created
3. At 1:00 PM Day 1: Reminder sent (4 hours)
4. User doesn't respond
5. At 9:00 AM Day 2: check_approval_timeouts() runs
6. Auto-approves with auto_decided=True
7. Workflow executes
8. Dashboard shows "Auto-approved after 24h"
```

## Error Handling

**Duplicate Approval Attempt:**
- Check database for existing decision
- Return error: "Already decided: [approved/rejected] at [timestamp]"

**Invalid Approval ID:**
- Validate ID exists in database
- Return error: "Approval ID not found: {id}"

**Concurrent Approval:**
- Use database transaction locking
- First decision wins
- Second returns: "Already processed"

**Missing Configuration:**
- Use default values (threshold=$1000, timeout=24h)
- Log warning about using defaults

## Testing Requirements

Tests must cover:
- Threshold detection (above/below $1000)
- Contract detection (always requires approval)
- Approval card generation (proper markdown format)
- Approval processing (file moves, database updates)
- Rejection processing (reason logged, file moves)
- Timeout auto-approval (triggers after 24 hours)
- Reminder system (sends at 4 hours)
- Concurrent approval handling (no race conditions)
- Database integrity (approval records accurate)
- Audit logging (all decisions recorded immutably)

## Performance Considerations

- Approval detection: <100ms per item
- Card generation: <500ms
- Database queries: Use indexed fields (uuid, item_id)
- Timeout checking: Runs every 15 minutes (not real-time)
- Reminder checking: Runs every 30 minutes

## Security and Compliance

- All approval decisions logged immutably
- Timestamps recorded for all actions (requested, decided, reminded)
- Auto-decisions clearly flagged in audit trail
- Rejection reasons preserved for legal review
- Database approval records provide complete compliance trail
- No approval can be deleted, only marked as voided

---

**Status:** Core Silver Skill  
**Dependencies:** vault-management, database, enhanced-dashboard  
**Priority:** Critical (financial and legal oversight)  
**Test Coverage Required:** >90% (financial impact)