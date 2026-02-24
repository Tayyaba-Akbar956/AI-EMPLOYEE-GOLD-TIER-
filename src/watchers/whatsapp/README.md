# WhatsApp Watcher

Real-time WhatsApp message monitoring for AI Employee Silver Tier.

## Overview

This Node.js watcher monitors your WhatsApp messages and automatically processes important business communications. It uses the WhatsApp Web protocol via `whatsapp-web.js`.

## Features

- ✅ QR code authentication (one-time setup)
- ✅ Real-time message monitoring
- ✅ Intelligent filtering (urgent keywords, media, mentions)
- ✅ Media download (images, PDFs, videos, audio)
- ✅ Python processor integration
- ✅ Error handling and logging
- ✅ Graceful shutdown

## Prerequisites

- Node.js 16+ installed
- Python 3.8+ with AI Employee environment
- WhatsApp account

## Installation

```bash
# Install dependencies
npm install
```

This installs:
- `whatsapp-web.js` - WhatsApp Web protocol client
- `qrcode-terminal` - QR code display in terminal

## Usage

### First Time Setup

```bash
# Start the watcher
npm start
```

A QR code will appear in your terminal:

```
============================================================
WHATSAPP QR CODE AUTHENTICATION
============================================================

📱 Scan this QR code with your WhatsApp app:

[QR CODE APPEARS HERE]

Steps:
1. Open WhatsApp on your phone
2. Tap Menu (⋮) or Settings
3. Tap "Linked Devices"
4. Tap "Link a Device"
5. Scan the QR code above

============================================================
```

After scanning, the watcher will connect and start monitoring.

### Subsequent Runs

```bash
npm start
```

No QR code needed - the session is saved in `.wwebjs_auth/` folder.

## Message Filtering

### Messages that ARE processed:

- ✅ Contains urgent keywords: `urgent`, `asap`, `emergency`, `invoice`, `payment`, `deadline`
- ✅ Contains business keywords: `invoice`, `receipt`, `contract`, `meeting`, `project`
- ✅ Has media attachments (images, PDFs, documents)
- ✅ Group messages where you're mentioned
- ✅ Messages longer than 20 characters with business context

### Messages that are SKIPPED:

- ❌ Casual short messages: "hey", "hi", "ok", "thanks"
- ❌ Group messages without mention
- ❌ Personal conversations without keywords
- ❌ WhatsApp status updates

## Output

Processed messages are saved to:
```
AI_Employee_Vault/Inbox/whatsapp/YYYY-MM-DD-HHMMSS_whatsapp_SenderName.md
```

Media files are saved to:
```
AI_Employee_Vault/Inbox/whatsapp/filename.ext
```

## Example

### Input Message
```
From: John Doe (+1234567890)
Message: "URGENT: Please review the attached invoice for $5000"
Attachment: invoice.pdf
```

### Output File
```markdown
# WhatsApp: Message from John Doe

**Priority:** 🔴 URGENT
**From:** John Doe
**Number:** +1234567890
**Date:** 2026-02-18T10:00:00Z
**Chat Type:** Direct

---

## Message

URGENT: Please review the attached invoice for $5000

## Attachments

- [invoice.pdf](invoice.pdf)

## Action Items

- [ ] Review message
- [ ] Respond if needed
- [ ] Archive when complete

---

*Processed: 2026-02-18 10:00:15*
*Source: WhatsApp*
```

## Configuration

Edit `whatsapp_watcher.js` to customize:

```javascript
// Urgent keywords
const URGENT_KEYWORDS = [
    'urgent', 'asap', 'emergency', 'immediately', 'critical',
    'invoice', 'payment', 'due', 'overdue', 'deadline'
];

// Business keywords
const BUSINESS_KEYWORDS = [
    'invoice', 'receipt', 'contract', 'payment', 'proposal',
    'quote', 'order', 'delivery', 'meeting', 'project'
];
```

## Troubleshooting

### QR Code Not Appearing

```bash
# Delete session data and restart
rm -rf .wwebjs_auth
npm start
```

### Authentication Failed

1. Delete `.wwebjs_auth` folder
2. Restart watcher
3. Scan QR code again
4. Ensure phone has internet connection

### Messages Not Processing

Check the filter criteria:
- Does message contain urgent/business keywords?
- Does message have media?
- For group messages, are you mentioned?

View error log:
```bash
cat ../../AI_Employee_Vault/Logs/whatsapp_errors.log
```

### Python Processor Errors

Verify Python environment:
```bash
# From project root
python -c "from src.processors.whatsapp_processor import WhatsAppProcessor; print('OK')"
```

## Stopping the Watcher

Press `Ctrl+C` to gracefully shutdown:

```
⚠️  Shutting down WhatsApp watcher...
✅ WhatsApp watcher stopped
```

## Security

- ✅ QR code authentication (secure)
- ✅ Session data encrypted by WhatsApp
- ✅ No password storage
- ✅ Messages processed locally
- ✅ No cloud storage
- ✅ Casual messages not stored

## Performance

- **Memory:** ~150MB (Node.js + Puppeteer)
- **CPU:** Low (event-driven)
- **Message processing:** <500ms per message
- **Media download:** <5s (typical)

## Files

- `whatsapp_watcher.js` - Main watcher script
- `package.json` - Node.js dependencies
- `.wwebjs_auth/` - Session data (auto-created)

## Integration

This watcher integrates with:
- Python WhatsApp processor (`src/processors/whatsapp_processor.py`)
- Approval manager (for high-value items)
- Workflow orchestrator (for automated workflows)

## Support

For issues or questions:
1. Check `AI_Employee_Vault/Logs/whatsapp_errors.log`
2. Review `WHATSAPP_INTEGRATION_COMPLETE.md`
3. See `WHATSAPP_LINKEDIN_SETUP.md` for detailed setup

---

**Version:** 1.0.0
**Status:** Production Ready
**Last Updated:** 2026-02-18
