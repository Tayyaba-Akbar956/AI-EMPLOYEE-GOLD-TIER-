# LinkedIn Autonomous Posting - Complete Guide

**Version:** 1.0.0
**Date:** 2026-02-20
**Status:** Production Ready

---

## Overview

Autonomous LinkedIn posting system using Playwright for browser automation. Supports text, images, links, and documents with smart scheduling, approval workflow, retry logic, and comprehensive logging.

---

## Features

✅ **Content Types:**
- Text-only posts (up to 3000 characters)
- Posts with images (multiple images supported)
- Posts with links (auto-preview)
- Posts with documents (PDF, presentations, etc.) — **Coming in Next Tier**

✅ **Scheduling:**
- Immediate posting
- Specific date/time scheduling
- Smart scheduling (optimal times: weekdays 9am-5pm)

✅ **Approval Workflow:**
- Auto-approve: Low and Normal importance
- Require approval: High and Critical importance
- 24-hour approval deadline
- Approval via CLI or Obsidian

✅ **Reliability:**
- Session persistence (7 days)
- Retry logic (2 attempts with 5-minute delays)
- Rate limiting (25 posts/day)
- Comprehensive error handling

✅ **Logging:**
- All actions logged to database
- Daily log files in `Logs/linkedin_posts/`
- Activity tracking for audit trail

---

## Installation

### 1. Install Dependencies

```bash
# Install Playwright
pip install playwright

# Install Playwright browsers
playwright install chromium

# Install other dependencies
pip install python-dotenv
```

### 2. Configure Environment Variables

Add to `.env` file:

```env
# LinkedIn credentials for authentication
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_password

# Optional: Custom session path
LINKEDIN_SESSION_PATH=AI_Employee_Vault/.linkedin_session
```

### 3. Initialize Database

The database schema is automatically created on first run. The `linkedin_posts` table will be added to your existing `ai_employee.db`.

---

## Quick Start

### Create a Simple Post

```bash
python -m src.cli.linkedin_cli create "Just shipped a new feature! 🚀" --importance normal
```

### Create Post with Image

```bash
python -m src.cli.linkedin_cli create "Check out our new design!" \
  --importance normal \
  --media "path/to/image.jpg"
```

### Create Post with Link

```bash
python -m src.cli.linkedin_cli create "Great article on AI trends" \
  --importance normal \
  --link "https://example.com/article"
```

### Schedule Post at Optimal Time

```bash
python -m src.cli.linkedin_cli schedule "Weekly update: Here's what we accomplished this week..." \
  --importance normal
```

### Schedule for Specific Time

```bash
python -m src.cli.linkedin_cli create "Product launch announcement" \
  --importance high \
  --time "2026-02-21T10:00:00"
```

---

## CLI Commands

### Create Post

```bash
python -m src.cli.linkedin_cli create "Content" [OPTIONS]

Options:
  --importance {low,normal,high,critical}  Importance level (default: normal)
  --media PATH                             Comma-separated image paths
  --link URL                               URL to share
  --document PATH                          Document path (PDF, etc.) — **Next Tier Only**
  --time DATETIME                          Schedule time (ISO format)
  --smart-schedule                         Auto-schedule at optimal time
```

### Schedule Post (Smart)

```bash
python -m src.cli.linkedin_cli schedule "Content" [OPTIONS]

# Automatically schedules at optimal time (weekdays 9am-5pm)
```

### List Posts

```bash
python -m src.cli.linkedin_cli list {pending|approved|posted|failed}

# Examples:
python -m src.cli.linkedin_cli list pending    # Posts needing approval
python -m src.cli.linkedin_cli list approved   # Ready to post
python -m src.cli.linkedin_cli list posted     # Already posted
python -m src.cli.linkedin_cli list failed     # Failed (can retry)
```

### Approve Post

```bash
python -m src.cli.linkedin_cli approve <post_id>
```

### Reject Post

```bash
python -m src.cli.linkedin_cli reject <post_id> --reason "Not appropriate"
```

### Check Post Status

```bash
python -m src.cli.linkedin_cli status <post_id>
```

### Retry Failed Post

```bash
python -m src.cli.linkedin_cli retry <post_id>
```

### Post Immediately

```bash
python -m src.cli.linkedin_cli post-now <post_id>
```

---

## Importance Levels

| Level | Description | Approval Required | Use Cases |
|-------|-------------|-------------------|-----------|
| **Low** | Personal updates | No | Casual content, personal thoughts |
| **Normal** | Professional content | No | Articles, insights, regular updates |
| **High** | Company announcements | Yes | Job postings, product launches |
| **Critical** | Major announcements | Yes | Legal notices, compliance posts |

---

## Approval Workflow

### High/Critical Posts

1. Post is created with `status='pending'`
2. Approval card generated in `Pending_Approval/linkedin_posts/`
3. User reviews and approves/rejects
4. Approved posts move to `status='approved'` and post at scheduled time

### Approval Methods

**Method 1: CLI**
```bash
# Approve
python -m src.cli.linkedin_cli approve <post_id>

# Reject
python -m src.cli.linkedin_cli reject <post_id> --reason "Reason here"
```

**Method 2: Obsidian**
- **Approve:** Move file from `Pending_Approval/linkedin_posts/` to `Approved/linkedin_posts/`
- **Reject:** Delete the approval card file

---

## Smart Scheduling

Smart scheduling automatically picks optimal posting times:

- **Weekdays:** 9am - 5pm
- **Avoids:** Weekends, early mornings, late evenings
- **Logic:**
  - If current time is optimal → post in 5 minutes
  - If after 5pm → schedule for next day 9am
  - If weekend → schedule for Monday 9am

### Example

```bash
# Run on Saturday at 3pm
python -m src.cli.linkedin_cli schedule "Weekend post"

# Result: Scheduled for Monday at 9am
```

---

## Rate Limiting

- **Limit:** 25 posts per day (LinkedIn allows ~30, we use conservative limit)
- **Enforcement:** Automatic check before posting
- **Behavior:** If limit exceeded, post marked as failed with error message

---

## Retry Logic

### Automatic Retry

- **Max Retries:** 2 attempts
- **Delay:** 5 minutes between retries
- **Triggers:** Network errors, timeouts, temporary failures

### Manual Retry

```bash
python -m src.cli.linkedin_cli retry <post_id>
```

### Retry States

1. **First Failure:** `status='failed'`, `retry_count=0`
2. **After Retry:** `status='approved'`, `retry_count=1`
3. **Max Retries:** `status='failed'`, `retry_count=2` (permanent failure)

---

## Session Management

### Session Persistence

- **Duration:** 7 days
- **Storage:** `AI_Employee_Vault/.linkedin_session/session.json`
- **Behavior:**
  - First run: Authenticate and save session
  - Subsequent runs: Reuse saved session
  - After 7 days: Re-authenticate automatically

### Manual Re-authentication

Delete session files to force re-authentication:

```bash
rm -rf AI_Employee_Vault/.linkedin_session/
```

---

## Programmatic Usage

### Python API

```python
from src.database.db_manager import DatabaseManager
from src.skills.linkedin_poster import LinkedInPoster

# Initialize
db = DatabaseManager()
poster = LinkedInPoster(db, 'AI_Employee_Vault')

# Create post
post_id = poster.create_post(
    content="My post content",
    importance_level="normal",
    smart_schedule=True
)

# Approve post
result = poster.approve_post(post_id)

# Post to LinkedIn
result = poster.post_to_linkedin(post_id)
```

---

## Integration with Existing System

### Database Integration

The `linkedin_posts` table is automatically added to your existing `ai_employee.db`:

```sql
CREATE TABLE linkedin_posts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    media_paths TEXT,
    link_url TEXT,
    document_path TEXT,
    scheduled_time TIMESTAMP,
    posted_time TIMESTAMP,
    status TEXT DEFAULT 'pending',
    importance_level TEXT DEFAULT 'normal',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 2,
    error_message TEXT,
    approval_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Approval System Integration

High/Critical posts automatically integrate with existing approval workflow:

- Creates approval record in `approvals` table
- Links via `approval_id` foreign key
- Follows same approval patterns as invoices/contracts

### Dashboard Integration

Add to `Dashboard.md`:

```markdown
## LinkedIn Posting

- **Pending Approval:** X posts
- **Scheduled:** X posts
- **Posted Today:** X posts
- **Failed (Retry):** X posts
```

---

## Troubleshooting

### Authentication Issues

**Problem:** Login fails or session expired

**Solution:**
```bash
# Delete session and re-authenticate
rm -rf AI_Employee_Vault/.linkedin_session/

# Verify credentials in .env
echo $LINKEDIN_EMAIL
echo $LINKEDIN_PASSWORD
```

### Posting Failures

**Problem:** Post fails with timeout

**Solution:**
```bash
# Check post status
python -m src.cli.linkedin_cli status <post_id>

# Retry manually
python -m src.cli.linkedin_cli retry <post_id>

# Check logs
cat AI_Employee_Vault/Logs/linkedin_posts/$(date +%Y-%m-%d).log
```

### Rate Limit Exceeded

**Problem:** "Daily rate limit exceeded" error

**Solution:**
- Wait until next day (resets at midnight)
- Check posted count: `python -m src.cli.linkedin_cli list posted`
- Adjust `MAX_DAILY_POSTS` in `linkedin_poster.py` if needed

### Headless Mode Issues

**Problem:** Posts fail in headless mode but work in visible mode

**Solution:**
```python
# Edit config to use visible browser for debugging
poster = LinkedInPoster(db, vault_path, config={'headless': False})
```

---

## Best Practices

### Content Guidelines

✅ **Do:**
- Keep posts under 3000 characters
- Use clear, professional language
- Include relevant hashtags
- Add images for better engagement
- Schedule during business hours

❌ **Don't:**
- Post too frequently (respect rate limits)
- Use all caps or excessive emojis
- Share sensitive company information
- Post on weekends (use smart scheduling)

### Scheduling Strategy

**Optimal Times:**
- **Tuesday-Thursday:** 9am-11am, 2pm-4pm
- **Monday/Friday:** 10am-3pm
- **Avoid:** Weekends, early mornings, late evenings

**Frequency:**
- **Maximum:** 25 posts/day
- **Recommended:** 2-5 posts/day
- **Ideal:** 1-2 posts/day for consistent engagement

### Approval Strategy

**Auto-approve (Normal/Low):**
- Regular updates
- Article shares
- Industry insights
- Personal achievements

**Require approval (High/Critical):**
- Company announcements
- Job postings
- Product launches
- Legal/compliance content
- Anything representing the company officially

---

## Monitoring & Logs

### Database Logs

All actions logged to `activity_log` table:

```sql
SELECT * FROM activity_log
WHERE component = 'linkedin-poster'
ORDER BY timestamp DESC
LIMIT 10;
```

### File Logs

Daily logs in `AI_Employee_Vault/Logs/linkedin_posts/`:

```bash
# View today's log
cat AI_Employee_Vault/Logs/linkedin_posts/$(date +%Y-%m-%d).log

# Watch live
tail -f AI_Employee_Vault/Logs/linkedin_posts/$(date +%Y-%m-%d).log
```

### Monitoring Commands

```bash
# Check pending approvals
python -m src.cli.linkedin_cli list pending

# Check failed posts
python -m src.cli.linkedin_cli list failed

# Check today's posts
python -m src.cli.linkedin_cli list posted | grep $(date +%Y-%m-%d)
```

---

## Advanced Configuration

### Custom Configuration

```python
config = {
    'headless': False,  # Show browser for debugging
    'session_path': '/custom/path',  # Custom session location
    'max_retries': 3,  # More retry attempts
    'retry_delay': 600  # 10-minute delay between retries
}

poster = LinkedInPoster(db, vault_path, config=config)
```

### Custom Optimal Times

Edit `linkedin_poster.py`:

```python
# Change optimal hours (default 9am-5pm)
OPTIMAL_HOURS = list(range(8, 20))  # 8am-8pm

# Change optimal days (default Mon-Fri)
OPTIMAL_DAYS = list(range(0, 6))  # Mon-Sat
```

### Custom Rate Limits

Edit `linkedin_poster.py`:

```python
# Change daily limit (default 25)
MAX_DAILY_POSTS = 30
```

---

## Security Considerations

### Credentials

- Store credentials in `.env` file (never commit)
- Use environment variables only
- Consider using password manager integration

### Session Files

- Session files contain authentication cookies
- Stored in `.linkedin_session/` (add to `.gitignore`)
- Auto-expire after 7 days

### Approval Workflow

- High/Critical posts require manual approval
- Prevents accidental posting of sensitive content
- Audit trail in database

---

## Testing

### Run Tests

```bash
# Run all LinkedIn poster tests
pytest tests/test_linkedin_poster.py -v

# Run specific test class
pytest tests/test_linkedin_poster.py::TestPostCreation -v

# Run with coverage
pytest tests/test_linkedin_poster.py --cov=src.skills.linkedin_poster
```

### Manual Testing

```bash
# 1. Create test post
python -m src.cli.linkedin_cli create "Test post - please ignore" --importance low

# 2. Check status
python -m src.cli.linkedin_cli list approved

# 3. Post immediately
python -m src.cli.linkedin_cli post-now <post_id>

# 4. Verify on LinkedIn
# Check your LinkedIn feed for the post
```

---

## FAQ

**Q: Can I schedule posts weeks in advance?**
A: Yes, use `--time` with any future date.

**Q: What happens if my computer is off at scheduled time?**
A: Posts will be processed when the system runs next. Consider running a scheduler (cron/Task Scheduler).

**Q: Can I edit a post after creation?**
A: Not currently. Delete and recreate if needed.

**Q: Does this work with LinkedIn company pages?**
A: Currently supports personal profiles only. Company page support and Document posting coming in the next tier.

**Q: What if I hit the rate limit?**
A: Posts will fail with rate limit error. They'll be retried the next day automatically.

**Q: Can I post to multiple accounts?**
A: Not currently. One account per configuration.

---

## Support

### Issues

Report issues at: `https://github.com/your-repo/issues`

### Logs

Include these when reporting issues:
- Post ID
- Error message
- Relevant log file: `Logs/linkedin_posts/YYYY-MM-DD.log`
- Database activity: `SELECT * FROM activity_log WHERE component='linkedin-poster'`

---

## Changelog

### v1.0.0 (2026-02-20)
- Initial release
- Text, image, link support
- Document support placeholder (Next Tier)
- Smart scheduling
- Approval workflow integration
- Retry logic
- Rate limiting
- Session persistence

---

*LinkedIn Autonomous Posting System - AI Employee Silver Tier*
