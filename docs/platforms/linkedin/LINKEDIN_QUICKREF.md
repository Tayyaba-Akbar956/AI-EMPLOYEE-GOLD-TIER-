# LinkedIn Posting - Quick Reference

## Quick Commands

```bash
# Create and post immediately
python -m src.cli.linkedin_cli create "Your content here" --importance normal

# Schedule at optimal time
python -m src.cli.linkedin_cli schedule "Your content here"

# Create with image
python -m src.cli.linkedin_cli create "Check this out!" --media "image.jpg"

# List pending approvals
python -m src.cli.linkedin_cli list pending

# Approve a post
python -m src.cli.linkedin_cli approve <post_id>

# Check status
python -m src.cli.linkedin_cli status <post_id>
```

## Importance Levels

- **low**: Personal updates (auto-approve)
- **normal**: Professional content (auto-approve) ← Default
- **high**: Company announcements (needs approval)
- **critical**: Major/legal posts (needs approval)

## Optimal Posting Times

- **Best:** Weekdays 9am-5pm
- **Avoid:** Weekends, early mornings, late evenings
- **Use:** `--smart-schedule` flag for automatic optimal timing

## Rate Limits

- **Max:** 25 posts per day
- **Resets:** Daily at midnight
- **Check:** `python -m src.cli.linkedin_cli list posted`

## Troubleshooting

```bash
# Re-authenticate
rm -rf AI_Employee_Vault/.linkedin_session/

# Retry failed post
python -m src.cli.linkedin_cli retry <post_id>

# View logs
cat AI_Employee_Vault/Logs/linkedin_posts/$(date +%Y-%m-%d).log
```

## Environment Setup

Add to `.env`:
```env
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_password
```

## Full Documentation

See `LINKEDIN_POSTING_GUIDE.md` for complete documentation.
