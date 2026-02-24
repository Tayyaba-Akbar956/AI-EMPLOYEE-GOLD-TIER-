"""
Twitter Poster - Gold Tier Feature 6
Posts to Twitter/X using Playwright browser automation
Same pattern as Facebook and Instagram
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from playwright.sync_api import sync_playwright

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager


class TwitterPoster:
    """
    Posts to Twitter/X using Playwright browser automation.
    Session persists across runs - login once, reuse session.
    Enforces 280 character limit.
    """

    def __init__(self, vault_path: Optional[str] = None, session_path: Optional[str] = None):
        """Initialize Twitter poster"""
        if vault_path is None:
            vault_path = os.environ.get('VAULT_PATH', str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault'))

        if session_path is None:
            session_path = str(Path.home() / '.twitter_session')

        self.vault_path = Path(vault_path)
        self.session_path = Path(session_path)
        self.platform = "twitter"

        # Ensure session directory exists
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = self.vault_path / "Database" / "ai_employee.db"
        if db_path.exists():
            self.db = DatabaseManager(str(db_path))
        else:
            self.db = None

    def enforce_character_limit(self, text: str) -> str:
        """
        Enforce Twitter's 280 character limit.
        Truncates with ellipsis if too long.
        """
        if len(text) <= 280:
            return text
        # Truncate to 277 chars + "..."
        return text[:277] + "..."

    def create_tweet(self, tweet_data: Dict[str, Any], require_approval: bool = True) -> Optional[str]:
        """
        Create a tweet.
        If require_approval=True, creates approval file and returns filename.
        Otherwise, posts directly to Twitter.
        """
        if require_approval:
            return self._create_approval_file(tweet_data)
        else:
            success, _ = self.post_to_twitter(tweet_data)
            return "posted" if success else None

    def _create_approval_file(self, tweet_data: Dict[str, Any]) -> str:
        """Create approval file for Twitter post"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_filename = f"SOCIAL_TW_{timestamp}.md"
        approval_path = self.vault_path / "Pending_Approval" / approval_filename

        # Ensure directory exists
        approval_path.parent.mkdir(parents=True, exist_ok=True)

        content = tweet_data.get("content", "")
        image_path = tweet_data.get("image_path", "")

        # Enforce character limit
        truncated_content = self.enforce_character_limit(content)
        was_truncated = len(content) > 280

        approval_content = f"""---
type: social_post
platform: twitter
approval_id: SOCIAL_TW_{timestamp}
---

## Social Media Post Request

**Platform**: Twitter/X
**Scheduled**: Immediate

### Content

{truncated_content}
"""

        if was_truncated:
            approval_content += f"""
**Note**: Original content was {len(content)} characters and has been truncated to meet Twitter's 280 character limit.
"""

        if image_path:
            approval_content += f"""
### Media

- Image: {image_path}
"""

        approval_content += """
## Approval Required

This will be posted to Twitter.
Approve to proceed, reject to cancel.
"""

        approval_path.write_text(approval_content, encoding='utf-8')
        return approval_filename

    def get_browser_context(self):
        """Get Playwright browser context with session persistence"""
        state_file = self.session_path / "state.json"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            if state_file.exists():
                context = browser.new_context(storage_state=str(state_file))
            else:
                context = browser.new_context()

            return p, browser, context

    def login(self, email: str, password: str) -> bool:
        """
        Login to Twitter and save session.
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to Twitter
            page.goto("https://twitter.com/i/flow/login")

            # Wait for username field
            page.wait_for_selector('input[autocomplete="username"]', timeout=10000)

            # Fill username/email
            page.fill('input[autocomplete="username"]', email)
            page.click('div[role="button"]:has-text("Next")')

            # Wait for password field
            page.wait_for_selector('input[name="password"]', timeout=10000)

            # Fill password
            page.fill('input[name="password"]', password)
            page.click('div[data-testid="LoginForm_Login_Button"]')

            # Wait for navigation
            page.wait_for_load_state("networkidle")

            # Save session
            state_file = self.session_path / "state.json"
            context.storage_state(path=str(state_file))

            page.close()
            context.close()
            browser.close()
            p.stop()

            return True

        except Exception as e:
            print(f"Twitter login error: {e}")
            return False

    def post_to_twitter(self, tweet_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Post to Twitter using Playwright.
        Returns (success, tweet_id) tuple.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to Twitter
            page.goto("https://twitter.com/home")

            # Wait for page load
            page.wait_for_load_state("networkidle")

            content = tweet_data.get("content", "")
            image_path = tweet_data.get("image_path")

            # Enforce character limit
            content = self.enforce_character_limit(content)

            # Click tweet box
            page.click('div[data-testid="tweetTextarea_0"]', timeout=5000)

            # Fill content
            page.fill('div[data-testid="tweetTextarea_0"]', content)

            # Upload image if provided
            if image_path and Path(image_path).exists():
                page.set_input_files('input[data-testid="fileInput"]', image_path)
                page.wait_for_timeout(2000)

            # Click tweet button
            page.click('div[data-testid="tweetButtonInline"]', timeout=5000)

            # Wait for tweet to post
            page.wait_for_timeout(3000)

            # Try to extract tweet ID from URL (if navigated to tweet)
            tweet_id = None
            try:
                current_url = page.url
                if "/status/" in current_url:
                    tweet_id = current_url.split("/status/")[1].split("?")[0]
            except:
                pass

            # Log success
            self.log_action(
                action_type="twitter_post",
                result="success",
                content=content[:100]
            )

            page.close()
            context.close()
            browser.close()
            p.stop()

            return True, tweet_id

        except Exception as e:
            print(f"Twitter post error: {e}")
            self.log_action(
                action_type="twitter_post",
                result="failure",
                error=str(e)
            )
            return False, None

    def delete_tweet(self, tweet_id: str) -> bool:
        """
        Delete a tweet by ID (for safe testing).
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to tweet
            page.goto(f"https://twitter.com/i/status/{tweet_id}")
            page.wait_for_load_state("networkidle")

            # Click options menu
            page.click('div[data-testid="caret"]', timeout=5000)
            page.wait_for_timeout(500)

            # Click Delete
            page.click('div[role="menuitem"]:has-text("Delete")', timeout=5000)
            page.wait_for_timeout(500)

            # Confirm deletion
            page.click('div[data-testid="confirmationSheetConfirm"]', timeout=5000)
            page.wait_for_timeout(2000)

            page.close()
            context.close()
            browser.close()
            p.stop()

            return True

        except Exception as e:
            print(f"Twitter delete error: {e}")
            return False

    def log_action(self, action_type: str, result: str, content: str = "", error: str = ""):
        """Log action to database"""
        if self.db is None:
            return

        timestamp = datetime.now().isoformat()

        try:
            self.db.log_activity({
                "timestamp": timestamp,
                "level": "INFO" if result == "success" else "ERROR",
                "component": "twitter_poster",
                "action": action_type,
                "item_id": "twitter",
                "details": f"Twitter post: {result}" + (f" - {error}" if error else "")
            })
        except Exception as e:
            print(f"Error logging to database: {e}")


def main():
    """Main entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Twitter Poster')
    parser.add_argument('--login', action='store_true', help='Login to Twitter')
    parser.add_argument('--email', type=str, help='Twitter email')
    parser.add_argument('--password', type=str, help='Twitter password')
    parser.add_argument('--tweet', type=str, help='Tweet content')
    parser.add_argument('--image', type=str, help='Image path')

    args = parser.parse_args()

    poster = TwitterPoster()

    if args.login:
        if not args.email or not args.password:
            print("Error: --email and --password required for login")
            return

        success = poster.login(args.email, args.password)
        print(f"Login {'successful' if success else 'failed'}")

    elif args.tweet:
        tweet_data = {
            "content": args.tweet,
            "image_path": args.image
        }

        success, tweet_id = poster.post_to_twitter(tweet_data)
        print(f"Tweet {'successful' if success else 'failed'}")
        if tweet_id:
            print(f"Tweet ID: {tweet_id}")

    else:
        print("Use --login or --tweet")


if __name__ == '__main__':
    main()
