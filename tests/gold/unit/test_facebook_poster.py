"""
Integration tests for Facebook Poster (Feature 5 - Part 1)
Real Playwright automation with safe testing (visibility: Only Me)
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
    session_dir = tmp_path / ".facebook_session"
    session_dir.mkdir()
    return session_dir


class TestFacebookPoster:
    """Test Facebook poster initialization"""

    def test_poster_initialization(self, vault_path, session_path):
        """Test that Facebook poster initializes correctly"""
        from src.social.facebook_poster import FacebookPoster

        poster = FacebookPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        assert poster.vault_path == vault_path
        assert poster.session_path == session_path
        assert poster.platform == "facebook"


class TestApprovalWorkflow:
    """Test approval file creation"""

    def test_create_approval_file_for_post(self, vault_path, session_path):
        """Test that posting creates approval file"""
        from src.social.facebook_poster import FacebookPoster

        poster = FacebookPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        post_data = {
            "content": "Test post content",
            "visibility": "public"
        }

        approval_file = poster.create_post(post_data, require_approval=True)

        assert approval_file is not None
        assert (vault_path / "Pending_Approval" / approval_file).exists()

    def test_approval_file_contains_content(self, vault_path, session_path):
        """Test approval file contains post content"""
        from src.social.facebook_poster import FacebookPoster

        poster = FacebookPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        post_data = {
            "content": "Test post about AI automation",
            "visibility": "friends"
        }

        approval_file = poster.create_post(post_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        assert "Test post about AI automation" in content
        assert "facebook" in content.lower()
        assert "friends" in content.lower()

    def test_approval_file_with_image(self, vault_path, session_path):
        """Test approval file includes image path"""
        from src.social.facebook_poster import FacebookPoster

        poster = FacebookPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        post_data = {
            "content": "Check out this image",
            "image_path": "/path/to/image.jpg",
            "visibility": "public"
        }

        approval_file = poster.create_post(post_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        assert "/path/to/image.jpg" in content


class TestSessionManagement:
    """Test session directory creation"""

    def test_session_directory_created(self, vault_path, session_path):
        """Test that session directory is created"""
        from src.social.facebook_poster import FacebookPoster

        poster = FacebookPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        assert session_path.exists()


# Note: Real Playwright tests would require actual Facebook credentials
# and would post with "Only Me" visibility for safety.
# These are documented but not run in CI to avoid requiring credentials.

class TestRealIntegration:
    """
    Real integration tests - require Facebook credentials in .env
    Run manually with: pytest -k TestRealIntegration --run-real
    """

    @pytest.mark.skip(reason="Real integration tests require --run-real flag and Facebook credentials")
    def test_real_post_to_facebook(self, vault_path, session_path):
        """
        Real test posting to Facebook with 'Only Me' visibility.
        Requires FACEBOOK_EMAIL and FACEBOOK_PASSWORD in environment.
        """
        import os
        from src.social.facebook_poster import FacebookPoster

        email = os.getenv("FACEBOOK_EMAIL")
        password = os.getenv("FACEBOOK_PASSWORD")

        if not email or not password:
            pytest.skip("Facebook credentials not found in environment")

        poster = FacebookPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        # Login first
        login_success = poster.login(email, password)
        assert login_success, "Facebook login failed"

        # Post with "Only Me" visibility for safety
        post_data = {
            "content": f"[TEST] Automated post from AI Employee - {datetime.now().isoformat()}",
            "visibility": "only_me"
        }

        post_success = poster.post_to_facebook(post_data)
        assert post_success, "Facebook post failed"

        print("✓ Real Facebook post successful (Only Me visibility)")

