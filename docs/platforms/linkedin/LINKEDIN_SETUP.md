# LinkedIn Autonomous Posting - Setup Guide

## Prerequisites

- Python 3.8+
- LinkedIn account
- AI Employee Silver Tier system installed

---

## Step 1: Install Dependencies

```bash
# Install Playwright
pip install playwright

# Install Playwright browsers (Chromium)
playwright install chromium

# Verify installation
playwright --version
```

---

## Step 2: Configure Credentials

### Create/Edit `.env` File

Add your LinkedIn credentials to `.env` in the project root:

```env
# LinkedIn Authentication
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_secure_password

# Optional: Custom session path
LINKEDIN_SESSION_PATH=AI_Employee_Vault/.linkedin_session
```

**Security Notes:**
- Never commit `.env` to version control
- Use a strong, unique password
- Consider enabling 2FA on LinkedIn (may require manual intervention)

---

## Step 3: Initialize Database

The database schema is automatically created on first use. To manually initialize:

```bash
python -c "from src.database.db_manager import DatabaseManager; DatabaseManager()"
```

This creates the `linkedin_posts` table in your existing `ai_employee.db`.

---

## Step 4: Test Authentication

### First-Time Authentication

```bash
# Create a test post (will trigger authentication)
python -m src.cli.linkedin_cli create "Test post - please ignore" --importance low
```

**What happens:**
1. Browser opens (visible mode for first auth)
2. Logs into LinkedIn with your credentials
3. Saves session for future use (7 days)
4. Creates the post in database

**If authentication fails:**
- Check credentials in `.env`
- Ensure LinkedIn account is active
- Check for 2FA requirements
- Review logs: `AI_Employee_Vault/Logs/linkedin_posts/`

---

## Step 5: Verify Setup

### Check Database

```bash
# Verify table exists
python -c "from src.database.db_manager import DatabaseManager; db = DatabaseManager(); print(db.get_tables())"

# Should include 'linkedin_posts'
```

### List Posts

```bash
python -m src.cli.linkedin_cli list approved
```

### Check Session

```bash
# Session files should exist
ls AI_Employee_Vault/.linkedin_session/
# Should show: session.json, timestamp.txt
```

---

## Step 6: Create Your First Real Post

### Simple Text Post

```bash
python -m src.cli.linkedin_cli create "Excited to share that I've automated my LinkedIn posting! 🚀" --importance normal
```

### Post with Image

```bash
python -m src.cli.linkedin_cli create "Check out this amazing view!" \
  --importance normal \
  --media "path/to/your/image.jpg"
```

### Scheduled Post

```bash
python -m src.cli.linkedin_cli schedule "Weekly update: Here's what I accomplished this week..." \
  --importance normal
```

---

## Step 7: Set Up Automation (Optional)

### Option A: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add job to check and post every 15 minutes
*/15 * * * * cd /path/to/AI_EMPLOYEE_SILVER && python -m src.cli.linkedin_cli post-pending >> logs/cron.log 2>&1
```

### Option B: Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily, repeat every 15 minutes
4. Action: Start a program
   - Program: `python`
   - Arguments: `-m src.cli.linkedin_cli post-pending`
   - Start in: `C:\path\to\AI_EMPLOYEE_SILVER`

### Option C: Python Script

Create `auto_poster.py`:

```python
#!/usr/bin/env python3
"""Automatic LinkedIn poster - runs continuously."""

import time
from datetime import datetime
from src.database.db_manager import DatabaseManager
from src.skills.linkedin_poster import LinkedInPoster

def main():
    db = DatabaseManager()
    poster = LinkedInPoster(db, 'AI_Employee_Vault')

    print("LinkedIn Auto-Poster started")

    while True:
        try:
            # Get posts ready to post
            posts = db.get_pending_linkedin_posts()

            for post in posts:
                print(f"Posting: {post['id'][:8]}...")
                result = poster.post_to_linkedin(post['id'])

                if result['success']:
                    print(f"  ✓ Posted successfully")
                else:
                    print(f"  ✗ Failed: {result['error']}")

                # Wait between posts
                time.sleep(60)

            # Check every 5 minutes
            time.sleep(300)

        except KeyboardInterrupt:
            print("\nStopping auto-poster...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
```

Run it:
```bash
python auto_poster.py
```

---

## Step 8: Configure Company Handbook

The configuration is already added to `Company_Handbook.md`. Verify it:

```bash
grep -A 10 "LinkedIn Posting Guidelines" AI_Employee_Vault/Company_Handbook.md
```

Should show:
- Importance levels
- Approval requirements
- Optimal posting times
- Rate limits
- Retry policy

---

## Step 9: Test Approval Workflow

### Create High-Importance Post

```bash
python -m src.cli.linkedin_cli create "Major company announcement!" --importance high
```

**What happens:**
1. Post created with `status='pending'`
2. Approval card generated in `Pending_Approval/linkedin_posts/`
3. Notification in dashboard (if integrated)

### Approve the Post

```bash
# List pending
python -m src.cli.linkedin_cli list pending

# Approve
python -m src.cli.linkedin_cli approve <post_id>
```

---

## Step 10: Monitor & Maintain

### Daily Checks

```bash
# Check pending approvals
python -m src.cli.linkedin_cli list pending

# Check failed posts
python -m src.cli.linkedin_cli list failed

# View today's activity
cat AI_Employee_Vault/Logs/linkedin_posts/$(date +%Y-%m-%d).log
```

### Weekly Maintenance

```bash
# Clean up old sessions (if needed)
find AI_Employee_Vault/.linkedin_session/ -mtime +7 -delete

# Archive old logs
gzip AI_Employee_Vault/Logs/linkedin_posts/*.log
```

### Monthly Review

```sql
-- Check posting stats
SELECT
    status,
    COUNT(*) as count,
    AVG(retry_count) as avg_retries
FROM linkedin_posts
WHERE created_at >= date('now', '-30 days')
GROUP BY status;
```

---

## Troubleshooting Setup

### Issue: "Module not found"

```bash
# Ensure you're in project root
cd /path/to/AI_EMPLOYEE_SILVER

# Install dependencies
pip install -r requirements.txt
```

### Issue: "Playwright not found"

```bash
# Reinstall Playwright
pip uninstall playwright
pip install playwright
playwright install chromium
```

### Issue: "Database locked"

```bash
# Check for other processes
ps aux | grep python

# Kill if needed
kill <pid>
```

### Issue: "Authentication failed"

```bash
# Delete session and retry
rm -rf AI_Employee_Vault/.linkedin_session/

# Verify credentials
cat .env | grep LINKEDIN

# Try with visible browser
# Edit linkedin_poster.py temporarily:
# config = {'headless': False}
```

### Issue: "Permission denied"

```bash
# Make CLI executable
chmod +x src/cli/linkedin_cli.py

# Or use python -m
python -m src.cli.linkedin_cli
```

---

## Next Steps

1. **Read Full Documentation:** `docs/LINKEDIN_POSTING_GUIDE.md`
2. **Quick Reference:** `docs/LINKEDIN_QUICKREF.md`
3. **Run Tests:** `pytest tests/test_linkedin_poster.py`
4. **Integrate with Dashboard:** Update `Dashboard.md` to show LinkedIn stats
5. **Set Up Monitoring:** Configure alerts for failed posts

---

## Support

If you encounter issues:

1. Check logs: `AI_Employee_Vault/Logs/linkedin_posts/`
2. Review database: `SELECT * FROM activity_log WHERE component='linkedin-poster'`
3. Test authentication: Delete session and re-authenticate
4. Verify credentials: Check `.env` file
5. Run tests: `pytest tests/test_linkedin_poster.py -v`

---

## Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] LinkedIn credentials are secure
- [ ] Session files are in `.gitignore`
- [ ] High/Critical posts require approval
- [ ] Logs don't contain sensitive data
- [ ] Rate limits are configured
- [ ] Approval workflow is tested

---

*Setup complete! You're ready to automate LinkedIn posting.*
