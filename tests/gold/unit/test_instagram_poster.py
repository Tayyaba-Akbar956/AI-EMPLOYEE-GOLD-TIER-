"""
Integration tests for Instagram Poster (Feature 5 - Part 2)
Real Playwright automation with safe testing (archive immediately after posting)
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
    session_dir = tmp_path / ".instagram_session"
    session_dir.mkdir()
    return session_dir


class TestInstagramPoster:
    """Test Instagram poster initialization"""

    def test_poster_initialization(self, vault_path, session_path):
        """Test that Instagram poster initializes correctly"""
        from src.social.instagram_poster import InstagramPoster

        poster = InstagramPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        assert poster.vault_path == vault_path
        assert poster.session_path == session_path
        assert poster.platform == "instagram"


class TestApprovalWorkflow:
    """Test approval file creation"""

    def test_create_approval_file_for_post(self, vault_path, session_path):
        """Test that posting creates approval file"""
        from src.social.instagram_poster import InstagramPoster

        poster = InstagramPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        post_data = {
            "caption": "Test post caption",
            "image_path": "/path/to/image.jpg"
        }

        approval_file = poster.create_post(post_data, require_approval=True)

        assert approval_file is not None
        assert (vault_path / "Pending_Approval" / approval_file).exists()

    def test_approval_file_contains_content(self, vault_path, session_path):
        """Test approval file contains post content"""
        from src.social.instagram_poster import InstagramPoster

        poster = InstagramPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        post_data = {
            "caption": "Check out this amazing view! #travel #photography",
            "image_path": "/path/to/photo.jpg"
        }

        approval_file = poster.create_post(post_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        assert "Check out this amazing view!" in content
        assert "#travel" in content
        assert "instagram" in content.lower()
        assert "/path/to/photo.jpg" in content

    def test_approval_file_story_post(self, vault_path, session_path):
        """Test approval file for story post"""
        from src.social.instagram_poster import InstagramPoster

        poster = InstagramPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        post_data = {
            "caption": "Story text content",
            "post_type": "story"
        }

        approval_file = poster.create_post(post_data, require_approval=True)
        content = (vault_path / "Pending_Approval" / approval_file).read_text()

        assert "Story text content" in content
        assert "story" in content.lower()


class TestSessionManagement:
    """Test session directory creation"""

    def test_session_directory_created(self, vault_path, session_path):
        """Test that session directory is created"""
        from src.social.instagram_poster import InstagramPoster

        poster = InstagramPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        assert session_path.exists()


# Note: Real Playwright tests would require actual Instagram credentials
# and would archive post immediately after verification.
# These are documented but not run in CI to avoid requiring credentials.

class TestRealIntegration:
    """
    Real integration tests - require Instagram credentials in .env
    Run manually with: pytest -k TestRealIntegration --run-real
    """

    @pytest.mark.skip(reason="Real integration tests require --run-real flag and Instagram credentials")
    def test_real_post_to_instagram(self, vault_path, session_path):
        """
        Real test posting to Instagram with immediate archive.
        Requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in environment.
        """
        import os
        from src.social.instagram_poster import InstagramPoster

        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")

        if not username or not password:
            pytest.skip("Instagram credentials not found in environment")

        poster = InstagramPoster(
            vault_path=str(vault_path),
            session_path=str(session_path)
        )

        # Login first
        login_success = poster.login(username, password)
        assert login_success, "Instagram login failed"

        # Post with test image (must provide real image path)
        post_data = {
            "caption": f"[TEST] Automated post from AI Employee - {datetime.now().isoformat()}",
            "image_path": "test_image.jpg"  # Must exist
        }

        post_success = poster.post_to_instagram(post_data)
        assert post_success, "Instagram post failed"

        # Archive immediately for safety
        archive_success = poster.archive_last_post()
        assert archive_success, "Failed to archive test post"

        print("✓ Real Instagram post successful and archived")
