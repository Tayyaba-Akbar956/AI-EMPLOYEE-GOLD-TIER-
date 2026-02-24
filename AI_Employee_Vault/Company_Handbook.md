# Company Handbook

**Version:** 2.0.0
**Last Updated:** 2026-02-17
**Tier:** Silver (Advanced Automation with Approval Workflows)

---

## Approval Workflow Configuration

### Thresholds
- **Invoice approval threshold:** $1000
- **Contract approval:** Always required
- **Expense report approval:** Required if >$500
- **Keyword trigger:** "approval required", "needs approval"

### Timeouts
- **Approval timeout:** 24 hours
- **Reminder schedule:** 4 hours after creation
- **Auto-approve on timeout:** Yes (configurable)

### Notifications
- **Dashboard alerts:** Yes
- **Email reminders:** No (Optional - configure in .env)

---

## Communication Rules

### Email Guidelines
- Reply to known contacts within 24 hours
- Flag emails with keywords: urgent, invoice, payment, contract
- Always use professional tone
- High-value invoices (>=$1000) require approval

### WhatsApp Guidelines
- Monitor direct messages with business keywords
- Group mentions of your name are flagged
- Media attachments downloaded and stored
- Urgent keywords: urgent, asap, emergency, immediately

### LinkedIn Guidelines
- Track job opportunities with salary info
- Relevant connection requests (industry, location)
- DMs with opportunity keywords: position, role, project, opportunity
- Ignore generic promotions and automated messages

### LinkedIn Posting Guidelines
- **Importance Levels:**
  - **Low:** Personal updates, casual content
  - **Normal:** Professional insights, article shares
  - **High:** Company announcements, job postings
  - **Critical:** Major announcements, legal/compliance posts
- **Approval Required:** High and Critical importance posts
- **Auto-post:** Low and Normal importance posts
- **Optimal Posting Times:** Weekdays 9am-5pm (avoid weekends)
- **Rate Limits:** Max 25 posts per day (LinkedIn limit ~30)
- **Retry Policy:** 2 retries with 5-minute delays
- **Session Duration:** 7 days (re-authenticate after expiry)

### Response Templates
- **Acknowledgment:** "Thank you for your message. I've received it and will respond within 24 hours."
- **Urgent:** "This has been flagged as urgent and moved to priority queue."
- **Needs Approval:** "This item requires your approval due to [reason]. Check Pending_Approval folder."
- **Approved:** "Approved. Processing workflow now."

---

## File Processing Rules

### Categorization
- **PDF invoices** → Pending_Approval/high_value/ (if >=$1000) or Needs_Action/urgent/
- **Contracts** → Pending_Approval/high_value/ (always)
- **Receipts** → Auto-processed, tracked in financial records
- **Regular documents** → Needs_Action/normal/

### Naming Convention
- **Format:** YYYY-MM-DD_category_description.ext
- **Example:** 2026-02-15_invoice_acme-corp.pdf
- **WhatsApp:** YYYY-MM-DD-HHMM_whatsapp_SenderName.md
- **LinkedIn:** YYYY-MM-DD-HHMM_linkedin_SenderName.md

### Priority Detection
**Urgent Keywords:**
- urgent, asap, emergency, immediately, critical
- invoice, payment due, past due, overdue
- contract, legal, compliance

**Normal Priority:**
- All other items

---

## Financial Categories

### Expense Categories
- **Meals:** Business meals and entertainment
- **Travel:** Flights, hotels, transportation
- **Supplies:** Office supplies and equipment
- **Software:** Subscriptions and licenses
- **Services:** Professional services, consulting
- **Marketing:** Advertising, promotion
- **Utilities:** Internet, phone, electricity
- **Miscellaneous:** Uncategorized expenses

### Budget Limits
- **Monthly Total:** $5000
- **Alert at:** 80% ($4000)
- **Critical at:** 95% ($4750)
- **Per-category budgets:** Defined monthly

---

## Planning System Configuration

### Simple Plan Triggers
- Tasks estimated < 2 hours
- 5-10 steps maximum
- Checklist format

### Detailed Plan Triggers
- Tasks estimated > 2 hours
- Multi-phase projects
- Requires timeline and budget
- Needs approval points

### Plan Keywords
- "plan", "organize", "prepare", "research", "coordinate"
- Multi-step tasks (>$500, >3 steps)

---

## Workflow Automation

### Invoice Processing Workflow
1. Extract amount and vendor
2. Check against approval threshold
3. Route to approval if needed
4. Create financial record
5. Set payment reminder

### Receipt Processing Workflow
1. Extract amount and category
2. Create expense record
3. Update monthly report
4. Archive to Done/

### Research Workflow
1. Identify research topic
2. Search and compile information
3. Generate report
4. Save to Reports/custom/

### File Organization Workflow
1. Detect file type
2. Extract metadata
3. Categorize (invoice/receipt/contract/document)
4. Rename per convention
5. Move to appropriate folder

### Email Response Workflow
1. Draft response (always requires approval)
2. Present for user review
3. Send if approved
4. Log to database

### Meeting Preparation Workflow
1. Extract meeting details
2. Check calendar
3. Prepare agenda
4. Set reminders

### Expense Report Workflow (Monthly)
1. Collect all receipts
2. Categorize expenses
3. Calculate totals
4. Generate PDF and CSV
5. Save to Reports/monthly/

---

## Logging Standards

### Log Entry Format
```
[TIMESTAMP] [LEVEL] [COMPONENT] Message
Example: [2026-02-15T10:30:00] [INFO] [EmailProcessor] Processed email from client@example.com
```

### Log Levels
- **DEBUG:** Detailed debugging information
- **INFO:** Normal operations
- **WARN:** Attention needed
- **ERROR:** Failed operations

### Log Locations
- **Daily logs:** Logs/YYYY-MM-DD.log
- **Approval logs:** Logs/approvals/YYYY-MM-DD-approvals.log
- **Workflow logs:** Logs/workflows/YYYY-MM-DD-workflows.log

---

## Report Schedule

### Weekly Reports
- **Generated:** Every Monday at 9:00 AM
- **Location:** Reports/weekly/
- **Format:** Markdown
- **Contains:** Items by source, categories processed, approvals, plans, time saved

### Monthly Reports
- **Generated:** 1st of month at 9:00 AM
- **Location:** Reports/monthly/
- **Format:** Markdown + CSV
- **Contains:** Financial summary, invoices, expenses, budget vs actual, recommendations

### Custom Reports
- **Generated:** On-demand
- **Location:** Reports/custom/
- **Trigger:** User request or specific event

---

## Database Configuration

### Connection Settings
- **Database Path:** AI_Employee_Vault/Database/ai_employee.db
- **Connection Pooling:** Enabled
- **Timeout:** 30 seconds
- **Backup:** Daily at 2:00 AM

### Retention Policy
- **Activity logs:** 1 year
- **Financial records:** 7 years (compliance)
- **Completed workflows:** 2 years
- **Rejected items:** 1 year

---

## Security & Compliance

### Approval Audit Trail
- All approval decisions logged immutably
- Timestamps for request, decision, reminders
- Auto-decisions clearly flagged
- Rejection reasons preserved

### Data Handling
- Sensitive financial data encrypted at rest
- API keys stored in .env (never committed)
- Database backups encrypted
- No PII in logs

---

*AI Employee Handbook v2.0.0 - Silver Tier*
