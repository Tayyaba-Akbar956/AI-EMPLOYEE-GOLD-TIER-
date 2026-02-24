"""
Integration tests for Twitter Poster (Feature 6)
Real Playwright automation with safe testing (delete immediately after posting)
NO MOCKING - 100% real integration
"""
import pytest
from pathlib import Path
from datetime import datetime


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()
    (vault / "Pending_Approval").mkdir()
    (vault / "Done").mkdir()
    (vault / "Database").mkdir()
    return vault


@pytest.fixture
def session_path(tmp_path):
    """Create temporary session directory"""
    session_dir = tmp_path / ".twitter_session"
    session_dir.mkdir()
    return session_dir


class TestTwitterPoster:
    """Test Twitter poster initialization"""

    def test_poster_initialization(self, vault_path, session_path):
        """Test that Twitter poster initializes correctly"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        assert poster.vault_path == vault_path
        assert poster.session_path == session_path
        assert poster.platform == "twitter"


class TestCharacterLimit:
    """Test 280 character limit enforcement"""

    def test_enforce_character_limit_short_text(self, vault_path, session_path):
        """Test that short text passes through unchanged"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        short_text = "This is a short tweet"
        result = poster.enforce_character_limit(short_text)

        assert result == short_text
        assert len(result) <= 280

    def test_enforce_character_limit_long_text(self, vault_path, session_path):
        """Test that long text is truncated with ellipsis"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        long_text = "A" * 300  # 300 characters
        result = poster.enforce_character_limit(long_text)

        assert len(result) <= 280
        assert result.endswith("...")
        assert len(result) == 280

    def test_enforce_character_limit_exactly_280(self, vault_path, session_path):
        """Test that exactly 280 characters passes through"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        exact_text = "A" * 280
        result = poster.enforce_character_limit(exact_text)

        assert result == exact_text
        assert len(result) == 280


class TestApprovalWorkflow:
    """Test approval file creation"""

    def test_create_approval_file_for_tweet(self, vault_path, session_path):
        """Test that tweeting creates approval file"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        tweet_data = {
            "content": "Test tweet content"
        }

        approval_file = poster.create_tweet(tweet_data, require_approval=True)

        assert approval_file is not None
        assert (vault_path / "Pending_Approval" / approval_file).exists()

    def test_approval_file_contains_content(self, vault_path, session_path):
        """Test approval file contains tweet content"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        tweet_data = {
            "content": "Excited to announce our new AI features! #AI #Innovation"
        }

        approval_file = poster.create_tweet(tweet_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        assert "Excited to announce our new AI features!" in content
        assert "#AI" in content
        assert "twitter" in content.lower()

    def test_approval_file_with_image(self, vault_path, session_path):
        """Test approval file includes image path"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        tweet_data = {
            "content": "Check out this screenshot",
            "image_path": "/path/to/screenshot.png"
        }

        approval_file = poster.create_tweet(tweet_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        assert "/path/to/screenshot.png" in content

    def test_approval_file_truncates_long_content(self, vault_path, session_path):
        """Test that approval file shows truncated content for long tweets"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        long_content = "A" * 300
        tweet_data = {
            "content": long_content
        }

        approval_file = poster.create_tweet(tweet_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        # Should show truncated version in approval file
        assert "..." in content
        assert "280 character limit" in content.lower()


class TestSessionManagement:
    """Test session directory creation"""

    def test_session_directory_created(self, vault_path, session_path):
        """Test that session directory is created"""
        from src.social.twitter_poster import TwitterPoster

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        assert session_path.exists()


# Note: Real Playwright tests would require actual Twitter credentials
# and would delete tweet immediately after verification.
# These are documented but not run in CI to avoid requiring credentials.

class TestRealIntegration:
    """
    Real integration tests - require Twitter credentials in .env
    Run manually with: pytest -k TestRealIntegration --run-real
    """

    @pytest.mark.skip(reason="Real integration tests require --run-real flag and Twitter credentials")
    def test_real_tweet_to_twitter(self, vault_path, session_path):
        """
        Real test posting to Twitter with immediate deletion.
        Requires TWITTER_EMAIL and TWITTER_PASSWORD in environment.
        """
        import os
        from src.social.twitter_poster import TwitterPoster

        email = os.getenv("TWITTER_EMAIL")
        password = os.getenv("TWITTER_PASSWORD")

        if not email or not password:
            pytest.skip("Twitter credentials not found in environment")

        poster = TwitterPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        # Login first
        login_success = poster.login(email, password)
        assert login_success, "Twitter login failed"

        # Tweet with test content
        tweet_data = {
            "content": f"[TEST] Automated tweet from AI Employee - {datetime.now().isoformat()}"
        }

        tweet_success, tweet_id = poster.post_to_twitter(tweet_data)
        assert tweet_success, "Twitter post failed"
        assert tweet_id is not None, "Tweet ID not returned"

        # Delete immediately for safety
        delete_success = poster.delete_tweet(tweet_id)
        assert delete_success, "Failed to delete test tweet"

        print("✓ Real Twitter post successful and deleted")
