---
name: whatsapp-processor
description: Process WhatsApp messages and media. Use when new WhatsApp message detected by watcher. Parses message metadata, extracts sender and group info, detects urgency from keywords, downloads media attachments, and generates markdown summaries for vault storage.
---

# WhatsApp Processor Skill

## Purpose
Process WhatsApp business messages, group mentions, and media files into structured vault entries for tracking and action.

## When to Use
- New WhatsApp message detected by whatsapp_watcher.js
- Message contains business keywords (urgent, invoice, payment, etc.)
- Group message where you're mentioned
- Media attachments present (images, PDFs, videos)

## Core Capabilities

### parse_message(message_data) -> dict
Extracts structured metadata from WhatsApp message:
- Sender name and phone number
- Message timestamp
- Message body text
- Group name (if group message)
- Media metadata (type, size, filename)
- Returns: Structured dictionary

### detect_urgency(message_body) -> str
Analyzes content for priority level:
- Urgent keywords: urgent, asap, emergency, invoice, payment, deadline, critical
- Important keywords: review, approval, meeting, decision
- Normal: Everything else
- Returns: "urgent", "normal", or "low"

### download_media(message_data) -> list
Handles media attachments:
- Downloads images, PDFs, videos, audio
- Saves to Inbox/whatsapp/ with timestamp
- Generates unique filenames
- Preserves original filename in metadata
- Returns: List of saved file paths

### generate_markdown(parsed_data, urgency, media_files) -> str
Creates markdown summary file:
- Header: "WhatsApp: Message from {sender}"
- Sender details (name, number, group if applicable)
- Priority badge (🔴 urgent, 🟡 normal, 🔵 low)
- Message body
- Attachments section with links
- Action items checklist
- Processing timestamp
- Returns: Complete markdown string

### categorize_message(message_data) -> str
Determines message category:
- Business vs personal (keyword analysis)
- Invoice, receipt, contract, general
- Returns: Category string for routing

## Message Filtering

**Process if:**
- Contains urgent keywords
- From important contact list (Company_Handbook.md)
- Group message with your mention
- Has media attachments
- From verified business number

**Skip if:**
- Casual personal conversation
- Group chatter (no mention of you)
- Promotional/marketing messages
- WhatsApp status updates
- Known spam numbers

## Configuration (Company_Handbook.md)

```markdown
## WhatsApp Configuration

### Important Contacts
whatsapp_important_contacts:
  - "+1234567890"  # Client A
  - "+0987654321"  # Vendor B

### Urgent Keywords
whatsapp_urgent_keywords:
  - invoice
  - urgent
  - asap
  - payment
  - deadline

### Filter Settings
- Process business messages: Yes
- Skip personal chats: Yes
- Download media: Yes (all types)
```

## Integration

**Called by:** whatsapp_watcher.js (Node.js watcher)

**Calls:**
- vault-management (save markdown and media files)
- approval-manager (if high-value item detected)
- workflow-orchestrator (if workflow applicable)

**Triggers:** Appropriate workflow based on message content

## Testing Requirements

- Message parsing (all metadata extracted)
- Urgency detection (keywords properly classified)
- Media download (all file types)
- Markdown generation (proper format)
- Category assignment (accurate routing)
- Filter logic (process vs skip decisions)

---

**Status:** Silver Skill  
**Dependencies:** vault-management, approval-manager  
**Priority:** Medium  
**Test Coverage Required:** >80%