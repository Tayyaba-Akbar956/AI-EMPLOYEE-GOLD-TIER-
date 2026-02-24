"""
Instagram Poster - Gold Tier Feature 5 (Part 2)
Posts to Instagram using Playwright browser automation
Same pattern as Facebook and LinkedIn
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


class InstagramPoster:
    """
    Posts to Instagram using Playwright browser automation.
    Session persists across runs - login once, reuse session.
    """

    def __init__(self, vault_path: Optional[str] = None, session_path: Optional[str] = None):
        """Initialize Instagram poster"""
        if vault_path is None:
            vault_path = os.environ.get('VAULT_PATH', str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault'))

        if session_path is None:
            session_path = str(Path.home() / '.instagram_session')

        self.vault_path = Path(vault_path)
        self.session_path = Path(session_path)
        self.platform = "instagram"

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
        Create an Instagram post.
        If require_approval=True, creates approval file and returns filename.
        Otherwise, posts directly to Instagram.
        """
        if require_approval:
            return self._create_approval_file(post_data)
        else:
            success = self.post_to_instagram(post_data)
            return "posted" if success else None

    def _create_approval_file(self, post_data: Dict[str, Any]) -> str:
        """Create approval file for Instagram post"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_filename = f"SOCIAL_IG_{timestamp}.md"
        approval_path = self.vault_path / "Pending_Approval" / approval_filename

        # Ensure directory exists
        approval_path.parent.mkdir(parents=True, exist_ok=True)

        caption = post_data.get("caption", "")
        image_path = post_data.get("image_path", "")
        post_type = post_data.get("post_type", "post")  # post or story

        approval_content = f"""---
type: social_post
platform: instagram
approval_id: SOCIAL_IG_{timestamp}
post_type: {post_type}
---

## Social Media Post Request

**Platform**: Instagram
**Type**: {post_type.title()}
**Scheduled**: Immediate

### Caption

{caption}
"""

        if image_path:
            approval_content += f"""
### Media

- Image: {image_path}
"""

        approval_content += """
## Approval Required

This will be posted to Instagram.
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

    def login(self, username: str, password: str) -> bool:
        """
        Login to Instagram and save session.
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to Instagram
            page.goto("https://www.instagram.com")

            # Wait for login form
            page.wait_for_selector('input[name="username"]', timeout=10000)

            # Fill login form
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')

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
            print(f"Instagram login error: {e}")
            return False

    def post_to_instagram(self, post_data: Dict[str, Any]) -> bool:
        """
        Post to Instagram using Playwright.
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to Instagram
            page.goto("https://www.instagram.com")

            # Wait for page load
            page.wait_for_load_state("networkidle")

            caption = post_data.get("caption", "")
            image_path = post_data.get("image_path")
            post_type = post_data.get("post_type", "post")

            if post_type == "story":
                # Post story
                page.click('svg[aria-label="New story"]', timeout=5000)

                if image_path and Path(image_path).exists():
                    page.set_input_files('input[type="file"]', image_path)
                    page.wait_for_timeout(2000)

                # Add text if caption provided
                if caption:
                    page.click('button[aria-label="Add text"]', timeout=5000)
                    page.fill('textarea', caption)

                # Share story
                page.click('button:has-text("Share")', timeout=5000)
                page.wait_for_timeout(3000)

            else:
                # Regular post
                # Click new post button
                page.click('svg[aria-label="New post"]', timeout=5000)

                # Upload image
                if image_path and Path(image_path).exists():
                    page.set_input_files('input[type="file"]', image_path)
                    page.wait_for_timeout(2000)

                    # Click Next
                    page.click('button:has-text("Next")', timeout=5000)
                    page.wait_for_timeout(1000)

                    # Click Next again (filters page)
                    page.click('button:has-text("Next")', timeout=5000)
                    page.wait_for_timeout(1000)

                    # Add caption
                    page.fill('textarea[aria-label="Write a caption..."]', caption)

                    # Click Share
                    page.click('button:has-text("Share")', timeout=5000)
                    page.wait_for_timeout(3000)

            # Log success
            self.log_action(
                action_type="instagram_post",
                result="success",
                content=caption[:100]
            )

            page.close()
            context.close()
            browser.close()
            p.stop()

            return True

        except Exception as e:
            print(f"Instagram post error: {e}")
            self.log_action(
                action_type="instagram_post",
                result="failure",
                error=str(e)
            )
            return False

    def archive_last_post(self) -> bool:
        """
        Archive the most recent post (for safe testing).
        Returns True on success, False on failure.
        """
        try:
            p, browser, context = self.get_browser_context()
            page = context.new_page()

            # Navigate to profile
            page.goto("https://www.instagram.com")
            page.wait_for_load_state("networkidle")

            # Click profile icon
            page.click('svg[aria-label="Profile"]', timeout=5000)
            page.wait_for_timeout(2000)

            # Click first post
            page.click('div[role="button"] img', timeout=5000)
            page.wait_for_timeout(1000)

            # Click options
            page.click('button[aria-label="More options"]', timeout=5000)
            page.wait_for_timeout(500)

            # Click Archive
            page.click('button:has-text("Archive")', timeout=5000)
            page.wait_for_timeout(2000)

            page.close()
            context.close()
            browser.close()
            p.stop()

            return True

        except Exception as e:
            print(f"Instagram archive error: {e}")
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
                "component": "instagram_poster",
                "action": action_type,
                "item_id": "instagram",
                "details": f"Instagram post: {result}" + (f" - {error}" if error else "")
            })
        except Exception as e:
            print(f"Error logging to database: {e}")


def main():
    """Main entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Instagram Poster')
    parser.add_argument('--login', action='store_true', help='Login to Instagram')
    parser.add_argument('--username', type=str, help='Instagram username')
    parser.add_argument('--password', type=str, help='Instagram password')
    parser.add_argument('--post', type=str, help='Post caption')
    parser.add_argument('--image', type=str, help='Image path')
    parser.add_argument('--story', action='store_true', help='Post as story')

    args = parser.parse_args()

    poster = InstagramPoster()

    if args.login:
        if not args.username or not args.password:
            print("Error: --username and --password required for login")
            return

        success = poster.login(args.username, args.password)
        print(f"Login {'successful' if success else 'failed'}")

    elif args.post:
        post_data = {
            "caption": args.post,
            "image_path": args.image,
            "post_type": "story" if args.story else "post"
        }

        success = poster.post_to_instagram(post_data)
        print(f"Post {'successful' if success else 'failed'}")

    else:
        print("Use --login or --post")


if __name__ == '__main__':
    main()
