"""
Facebook Poster - Gold Tier Feature 5 (Part 1)
Posts to Facebook using Playwright browser automation
Same pattern as LinkedIn in Silver Tier
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager


class FacebookPoster:
    """
    Posts to Facebook using Playwright browser automation.
    Session persists across runs - login once, reuse session.
    """

    def __init__(self, vault_path: Optional[str] = None, session_path: Optional[str] = None):
        """Initialize Facebook poster"""
        if vault_path is None:
            vault_path = os.environ.get('VAULT_PATH', str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault'))

        if session_path is None:
            session_path = str(Path.home() / '.facebook_session')

        self.vault_path = Path(vault_path)
        self.session_path = Path(session_path)
        self.platform = "facebook"

        # Ensure session directory exists
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = self.vault_path / "Database" / "ai_employee.db"
        if db_path.exists():
            self.db = DatabaseManager(str(db_path))
        else:
            self.db = None

    def create_post(self, post_data: Dict[str, Any], require_approval: bool = True) -> Optional[str]:
        """
        Create a Facebook post.
        If require_approval=True, creates approval file and returns filename.
        Otherwise, posts directly to Facebook.
        """
        if require_approval:
            return self._create_approval_file(post_data)
        else:
            success = self.post_to_facebook(post_data)
            return "posted" if success else None

    def _create_approval_file(self, post_data: Dict[str, Any]) -> str:
        """Create approval file for Facebook post"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_filename = f"SOCIAL_FB_{timestamp}.md"
        approval_path = self.vault_path / "Pending_Approval" / approval_filename

        # Ensure directory exists
        approval_path.parent.mkdir(parents=True, exist_ok=True)

        content = post_data.get("content", "")
        visibility = post_data.get("visibility", "public")
        image_path = post_data.get("image_path", "")

        approval_content = f"""---
type: social_post
platform: facebook
approval_id: SOCIAL_FB_{timestamp}
visibility: {visibility}
---

## Social Media Post Request

**Platform**: Facebook
**Visibility**: {visibility.title()}
**Scheduled**: Immediate

### Content

{content}
"""

        if image_path:
            approval_content += f"""
### Media

- Image: {image_path}
"""

        approval_content += """
## Approval Required

This will be posted to Facebook.
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
        Login to Facebook and save session.
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to Facebook
            page.goto("https://www.facebook.com")

            # Fill login form
            page.fill('input[name="email"]', email)
            page.fill('input[name="pass"]', password)
            page.click('button[name="login"]')

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
            print(f"Facebook login error: {e}")
            return False

    def post_to_facebook(self, post_data: Dict[str, Any]) -> bool:
        """
        Post to Facebook using Playwright.
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to Facebook
            page.goto("https://www.facebook.com")

            # Wait for page load
            page.wait_for_load_state("networkidle")

            # Click on post box
            page.click('div[role="textbox"]')

            # Fill content
            content = post_data.get("content", "")
            page.fill('div[role="textbox"]', content)

            # Set visibility if specified
            visibility = post_data.get("visibility", "public")
            if visibility == "only_me":
                # Click visibility dropdown
                page.click('div[aria-label*="audience"]', timeout=5000)
                # Select "Only me"
                page.click('text="Only me"', timeout=5000)

            # Upload image if provided
            image_path = post_data.get("image_path")
            if image_path and Path(image_path).exists():
                # Click photo/video button
                page.click('div[aria-label="Photo/video"]')
                # Upload file
                page.set_input_files('input[type="file"]', image_path)
                # Wait for upload
                page.wait_for_timeout(2000)

            # Click post button
            page.click('div[aria-label="Post"]')

            # Wait for post to complete
            page.wait_for_timeout(3000)

            # Log success
            self.log_action(
                action_type="facebook_post",
                result="success",
                content=content[:100]
            )

            page.close()
            context.close()
            browser.close()
            p.stop()

            return True

        except Exception as e:
            print(f"Facebook post error: {e}")
            self.log_action(
                action_type="facebook_post",
                result="failure",
                error=str(e)
            )
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
                "component": "facebook_poster",
                "action": action_type,
                "item_id": "facebook",
                "details": f"Facebook post: {result}" + (f" - {error}" if error else "")
            })
        except Exception as e:
            print(f"Error logging to database: {e}")


def main():
    """Main entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Facebook Poster')
    parser.add_argument('--login', action='store_true', help='Login to Facebook')
    parser.add_argument('--email', type=str, help='Facebook email')
    parser.add_argument('--password', type=str, help='Facebook password')
    parser.add_argument('--post', type=str, help='Post content')
    parser.add_argument('--visibility', type=str, default='only_me', help='Post visibility')

    args = parser.parse_args()

    poster = FacebookPoster()

    if args.login:
        if not args.email or not args.password:
            print("Error: --email and --password required for login")
            return

        success = poster.login(args.email, args.password)
        print(f"Login {'successful' if success else 'failed'}")

    elif args.post:
        post_data = {
            "content": args.post,
            "visibility": args.visibility
        }

        success = poster.post_to_facebook(post_data)
        print(f"Post {'successful' if success else 'failed'}")

    else:
        print("Use --login or --post")


if __name__ == '__main__':
    main()
