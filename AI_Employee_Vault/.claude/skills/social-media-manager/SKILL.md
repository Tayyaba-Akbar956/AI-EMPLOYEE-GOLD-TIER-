---
name: social-media-manager
description: Manage posts across Facebook, Instagram, and Twitter using Playwright browser automation
version: 1.0.0
trigger: Social media post requests, scheduled posts, content sharing
---

# Social Media Manager Skill

## Purpose

Automates posting to Facebook, Instagram, and Twitter (X) using Playwright browser automation. Same pattern as LinkedIn and WhatsApp in Silver Tier - no APIs, no OAuth, just browser automation with session persistence.

## Supported Platforms

### Facebook
- **Auth**: Playwright logs in with `FACEBOOK_EMAIL` + `FACEBOOK_PASSWORD`
- **Session**: Saved to `.facebook_session/`
- **Actions**: Text posts, image posts, link sharing
- **Testing**: Set visibility to "Only Me" during testing
- **Approval**: Always required before posting

### Instagram
- **Auth**: Playwright logs in with `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD`
- **Session**: Saved to `.instagram_session/`
- **Actions**: Image posts with captions, text-only stories
- **Testing**: Archive post immediately after verification
- **Approval**: Always required before posting

### Twitter/X
- **Auth**: Playwright logs in with `TWITTER_EMAIL` + `TWITTER_PASSWORD`
- **Session**: Saved to `.twitter_session/`
- **Actions**: Tweets (280 char limit enforced)
- **Testing**: Delete tweet immediately after verification
- **Approval**: Always required before posting

## Why Playwright Over APIs

✅ **No app review process** - Works immediately
✅ **No OAuth complexity** - Just email/password
✅ **No API credentials** - No tokens to manage
✅ **Proven pattern** - Already works for LinkedIn & WhatsApp
✅ **Session persistence** - Login once, reuse session
✅ **Visual verification** - Can screenshot for debugging

## Approval Workflow

All social posts require approval:

1. Claude drafts post content
2. Creates approval file: `/Pending_Approval/SOCIAL_FB_<timestamp>.md`
3. Ralph Wiggum blocks exit
4. Human reviews and approves via CLI
5. Orchestrator detects approval
6. Playwright posts to platform
7. Task moves to `/Done/`, logged to SQLite + JSON

## Approval File Format

```markdown
---
type: social_post
platform: facebook | instagram | twitter
approval_id: SOCIAL_FB_20260224_1000
visibility: public | friends | only_me
---

## Social Media Post Request

**Platform**: Facebook
**Visibility**: Public
**Scheduled**: Immediate

### Content

[Post content here - max 280 chars for Twitter]

### Media

- Image: /path/to/image.jpg (optional)
- Link: https://example.com (optional)

## Approval Required

This will be posted to Facebook.
Approve to proceed, reject to cancel.
```

## Facebook Poster

### Features
- Text-only posts
- Image posts with captions
- Link sharing with preview
- Visibility control (Public, Friends, Only Me)
- Session persistence across runs

### Playwright Selectors
```python
# Login
email_field = 'input[name="email"]'
password_field = 'input[name="pass"]'
login_button = 'button[name="login"]'

# Post creation
post_box = 'div[role="textbox"]'
photo_button = 'div[aria-label="Photo/video"]'
post_button = 'div[aria-label="Post"]'
visibility_button = 'div[aria-label="Select audience"]'
```

### Safe Testing
During testing, always set visibility to "Only Me":
```python
# Click visibility dropdown
page.click('div[aria-label="Select audience"]')
# Select "Only Me"
page.click('text="Only me"')
```

## Instagram Poster

### Features
- Image posts with captions
- Text-only stories
- Hashtag support
- Session persistence

### Playwright Selectors
```python
# Login
username_field = 'input[name="username"]'
password_field = 'input[name="password"]'
login_button = 'button[type="submit"]'

# Post creation
new_post_button = 'svg[aria-label="New post"]'
upload_input = 'input[type="file"]'
caption_field = 'textarea[aria-label="Write a caption..."]'
share_button = 'button:has-text("Share")'
```

### Safe Testing
Archive post immediately after verification:
```python
# Navigate to post
page.goto(f"https://instagram.com/p/{post_id}")
# Click options
page.click('button[aria-label="More options"]')
# Archive
page.click('button:has-text("Archive")')
```

## Twitter Poster

### Features
- Text tweets (280 char limit enforced)
- Image tweets
- Thread support
- Session persistence

### Character Limit Enforcement
```python
def enforce_twitter_limit(text: str) -> str:
    if len(text) <= 280:
        return text
    # Truncate with ellipsis
    return text[:277] + "..."
```

### Playwright Selectors
```python
# Login
username_field = 'input[autocomplete="username"]'
password_field = 'input[name="password"]'
login_button = 'div[data-testid="LoginForm_Login_Button"]'

# Tweet creation
tweet_box = 'div[data-testid="tweetTextarea_0"]'
tweet_button = 'div[data-testid="tweetButtonInline"]'
media_button = 'input[data-testid="fileInput"]'
```

### Safe Testing
Delete tweet immediately after verification:
```python
# Navigate to tweet
page.goto(f"https://twitter.com/user/status/{tweet_id}")
# Click options
page.click('div[data-testid="caret"]')
# Delete
page.click('div[data-testid="Dropdown"] >> text="Delete"')
# Confirm
page.click('div[data-testid="confirmationSheetConfirm"]')
```

## Session Management

All platforms use persistent sessions:

```python
from playwright.sync_api import sync_playwright

def get_browser_context(platform: str):
    session_dir = Path.home() / f".{platform}_session"
    session_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=str(session_dir / "state.json") if (session_dir / "state.json").exists() else None
        )
        return context
```

## Error Handling

If platform is unavailable:
1. Log error to SQLite + JSON
2. Create `SYSTEM_ALERT_<PLATFORM>_*.md`
3. Move task back to `/Needs_Action/`
4. Other platforms continue working

## Integration with Orchestrator

When orchestrator detects task type `social`:

1. Loads this SKILL.md
2. Triggers Claude Code with task + skill
3. Claude drafts post, creates approval file
4. Ralph Wiggum blocks until approved
5. Orchestrator executes via Playwright
6. Logs to SQLite + JSON
7. Updates Dashboard

## Weekly Summary

Track posts per platform:
```python
def get_weekly_summary():
    return {
        "facebook": count_posts_this_week("facebook"),
        "instagram": count_posts_this_week("instagram"),
        "twitter": count_posts_this_week("twitter"),
        "total": sum(...)
    }
```

## Environment Variables

```env
# Facebook
FACEBOOK_EMAIL=your@email.com
FACEBOOK_PASSWORD=<set>

# Instagram
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=<set>

# Twitter
TWITTER_EMAIL=your@email.com
TWITTER_PASSWORD=<set>
```

## Testing

Unit tests verify:
- Session creation and persistence
- Login flow for each platform
- Post creation with approval workflow
- Character limit enforcement (Twitter)
- Error handling when platform down
- Safe testing mode (Only Me, Archive, Delete)

## CEO Briefing Integration

The CEO briefing (Feature 8) will include:
- Posts per platform this week
- Engagement metrics (if available)
- Failed posts requiring attention

## Notes

- All platforms use Playwright - no API keys needed
- Sessions persist across runs - login once
- Always require approval before posting
- Safe testing rules prevent public embarrassment
- Same proven pattern as LinkedIn/WhatsApp in Silver
