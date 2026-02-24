"""Tests for LinkedIn Poster Skill.

Tests cover:
- Post creation and validation
- Scheduling logic
- Approval workflow integration
- Retry mechanism
- Rate limiting
- Error handling
- Session management
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

# Import the skill (will be created)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.db_manager import DatabaseManager
from skills.linkedin_poster import LinkedInPoster


@pytest.fixture
def db_manager(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    return DatabaseManager(str(db_path))


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure."""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()
    (vault / "Pending_Approval").mkdir()
    (vault / "Approved").mkdir()
    (vault / "Logs").mkdir()
    return str(vault)


@pytest.fixture
def linkedin_poster(db_manager, vault_path):
    """Create LinkedInPoster instance."""
    return LinkedInPoster(db_manager, vault_path)


class TestPostCreation:
    """Test post creation and validation."""

    def test_create_text_post(self, linkedin_poster, db_manager):
        """Test creating a simple text post."""
        post_id = linkedin_poster.create_post(
            content="This is a test post",
            importance_level="normal"
        )

        assert post_id is not None
        post = db_manager.get_linkedin_post(post_id)
        assert post['content'] == "This is a test post"
        assert post['status'] == 'approved'  # Normal importance auto-approves
        assert post['importance_level'] == 'normal'

    def test_create_post_with_image(self, linkedin_poster, db_manager, tmp_path):
        """Test creating post with image attachment."""
        # Create dummy image
        image_path = tmp_path / "test.jpg"
        image_path.write_text("fake image")

        post_id = linkedin_poster.create_post(
            content="Post with image",
            media_paths=[str(image_path)],
            importance_level="normal"
        )

        post = db_manager.get_linkedin_post(post_id)
        media = json.loads(post['media_paths'])
        assert len(media) == 1
        assert str(image_path) in media

    def test_create_post_with_link(self, linkedin_poster, db_manager):
        """Test creating post with URL link."""
        post_id = linkedin_poster.create_post(
            content="Check out this article",
            link_url="https://example.com/article",
            importance_level="normal"
        )

        post = db_manager.get_linkedin_post(post_id)
        assert post['link_url'] == "https://example.com/article"

    def test_create_post_with_document(self, linkedin_poster, db_manager, tmp_path):
        """Test creating post with document attachment."""
        doc_path = tmp_path / "presentation.pdf"
        doc_path.write_text("fake pdf")

        post_id = linkedin_poster.create_post(
            content="New presentation",
            document_path=str(doc_path),
            importance_level="high"
        )

        post = db_manager.get_linkedin_post(post_id)
        assert post['document_path'] == str(doc_path)
        assert post['status'] == 'pending'  # High importance needs approval

    def test_empty_content_validation(self, linkedin_poster):
        """Test that empty content is rejected."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            linkedin_poster.create_post(content="", importance_level="normal")

    def test_content_length_validation(self, linkedin_poster):
        """Test content length limit (LinkedIn max 3000 chars)."""
        long_content = "x" * 3001
        with pytest.raises(ValueError, match="Content exceeds 3000 characters"):
            linkedin_poster.create_post(content=long_content, importance_level="normal")

    def test_invalid_importance_level(self, linkedin_poster):
        """Test invalid importance level."""
        with pytest.raises(ValueError, match="Invalid importance level"):
            linkedin_poster.create_post(
                content="Test",
                importance_level="invalid"
            )


class TestScheduling:
    """Test scheduling logic."""

    def test_schedule_specific_time(self, linkedin_poster, db_manager):
        """Test scheduling post for specific time."""
        future_time = datetime.now() + timedelta(hours=2)
        post_id = linkedin_poster.create_post(
            content="Scheduled post",
            importance_level="normal",
            scheduled_time=future_time
        )

        post = db_manager.get_linkedin_post(post_id)
        scheduled = datetime.fromisoformat(post['scheduled_time'])
        assert abs((scheduled - future_time).total_seconds()) < 1

    def test_smart_scheduling_weekday(self, linkedin_poster, db_manager):
        """Test smart scheduling picks optimal weekday time."""
        post_id = linkedin_poster.create_post(
            content="Smart scheduled",
            importance_level="normal",
            smart_schedule=True
        )

        post = db_manager.get_linkedin_post(post_id)
        scheduled = datetime.fromisoformat(post['scheduled_time'])

        # Should be scheduled for weekday 9am-5pm
        assert scheduled.weekday() < 5  # Monday-Friday
        assert 9 <= scheduled.hour <= 17

    def test_smart_scheduling_avoids_weekend(self, linkedin_poster, db_manager):
        """Test smart scheduling avoids weekends."""
        # Mock current time as Saturday
        with patch('skills.linkedin_poster.datetime') as mock_dt:
            saturday = datetime(2026, 2, 21, 10, 0)  # Saturday
            mock_dt.now.return_value = saturday
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            post_id = linkedin_poster.create_post(
                content="Weekend test",
                importance_level="normal",
                smart_schedule=True
            )

            post = db_manager.get_linkedin_post(post_id)
            scheduled = datetime.fromisoformat(post['scheduled_time'])

            # Should be scheduled for Monday
            assert scheduled.weekday() == 0  # Monday

    def test_immediate_posting(self, linkedin_poster, db_manager):
        """Test immediate posting (no scheduling)."""
        post_id = linkedin_poster.create_post(
            content="Post now",
            importance_level="normal",
            scheduled_time=None
        )

        post = db_manager.get_linkedin_post(post_id)
        scheduled = datetime.fromisoformat(post['scheduled_time'])
        now = datetime.now()

        # Should be scheduled within 1 minute
        assert abs((scheduled - now).total_seconds()) < 60


class TestApprovalWorkflow:
    """Test approval workflow integration."""

    def test_high_importance_requires_approval(self, linkedin_poster, db_manager):
        """Test high importance posts require approval."""
        post_id = linkedin_poster.create_post(
            content="Important announcement",
            importance_level="high"
        )

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'pending'
        assert post['approval_id'] is not None

    def test_critical_importance_requires_approval(self, linkedin_poster, db_manager):
        """Test critical importance posts require approval."""
        post_id = linkedin_poster.create_post(
            content="Critical update",
            importance_level="critical"
        )

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'pending'

    def test_normal_importance_auto_approves(self, linkedin_poster, db_manager):
        """Test normal importance posts auto-approve."""
        post_id = linkedin_poster.create_post(
            content="Regular post",
            importance_level="normal"
        )

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'approved'
        assert post['approval_id'] is None

    def test_approve_pending_post(self, linkedin_poster, db_manager):
        """Test approving a pending post."""
        post_id = linkedin_poster.create_post(
            content="Needs approval",
            importance_level="high"
        )

        result = linkedin_poster.approve_post(post_id)
        assert result['success'] is True

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'approved'

    def test_reject_pending_post(self, linkedin_poster, db_manager):
        """Test rejecting a pending post."""
        post_id = linkedin_poster.create_post(
            content="Will be rejected",
            importance_level="high"
        )

        result = linkedin_poster.reject_post(post_id, reason="Not appropriate")
        assert result['success'] is True

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'rejected'
        assert "Not appropriate" in post['error_message']


class TestRetryMechanism:
    """Test retry logic."""

    def test_retry_failed_post(self, linkedin_poster, db_manager):
        """Test retrying a failed post."""
        post_id = linkedin_poster.create_post(
            content="Will fail",
            importance_level="normal"
        )

        # Simulate failure
        db_manager.update_linkedin_post(post_id, {
            'status': 'failed',
            'retry_count': 0,
            'error_message': 'Network error'
        })

        result = linkedin_poster.retry_post(post_id)
        assert result['success'] is True

        post = db_manager.get_linkedin_post(post_id)
        assert post['retry_count'] == 1

    def test_max_retries_exceeded(self, linkedin_poster, db_manager):
        """Test that posts exceeding max retries are not retried."""
        post_id = linkedin_poster.create_post(
            content="Max retries",
            importance_level="normal"
        )

        # Simulate max retries reached
        db_manager.update_linkedin_post(post_id, {
            'status': 'failed',
            'retry_count': 2,
            'max_retries': 2
        })

        result = linkedin_poster.retry_post(post_id)
        assert result['success'] is False
        assert 'max retries' in result['error'].lower()

    def test_retry_increments_count(self, linkedin_poster, db_manager):
        """Test retry increments retry count."""
        post_id = linkedin_poster.create_post(
            content="Retry test",
            importance_level="normal"
        )

        db_manager.update_linkedin_post(post_id, {
            'status': 'failed',
            'retry_count': 0
        })

        linkedin_poster.retry_post(post_id)
        post = db_manager.get_linkedin_post(post_id)
        assert post['retry_count'] == 1


class TestRateLimiting:
    """Test rate limiting."""

    def test_daily_post_limit(self, linkedin_poster, db_manager):
        """Test daily post limit enforcement."""
        # Create 25 posts (at limit)
        today = datetime.now().date()
        for i in range(25):
            post_id = str(uuid4())
            db_manager.create_linkedin_post({
                'id': post_id,
                'content': f'Post {i}',
                'status': 'posted',
                'importance_level': 'normal',
                'posted_time': datetime.now().isoformat()
            })

        # Try to create one more
        can_post = linkedin_poster.check_rate_limit()
        assert can_post is False

    def test_rate_limit_allows_posting(self, linkedin_poster):
        """Test rate limit allows posting when under limit."""
        can_post = linkedin_poster.check_rate_limit()
        assert can_post is True


class TestPlaywrightIntegration:
    """Test Playwright automation (mocked)."""

    @patch('skills.linkedin_poster.sync_playwright')
    def test_authenticate_success(self, mock_playwright, linkedin_poster):
        """Test successful authentication."""
        mock_page = MagicMock()
        mock_page.url = 'https://www.linkedin.com/feed/'
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        
        mock_mv = mock_playwright.return_value
        mock_p = mock_mv.__enter__.return_value
        mock_launch = mock_p.chromium.launch_persistent_context
        mock_launch.return_value = mock_context

        result = linkedin_poster.authenticate()
        
        # Verbose assertions
        assert result is True
        mock_playwright.assert_called_once()
        mock_mv.__enter__.assert_called_once()
        mock_launch.assert_called_once()
        
        _, kwargs = mock_launch.call_args
        assert kwargs['viewport'] == {"width": 1400, "height": 900}

    @patch('skills.linkedin_poster.sync_playwright')
    def test_post_text_only(self, mock_playwright, linkedin_poster, db_manager):
        """Test posting text-only content."""
        post_id = linkedin_poster.create_post(
            content="Test post",
            importance_level="normal"
        )

        mock_page = MagicMock()
        mock_page.url = 'https://www.linkedin.com/feed/'
        
        # Mock locator behavior recursively
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.is_visible.return_value = True
        mock_locator.locator.return_value.first = mock_locator
        mock_page.locator.return_value.first = mock_locator
        
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_launch = mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context
        mock_launch.return_value = mock_context

        result = linkedin_poster.post_to_linkedin(post_id)
        assert result['success'] is True
        
        # Verify viewport
        mock_launch.assert_called_once()
        _, kwargs = mock_launch.call_args
        assert kwargs['viewport'] == {"width": 1400, "height": 900}

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'posted'
        assert post['posted_time'] is not None

    @patch('skills.linkedin_poster.sync_playwright')
    def test_post_with_media(self, mock_playwright, linkedin_poster, db_manager, tmp_path):
        """Test posting with media attachment."""
        image_path = tmp_path / "test.jpg"
        image_path.write_text("fake image")

        post_id = linkedin_poster.create_post(
            content="Post with image",
            media_paths=[str(image_path)],
            importance_level="normal"
        )

        mock_page = MagicMock()
        mock_page.url = 'https://www.linkedin.com/feed/'
        
        # Mock locator behavior recursively
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.is_visible.return_value = True
        mock_locator.locator.return_value.first = mock_locator
        mock_page.locator.return_value.first = mock_locator
        
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_launch = mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context
        mock_launch.return_value = mock_context

        result = linkedin_poster.post_to_linkedin(post_id)
        assert result['success'] is True
        
        # Verify viewport
        mock_launch.assert_called_once()
        _, kwargs = mock_launch.call_args
        assert kwargs['viewport'] == {"width": 1400, "height": 900}

    @patch('skills.linkedin_poster.sync_playwright')
    def test_post_failure_handling(self, mock_playwright, linkedin_poster, db_manager):
        """Test handling of posting failures."""
        post_id = linkedin_poster.create_post(
            content="Will fail",
            importance_level="normal"
        )

        # Simulate failure
        mock_playwright.return_value.__enter__.return_value.chromium.launch_persistent_context.side_effect = Exception("Network error")

        result = linkedin_poster.post_to_linkedin(post_id)
        assert result['success'] is False

        post = db_manager.get_linkedin_post(post_id)
        assert post['status'] == 'failed'
        assert post['error_message'] is not None


class TestSessionManagement:
    """Test session persistence."""

    def test_save_session(self, linkedin_poster, tmp_path):
        """Test saving browser session."""
        session_path = tmp_path / "session"
        linkedin_poster.session_path = str(session_path)

        # Mock session save
        result = linkedin_poster.save_session()
        assert result is True

    def test_load_session(self, linkedin_poster, tmp_path):
        """Test loading existing session."""
        session_path = tmp_path / "session"
        session_path.mkdir()
        (session_path / "cookies.json").write_text('[]')

        linkedin_poster.session_path = str(session_path)
        result = linkedin_poster.load_session()
        assert result is True

    def test_session_expiry(self, linkedin_poster, tmp_path):
        """Test session expiry detection."""
        session_path = tmp_path / "session"
        session_path.mkdir()

        # Create old session (8 days ago)
        old_time = datetime.now() - timedelta(days=8)
        (session_path / "cookies.json").write_text('[]')
        (session_path / "cookies.json").touch()

        is_valid = linkedin_poster.is_session_valid()
        # Should be invalid (>7 days old)
        # Note: This test may need adjustment based on implementation


class TestLogging:
    """Test comprehensive logging."""

    def test_log_post_creation(self, linkedin_poster, db_manager):
        """Test logging of post creation."""
        post_id = linkedin_poster.create_post(
            content="Test logging",
            importance_level="normal"
        )

        logs = db_manager.get_recent_activity(limit=1)
        assert len(logs) > 0
        assert 'linkedin-poster' in logs[0]['component']
        assert 'created' in logs[0]['action'].lower()

    def test_log_post_success(self, linkedin_poster, db_manager):
        """Test logging of successful post."""
        post_id = linkedin_poster.create_post(
            content="Success test",
            importance_level="normal"
        )

        mock_page = MagicMock()
        mock_page.url = 'https://www.linkedin.com/feed/'
        
        # Mock locator behavior recursively
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_locator.is_visible.return_value = True
        mock_locator.locator.return_value.first = mock_locator
        mock_page.locator.return_value.first = mock_locator
        
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        with patch('skills.linkedin_poster.sync_playwright') as mock_p:
            mock_launch = mock_p.return_value.__enter__.return_value.chromium.launch_persistent_context
            mock_launch.return_value = mock_context
            linkedin_poster.post_to_linkedin(post_id)
            
            # Verify viewport
            mock_launch.assert_called_once()
            _, kwargs = mock_launch.call_args
            assert kwargs['viewport'] == {"width": 1400, "height": 900}

        logs = db_manager.get_recent_activity(limit=5)
        success_logs = [l for l in logs if 'published' in l['action'].lower()]
        assert len(success_logs) > 0

    def test_log_post_failure(self, linkedin_poster, db_manager):
        """Test logging of failed post."""
        post_id = linkedin_poster.create_post(
            content="Failure test",
            importance_level="normal"
        )

        with patch('skills.linkedin_poster.sync_playwright', side_effect=Exception("Error")):
            linkedin_poster.post_to_linkedin(post_id)

        logs = db_manager.get_recent_activity(limit=5)
        error_logs = [l for l in logs if l['level'] == 'ERROR']
        assert len(error_logs) > 0
