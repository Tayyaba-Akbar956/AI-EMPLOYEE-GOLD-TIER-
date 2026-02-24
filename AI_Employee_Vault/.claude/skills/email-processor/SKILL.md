---
name: email-processor
description: Process and triage incoming Gmail messages. Use when Claude needs to parse emails, extract information, categorize by urgency (urgent/normal), generate markdown summaries, and route emails to appropriate vault folders (Inbox, Needs_Action/urgent, Needs_Action/normal).
---

# Email Processor Skill

Process and triage incoming Gmail messages with intelligent categorization, urgency detection, and automated routing to appropriate vault folders.

## Purpose

Transform raw email data into structured markdown files, automatically categorize emails by urgency and type, and route them to the correct locations in the AI_Employee_Vault for further action or archival.

## Core Capabilities

### 1. Email Parsing
Extract structured data from raw email:
```python
import email
from email.header import decode_header
from datetime import datetime

def parse_email(raw_email: str) -> dict:
    """
    Parse raw email into structured data.
    
    Args:
        raw_email: Raw email content (RFC 822 format)
    
    Returns:
        Dictionary with parsed email data
    """
    msg = email.message_from_string(raw_email)
    
    # Decode header if needed
    def decode_str(s):
        if s is None:
            return ""
        decoded = decode_header(s)
        return str(decoded[0][0], decoded[0][1] or 'utf-8') if isinstance(decoded[0][0], bytes) else decoded[0][0]
    
    # Extract body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode('utf-8', errors='ignore')
    
    return {
        'from': decode_str(msg.get('From', '')),
        'to': decode_str(msg.get('To', '')),
        'subject': decode_str(msg.get('Subject', 'No Subject')),
        'date': msg.get('Date', ''),
        'message_id': msg.get('Message-ID', ''),
        'body': body.strip(),
        'has_attachments': any(part.get_content_disposition() == 'attachment' for part in msg.walk())
    }
```

### 2. Urgency Detection
Categorize emails by priority:
```python
def detect_urgency(email_data: dict) -> dict:
    """
    Detect urgency level and category from email content.
    
    Args:
        email_data: Parsed email dictionary
    
    Returns:
        Dictionary with priority, category, and destination
    """
    subject = email_data['subject'].lower()
    body = email_data['body'].lower()
    combined = f"{subject} {body}"
    
    # Urgency keywords
    urgent_keywords = [
        'urgent', 'asap', 'immediate', 'critical', 'emergency',
        'overdue', 'past due', 'final notice', 'action required',
        'time sensitive', 'deadline', 'expires'
    ]
    
    # Important keywords
    important_keywords = [
        'invoice', 'payment', 'bill', 'quote', 'proposal',
        'contract', 'agreement', 'due date', 'review needed',
        'approval', 'signature required'
    ]
    
    # Check for urgency
    is_urgent = any(keyword in combined for keyword in urgent_keywords)
    is_important = any(keyword in combined for keyword in important_keywords)
    
    # Determine priority
    if is_urgent or (is_important and 'invoice' in subject):
        return {
            'priority': 'urgent',
            'category': 'action_required',
            'destination': 'Needs_Action/urgent/',
            'reason': 'Contains urgent keywords or invoice'
        }
    elif is_important:
        return {
            'priority': 'normal',
            'category': 'action_required',
            'destination': 'Needs_Action/normal/',
            'reason': 'Contains important keywords'
        }
    else:
        return {
            'priority': 'low',
            'category': 'informational',
            'destination': 'Inbox/emails/',
            'reason': 'No urgent or important keywords detected'
        }
```

### 3. Markdown Generation
Create markdown summary of email:
```python
def generate_email_markdown(email_data: dict, urgency: dict) -> str:
    """
    Generate markdown summary from email data.
    
    Args:
        email_data: Parsed email dictionary
        urgency: Urgency classification dictionary
    
    Returns:
        Formatted markdown string
    """
    timestamp = datetime.now().isoformat()
    
    # Extract sender name and email
    from_field = email_data['from']
    
    markdown = f"""# Email: {email_data['subject']}

**From:** {from_field}
**To:** {email_data['to']}
**Date:** {email_data['date']}
**Priority:** {urgency['priority'].upper()}
**Category:** {urgency['category']}

## Classification
- **Destination:** {urgency['destination']}
- **Reason:** {urgency['reason']}
- **Has Attachments:** {'Yes' if email_data['has_attachments'] else 'No'}

## Email Body

{email_data['body']}

## Metadata
- **Message ID:** {email_data['message_id']}
- **Processed:** {timestamp}

## Actions Needed
- [ ] Review email content
- [ ] Respond if required
- [ ] Move to Done when complete

---
*Processed by email-processor skill at {timestamp}*
"""
    return markdown
```

### 4. Email Routing
Save email to appropriate folder:
```python
import re
from pathlib import Path

def route_email(email_data: dict, urgency: dict, markdown_content: str) -> dict:
    """
    Save email markdown to appropriate vault location.
    
    Args:
        email_data: Parsed email data
        urgency: Urgency classification
        markdown_content: Generated markdown
    
    Returns:
        Result dictionary with status and file path
    """
    # Create safe filename from subject
    subject = email_data['subject']
    safe_subject = re.sub(r'[^\w\s-]', '', subject)[:50]
    safe_subject = re.sub(r'[-\s]+', '-', safe_subject).strip('-')
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M')
    filename = f"{timestamp}_email_{safe_subject}.md"
    
    # Determine full path
    vault_path = Path("AI_Employee_Vault")
    destination = vault_path / urgency['destination']
    destination.mkdir(parents=True, exist_ok=True)
    
    file_path = destination / filename
    
    # Write file
    try:
        file_path.write_text(markdown_content, encoding='utf-8')
        
        # Log success
        from vault_management import write_log
        write_log('INFO', 'EmailProcessor', 
                  f"Routed email '{subject}' to {urgency['destination']}")
        
        return {
            'status': 'success',
            'file_path': str(file_path),
            'destination': urgency['destination'],
            'priority': urgency['priority']
        }
    except Exception as e:
        from vault_management import write_log
        write_log('ERROR', 'EmailProcessor', 
                  f"Failed to route email: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
```

## Complete Processing Pipeline

Process email end-to-end:
```python
def process_email_complete(raw_email: str) -> dict:
    """
    Complete email processing pipeline.
    
    Steps:
    1. Parse raw email
    2. Detect urgency
    3. Generate markdown
    4. Route to vault
    5. Update dashboard
    
    Args:
        raw_email: Raw email content
    
    Returns:
        Processing result dictionary
    """
    # Step 1: Parse
    email_data = parse_email(raw_email)
    
    # Step 2: Categorize
    urgency = detect_urgency(email_data)
    
    # Step 3: Generate markdown
    markdown = generate_email_markdown(email_data, urgency)
    
    # Step 4: Route
    result = route_email(email_data, urgency, markdown)
    
    # Step 5: Update dashboard (if successful)
    if result['status'] == 'success':
        from dashboard_updater import add_activity, update_daily_stats
        add_activity(f"Processed email from {email_data['from']} → {urgency['destination']}")
        update_daily_stats('email')
    
    return result
```

## Urgency Keywords Reference

### Urgent Keywords (Priority 1)
- urgent, asap, immediate, critical, emergency
- overdue, past due, final notice
- action required, time sensitive
- deadline, expires

### Important Keywords (Priority 2)
- invoice, payment, bill, quote
- proposal, contract, agreement
- due date, review needed
- approval, signature required

### Informational Keywords (Priority 3)
- newsletter, update, announcement
- confirmation, receipt, thank you
- fyi, for your information

## Email Categories

**action_required**: Email needs action (urgent or normal priority)
**informational**: Email is FYI only (low priority)
**automated**: System-generated emails (typically low priority)
**spam**: Potential spam (move to separate folder)

## Routing Logic

```
IF contains urgent keywords OR (contains "invoice" in subject AND important keywords):
    → Needs_Action/urgent/
    
ELSE IF contains important keywords:
    → Needs_Action/normal/
    
ELSE:
    → Inbox/emails/
```

## Error Handling

- **Malformed email**: Extract what's possible, log warning, save to Inbox
- **Missing sender**: Mark as "Unknown Sender", flag for review
- **Encoding issues**: Try UTF-8, then Latin-1, then ignore errors
- **Large email**: Truncate body to 10,000 chars, note truncation
- **Missing subject**: Use "No Subject" as placeholder

## Integration with Other Skills

- Uses `vault-management` to save files and write logs
- Calls `dashboard-updater` after successful processing
- Reads categorization rules from `Company_Handbook.md`

## Examples

### Example 1: Process Urgent Invoice Email
```python
raw_email = """From: vendor@acme.com
To: me@company.com
Subject: URGENT: Invoice #12345 Due Today
Date: Fri, 15 Feb 2026 10:30:00 +0000

Your invoice #12345 for $5,000 is due today.
Please process payment immediately.
"""

result = process_email_complete(raw_email)
# Result: routed to Needs_Action/urgent/
```

### Example 2: Process Newsletter
```python
raw_email = """From: newsletter@techco.com
To: me@company.com
Subject: Weekly Tech News
Date: Fri, 15 Feb 2026 09:00:00 +0000

This week's top stories...
"""

result = process_email_complete(raw_email)
# Result: routed to Inbox/emails/
```

## Testing

Test email processing:
```python
def test_email_processor():
    """Test email processing with sample data"""
    test_email = """From: test@example.com
Subject: Test Email
Date: 2026-02-15

This is a test.
"""
    result = process_email_complete(test_email)
    assert result['status'] == 'success'
    assert 'file_path' in result
```

## Notes

- Email processor only handles parsing and routing
- Actual email fetching is done by the watcher (gmail_watcher.py)
- Attachments are noted but not downloaded in Bronze tier
- All processing is logged for audit trail