---
name: dashboard-updater
description: Generate real-time multi-platform dashboard. Use when any system activity occurs or on scheduled refresh. Aggregates counts across all 4 sources, displays pending approvals, shows active plans with progress, tracks workflow status, calculates financial metrics, and updates Dashboard.md in real-time.
---

# Enhanced Dashboard Skill

## Purpose
Provide real-time visibility into all system activity with multi-platform tracking, approval queue, workflow status, and financial metrics in one unified Dashboard.md view.

## When to Use
- Any item processed (email, file, WhatsApp, LinkedIn)
- Approval created, decided, or timed out
- Plan created, updated, or completed
- Workflow starts, progresses, or completes
- Scheduled refresh (every 60 seconds)
- User opens/views Dashboard.md

## Core Capabilities

### aggregate_multi_platform_counts() -> dict
Counts items across all 4 sources:
- Gmail: Counts files in Inbox/emails/
- Filesystem: Counts files in Inbox/files/
- WhatsApp: Counts files in Inbox/whatsapp/
- LinkedIn: Counts files in Inbox/linkedin/
- Categorizes by: today, pending, urgent, normal
- Returns: Nested dictionary by source and category

### display_approval_queue() -> str
Shows pending approvals with details:
- Queries database for pending approvals
- Calculates time waiting (hours/minutes)
- Computes deadline remaining
- Formats with priority indicators (🔴🟡)
- Sorts by urgency (most urgent first)
- Returns: Markdown formatted list

### show_active_plans() -> str
Lists currently executing plans:
- Reads Plans/active/ folder
- Parses each plan for progress
- Calculates completion percentage
- Identifies current phase/step
- Shows status indicators (⏳✅⚠️)
- Returns: Markdown plan list with progress

### track_workflow_status() -> str
Displays running workflows:
- Queries database for active workflows
- Gets current step number and description
- Shows workflow type and item
- Calculates estimated completion
- Returns: Markdown workflow list

### calculate_financial_metrics() -> dict
Computes financial summary:
- Pending invoices: Sum and count
- Paid this month: Sum and count
- Monthly expenses: Sum by category
- Budget usage: Spent / allocated
- Overdue amounts: Sum and count
- Returns: Financial metrics dictionary

### generate_recent_activity(limit=10) -> list
Gets last N activities:
- Queries activity_log table
- Formats with timestamps and icons
- Groups similar activities
- Returns: List of activity strings

### check_system_status() -> dict
Monitors all components:
- Checks if watchers are running (process detection)
- Database connection and health
- Last backup timestamp
- Disk space usage
- Returns: System status dictionary

### generate_dashboard() -> str
Creates complete Dashboard.md:
- Multi-platform summary table
- Pending approvals section (if any)
- Active plans section (if any)
- Workflow status section (if any)
- Financial tracking section
- Recent activity log
- System status section
- Returns: Complete markdown document

### update_dashboard_realtime(event_type, event_data)
Triggers immediate dashboard refresh:
- Incrementally updates based on event
- Doesn't regenerate entire dashboard
- Updates specific sections only
- Writes to Dashboard.md atomically
- Faster than full regeneration

## Dashboard Template Structure

```markdown
# AI Employee Dashboard - Silver Tier

**Last Updated:** {timestamp}
**Status:** {emoji} {status}

## 📊 Multi-Platform Summary
| Source | Today | Pending | Urgent | Normal |
|--------|-------|---------|--------|--------|
| 📧 Gmail | {count} | {count} | {count} | {count} |
| 📄 Files | {count} | {count} | {count} | {count} |
| 📱 WhatsApp | {count} | {count} | {count} | {count} |
| 💼 LinkedIn | {count} | {count} | {count} | {count} |
| **TOTAL** | **{total}** | **{total}** | **{total}** | **{total}** |

## ⏳ Pending Your Approval ({count})
{approval_list or "✅ No items pending approval"}

## 📋 Active Plans ({count})
{plan_list or "📝 No active plans"}

## 🔄 Workflow Status ({count})
{workflow_list or "No active workflows"}

## 💰 Financial Tracking
**This Month:**
- Pending Invoices: ${amount} ({count} items)
- Paid This Month: ${amount} ({count} items)
- Expenses: ${amount} ({count} items)
- Budget: ${spent}/${budget} ({percent}%) {status_indicator}

## 📝 Recent Activity
{last_10_activities}

## ⚙️ System Status
- Gmail Watcher: {status} (last check: {time})
- Filesystem Watcher: {status} (last check: {time})
- WhatsApp Watcher: {status} (last check: {time})
- LinkedIn Watcher: {status} (last check: {time})
- Database: {status} ({record_count} records)
- Last Backup: {timestamp}

---
*AI Employee v2.0.0 - Silver Tier*
```

## Update Frequency

- **Real-time**: On any item processed (immediate)
- **Scheduled**: Every 60 seconds (status checks, counts)
- **On-demand**: When Dashboard.md opened in Obsidian

## Integration

**Called by:** ALL skills after operations

**Reads from:**
- All vault folders (for counts)
- Database (approvals, plans, workflows, financials)
- System processes (watcher status)

**Writes to:** Dashboard.md (atomic writes)

## Testing Requirements

- Multi-platform counting (accurate across sources)
- Approval queue display (all pending shown)
- Plan progress calculation (correct percentages)
- Workflow status tracking (reflects database state)
- Financial totals (exact calculations)
- Real-time updates (triggers on events)
- Performance (updates complete in <1 second)

---

**Status:** Core Silver Skill  
**Dependencies:** database, vault-management, ALL other skills  
**Priority:** High (visibility critical)  
**Test Coverage Required:** >85%