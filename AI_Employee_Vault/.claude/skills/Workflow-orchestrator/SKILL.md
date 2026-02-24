# Workflow Orchestrator Skill

**Version:** 1.0.0
**Type:** Skill
**Category:** Automation & Orchestration

---

## Overview

The Workflow Orchestrator skill executes and manages multi-step automated workflows. It handles 7 different workflow types with state management, approval points, error recovery, and database integration.

## When to Use

Use this skill when:
- Invoice or receipt detected (financial workflows)
- Research request identified (keywords: research, find, compare)
- New file needs organization
- Important email requires response
- Meeting invite received
- End of month (expense report)
- Any multi-step automated process needed

## Capabilities

### 1. Seven Automated Workflows

#### Invoice Processing
- Validates invoice data
- Checks approval threshold ($1000)
- Creates financial record
- Sets payment reminder

#### Receipt Processing
- Validates receipt data
- Categorizes expense
- Creates expense record
- Updates budget tracking

#### Research
- Defines research scope
- Gathers information sources
- Analyzes collected data
- Generates research report

#### File Organization
- Detects file type
- Extracts metadata
- Categorizes file
- Moves to appropriate folder

#### Email Response
- Analyzes email content
- Drafts response
- Reviews draft (approval point)
- Sends email

#### Meeting Preparation
- Parses meeting details
- Creates agenda
- Gathers relevant materials
- Sends reminders

#### Expense Report
- Collects all expenses
- Categorizes by type
- Calculates totals
- Generates report
- Exports to CSV

### 2. State Management
- **Pause:** Stop workflow at current step
- **Resume:** Continue from paused step
- **Rollback:** Reset to beginning
- **Retry:** Retry failed workflow

### 3. Approval Handling
- Automatic pause at approval points
- User approval/rejection
- Configurable thresholds
- Rejection reasons logged

### 4. Error Recovery
- Automatic retry on failure (up to 3 times)
- Retry count tracking
- Failure state management
- Error logging

### 5. Database Integration
- Workflow state persistence
- Active workflow tracking
- Audit trail logging
- Concurrent workflow support

---

## Usage Examples

### Execute Workflow
```python
from src.skills.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator('AI_Employee_Vault')

# Invoice workflow
result = orchestrator.execute_workflow('invoice_processing', {
    'type': 'invoice',
    'amount': 1500,
    'vendor': 'Tech Supplies Inc'
})

print(f"Workflow ID: {result['workflow_id']}")
```

### Handle Approval
```python
# High-value invoice pauses for approval
workflow_id = result['workflow_id']

# Approve
orchestrator.approve_workflow(workflow_id)

# Or reject
orchestrator.reject_workflow(workflow_id, reason='Budget exceeded')
```

### State Management
```python
# Pause
orchestrator.pause_workflow(workflow_id)

# Resume
orchestrator.resume_workflow(workflow_id)

# Rollback
orchestrator.rollback_workflow(workflow_id)
```

---

**Status:** Production Ready
**Last Updated:** 2026-02-18
