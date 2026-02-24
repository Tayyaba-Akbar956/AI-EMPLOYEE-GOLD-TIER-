"""
Unit tests for Error Recovery and Graceful Degradation (Feature 9)
Tests retry logic, error handling, and SYSTEM_ALERT generation
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import time


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()
    (vault / "Needs_Action").mkdir()
    return vault


class TestRetryDecorator:
    """Test retry decorator functionality"""

    def test_retry_succeeds_on_first_attempt(self):
        """Test that successful calls don't retry"""
        from src.utils.error_recovery import with_retry

        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.1)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_succeeds_on_second_attempt(self):
        """Test that function retries and eventually succeeds"""
        from src.utils.error_recovery import with_retry

        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.1)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 2

    def test_retry_fails_after_max_attempts(self):
        """Test that function fails after max attempts"""
        from src.utils.error_recovery import with_retry

        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent failure")

        with pytest.raises(Exception, match="Permanent failure"):
            always_fails()

        assert call_count == 3

    def test_retry_respects_exponential_backoff(self):
        """Test that retry delays increase exponentially"""
        from src.utils.error_recovery import with_retry

        call_times = []

        @with_retry(max_attempts=3, base_delay=0.1, max_delay=1.0)
        def timed_function():
            call_times.append(time.time())
            raise Exception("Always fails")

        with pytest.raises(Exception):
            timed_function()

        # Check that delays increase (approximately)
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay2 > delay1  # Second delay should be longer


class TestSystemAlertGeneration:
    """Test SYSTEM_ALERT file generation"""

    def test_create_system_alert(self, vault_path):
        """Test that system alert file is created"""
        from src.utils.error_recovery import create_system_alert

        alert_file = create_system_alert(
            vault_path=str(vault_path),
            service="gmail",
            error="Connection timeout",
            action_required=True
        )

        assert alert_file is not None
        alert_path = vault_path / "Needs_Action" / alert_file
        assert alert_path.exists()

    def test_system_alert_contains_error_details(self, vault_path):
        """Test that alert file contains error information"""
        from src.utils.error_recovery import create_system_alert

        alert_file = create_system_alert(
            vault_path=str(vault_path),
            service="odoo",
            error="Authentication failed",
            action_required=True
        )

        content = (vault_path / "Needs_Action" / alert_file).read_text(encoding='utf-8')
        assert "odoo" in content.lower()
        assert "Authentication failed" in content
        assert "action_required: true" in content.lower()

    def test_system_alert_filename_format(self, vault_path):
        """Test that alert filename follows correct format"""
        from src.utils.error_recovery import create_system_alert

        alert_file = create_system_alert(
            vault_path=str(vault_path),
            service="facebook",
            error="Post failed",
            action_required=False
        )

        assert alert_file.startswith("SYSTEM_ALERT_FACEBOOK_")
        assert alert_file.endswith(".md")


class TestGracefulDegradation:
    """Test graceful degradation when services fail"""

    def test_service_failure_does_not_crash_system(self, vault_path):
        """Test that one service failure doesn't affect others"""
        from src.utils.error_recovery import with_retry, create_system_alert

        # Simulate Gmail failing
        @with_retry(max_attempts=2, base_delay=0.1)
        def gmail_check():
            raise Exception("Gmail unavailable")

        # Should raise exception but not crash
        with pytest.raises(Exception):
            gmail_check()

        # System should continue - verify by creating alert
        alert = create_system_alert(
            vault_path=str(vault_path),
            service="gmail",
            error="Service unavailable",
            action_required=True
        )
        assert alert is not None

    def test_multiple_service_failures_tracked_separately(self, vault_path):
        """Test that multiple service failures create separate alerts"""
        from src.utils.error_recovery import create_system_alert

        alert1 = create_system_alert(
            vault_path=str(vault_path),
            service="gmail",
            error="Error 1",
            action_required=True
        )

        alert2 = create_system_alert(
            vault_path=str(vault_path),
            service="odoo",
            error="Error 2",
            action_required=True
        )

        alerts = list((vault_path / "Needs_Action").glob("SYSTEM_ALERT_*.md"))
        assert len(alerts) == 2
        assert alert1 != alert2


class TestRetryConfiguration:
    """Test retry configuration options"""

    def test_custom_max_attempts(self):
        """Test custom max_attempts parameter"""
        from src.utils.error_recovery import with_retry

        call_count = 0

        @with_retry(max_attempts=5, base_delay=0.1)
        def custom_retry():
            nonlocal call_count
            call_count += 1
            raise Exception("Fail")

        with pytest.raises(Exception):
            custom_retry()

        assert call_count == 5

    def test_custom_base_delay(self):
        """Test custom base_delay parameter"""
        from src.utils.error_recovery import with_retry

        start_time = time.time()

        @with_retry(max_attempts=2, base_delay=0.5)
        def delayed_retry():
            raise Exception("Fail")

        with pytest.raises(Exception):
            delayed_retry()

        elapsed = time.time() - start_time
        # Should have at least one 0.5s delay
        assert elapsed >= 0.5

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay"""
        from src.utils.error_recovery import with_retry

        call_times = []

        @with_retry(max_attempts=4, base_delay=1.0, max_delay=2.0)
        def capped_delay():
            call_times.append(time.time())
            raise Exception("Fail")

        with pytest.raises(Exception):
            capped_delay()

        # Check that no delay exceeds max_delay
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay <= 2.5  # Allow some margin for execution time
