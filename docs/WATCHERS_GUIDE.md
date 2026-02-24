# 👁️ AI Employee Watchers Guide

This guide provides details on the four primary watchers that feed data into the AI Employee system.

---

## 1. Filesystem Watcher
**Location:** `src/watchers/filesystem_watcher.py`

### Purpose
Monitors a local directory for new files. It automatically categorizes, metadata-extracts, and organizes files (Invoices, Receipts, Contracts, Reports) into the Obsidian Vault.

### Setup & Execution
```bash
python -m src.watchers.filesystem_watcher ./watch_folder
```

### Key Features
- **Auto-Categorization:** Uses filename patterns and extensions.
- **Vault Organization:** Moves files to `Inbox/files/` or `Needs_Action/`.
- **Markdown Generation:** Creates a summary card for every organized file.

---

## 2. Gmail Watcher
**Location:** `src/watchers/gmail_watcher.py`

### Purpose
Polls the Gmail API for new messages matching specific criteria. It extracts content and attachments, preparing them for AI processing.

### Setup & Execution
1. Ensure `credentials.json` is in the root.
2. Run once to authenticate and generate `token.json`.
```bash
python -m src.watchers.gmail_watcher
```

### Key Features
- **Smart Filtering:** Only processes important/unread emails.
- **Attachment Handling:** Automatically saves and links attachments in the vault.

---

## 3. WhatsApp Watcher
**Location:** `src/watchers/whatsapp/whatsapp_watcher.js`

### Purpose
Uses `whatsapp-web.js` to monitor real-time messages. It filters for urgent keywords or important contacts.

### Setup & Execution
```bash
cd src/watchers/whatsapp
npm install
npm start
```
*Note: Requires scanning a QR code on first run.*

### Key Features
- **Real-time Monitoring:** Low latency message detection.
- **Media Support:** Captures images and documents sent via WhatsApp.

---

## 4. LinkedIn Watcher
**Location:** `src/watchers/linkedin_watcher.py`

### Purpose
Polls LinkedIn for job opportunities, DMs, and relevant connection requests.

### Setup & Execution
```bash
python -m src.watchers.linkedin_watcher
```
*Note: Requires LinkedIn API credentials in `.env`.*

### Key Features
- **Opportunity Detection:** Specifically looks for roles and projects.
- **Rate Limit Aware:** Polling intervals respect LinkedIn API limits.

---

## 🚀 Unified Management
Use the provided scripts in the `scripts/` folder to manage all watchers at once:
- `./scripts/start_all_watchers.sh`
- `./scripts/check_watchers.sh`
- `./scripts/stop_all_watchers.sh`

---
*AI Employee Silver Tier Documentation*
