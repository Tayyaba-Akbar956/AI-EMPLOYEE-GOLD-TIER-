"""
Unit tests for Ralph Wiggum Stop Hook (Feature 2)
Tests exit interception, completion checking, re-injection, iteration tracking
"""
import pytest
import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault structure for testing"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()

    # Create required folders
    (vault / "In_Progress").mkdir()
    (vault / "Done").mkdir()
    (vault / "Needs_Action").mkdir()

    return vault


@pytest.fixture
def state_path(tmp_path):
    """Create temporary state directory"""
    state_dir = tmp_path / "ralph_state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def sample_state(vault_path):
    """Create a sample state dictionary"""
    return {
        "task_id": "TASK_001",
        "original_prompt": "Process this email",
        "task_file": str(vault_path / "In_Progress" / "EMAIL_001.md"),
        "done_file": str(vault_path / "Done" / "EMAIL_001.md"),
        "iteration": 1,
        "max_iterations": 10,
        "started": "2026-02-24T10:00:00Z",
        "previous_outputs": []
    }


class TestExitInterception:
    """Test exit signal interception"""

    def test_hook_intercepts_exit_signal(self, vault_path, state_path, sample_state):
        """Test that the hook intercepts Claude Code exit"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # Create task in In_Progress (not Done)
        task_file = Path(sample_state["task_file"])
        task_file.write_text("---\ntype: email\n---\nContent")

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        should_exit = hook.check_exit("TASK_001")

        assert should_exit is False  # Should block exit

    def test_hook_allows_exit_when_done(self, vault_path, state_path, sample_state):
        """Test that hook allows exit when task is in Done"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # Create task in Done
        done_file = Path(sample_state["done_file"])
        done_file.write_text("---\ntype: email\n---\nContent")

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        should_exit = hook.check_exit("TASK_001")

        assert should_exit is True  # Should allow exit


class TestCompletionChecking:
    """Test task completion verification"""

    def test_task_in_done_returns_true(self, vault_path, state_path, sample_state):
        """Test that task in Done folder is detected as complete"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        done_file = Path(sample_state["done_file"])
        done_file.write_text("---\ntype: email\n---\nContent")

        hook = RalphWiggumHook(state_path=str(state_path))
        is_complete = hook.is_task_complete(sample_state)

        assert is_complete is True

    def test_task_in_progress_returns_false(self, vault_path, state_path, sample_state):
        """Test that task in In_Progress is not complete"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        task_file = Path(sample_state["task_file"])
        task_file.write_text("---\ntype: email\n---\nContent")

        hook = RalphWiggumHook(state_path=str(state_path))
        is_complete = hook.is_task_complete(sample_state)

        assert is_complete is False

    def test_missing_task_file_returns_false(self, vault_path, state_path, sample_state):
        """Test that missing task file is not complete"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        hook = RalphWiggumHook(state_path=str(state_path))
        is_complete = hook.is_task_complete(sample_state)

        assert is_complete is False


class TestIterationTracking:
    """Test iteration counting and limits"""

    def test_increment_iteration_increases_count(self, state_path, sample_state):
        """Test that iteration count increments"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        hook.increment_iteration("TASK_001", "Output from iteration 1")

        # Read updated state
        updated_state = json.loads(state_file.read_text())
        assert updated_state["iteration"] == 2
        assert len(updated_state["previous_outputs"]) == 1
        assert "Output from iteration 1" in updated_state["previous_outputs"][0]

    def test_max_iterations_reached(self, state_path, sample_state):
        """Test detection of max iterations"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        sample_state["iteration"] = 10
        sample_state["max_iterations"] = 10

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        max_reached = hook.is_max_iterations_reached("TASK_001")

        assert max_reached is True

    def test_below_max_iterations(self, state_path, sample_state):
        """Test that below max iterations returns False"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        sample_state["iteration"] = 5
        sample_state["max_iterations"] = 10

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        max_reached = hook.is_max_iterations_reached("TASK_001")

        assert max_reached is False


class TestPromptReinjection:
    """Test prompt re-injection with context"""

    def test_build_reinjection_prompt(self, state_path, sample_state):
        """Test building re-injection prompt with context"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        sample_state["previous_outputs"] = [
            "Iteration 1: Created approval file",
            "Iteration 2: Waiting for approval"
        ]

        hook = RalphWiggumHook(state_path=str(state_path))
        prompt = hook.build_reinjection_prompt(sample_state)

        assert "Process this email" in prompt  # Original prompt
        assert "Iteration 1: Created approval file" in prompt
        assert "Iteration 2: Waiting for approval" in prompt
        assert "Continue from where you left off" in prompt

    def test_reinjection_includes_iteration_number(self, state_path, sample_state):
        """Test that re-injection prompt includes iteration number"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        sample_state["iteration"] = 3

        hook = RalphWiggumHook(state_path=str(state_path))
        prompt = hook.build_reinjection_prompt(sample_state)

        assert "Iteration 3" in prompt or "iteration 3" in prompt


class TestFailureHandling:
    """Test failure handling when max iterations reached"""

    def test_move_to_failed_on_max_iterations(self, vault_path, state_path, sample_state):
        """Test that task moves to FAILED when max iterations reached"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # Create task in In_Progress
        task_file = Path(sample_state["task_file"])
        task_file.write_text("---\ntype: email\n---\nContent")

        sample_state["iteration"] = 10
        sample_state["max_iterations"] = 10

        hook = RalphWiggumHook(state_path=str(state_path), vault_path=str(vault_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        hook.handle_failure("TASK_001")

        # Check task moved to Needs_Action with FAILED prefix
        failed_file = vault_path / "Needs_Action" / "FAILED_EMAIL_001.md"
        assert failed_file.exists()
        assert not task_file.exists()

    def test_create_system_alert_on_failure(self, vault_path, state_path, sample_state):
        """Test that system alert is created on failure"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        sample_state["iteration"] = 10
        sample_state["max_iterations"] = 10

        hook = RalphWiggumHook(state_path=str(state_path), vault_path=str(vault_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        hook.handle_failure("TASK_001")

        # Check system alert created
        alert_files = list((vault_path / "Needs_Action").glob("SYSTEM_ALERT_*.md"))
        assert len(alert_files) == 1

        alert_content = alert_files[0].read_text()
        assert "Max iterations reached" in alert_content
        assert "TASK_001" in alert_content
        assert "ralph_wiggum" in alert_content

    def test_failure_logs_to_database(self, vault_path, state_path, sample_state):
        """Test that failure is logged to database"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        sample_state["iteration"] = 10

        hook = RalphWiggumHook(state_path=str(state_path), vault_path=str(vault_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        with patch.object(hook, 'log_action') as mock_log:
            hook.handle_failure("TASK_001")
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args["action_type"] == "ralph_failure"
            assert call_args["result"] == "failure"


class TestStateManagement:
    """Test state file persistence and loading"""

    def test_load_state_from_file(self, state_path, sample_state):
        """Test loading state from JSON file"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        hook = RalphWiggumHook(state_path=str(state_path))
        loaded_state = hook.load_state("TASK_001")

        assert loaded_state["task_id"] == "TASK_001"
        assert loaded_state["iteration"] == 1
        assert loaded_state["max_iterations"] == 10

    def test_save_state_to_file(self, state_path, sample_state):
        """Test saving state to JSON file"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        hook = RalphWiggumHook(state_path=str(state_path))
        hook.save_state("TASK_001", sample_state)

        state_file = state_path / "TASK_001.json"
        assert state_file.exists()

        loaded = json.loads(state_file.read_text())
        assert loaded["task_id"] == "TASK_001"

    def test_state_persists_across_hook_instances(self, state_path, sample_state):
        """Test that state persists across different hook instances"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # First instance saves state
        hook1 = RalphWiggumHook(state_path=str(state_path))
        hook1.save_state("TASK_001", sample_state)

        # Second instance loads same state
        hook2 = RalphWiggumHook(state_path=str(state_path))
        loaded_state = hook2.load_state("TASK_001")

        assert loaded_state["task_id"] == sample_state["task_id"]
        assert loaded_state["iteration"] == sample_state["iteration"]

    def test_missing_state_file_returns_none(self, state_path):
        """Test that missing state file returns None"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        hook = RalphWiggumHook(state_path=str(state_path))
        loaded_state = hook.load_state("NONEXISTENT")

        assert loaded_state is None


class TestIntegration:
    """Test complete Ralph Wiggum flow"""

    def test_complete_flow_task_not_done(self, vault_path, state_path, sample_state):
        """Test complete flow when task is not done"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # Create task in In_Progress
        task_file = Path(sample_state["task_file"])
        task_file.write_text("---\ntype: email\n---\nContent")

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        # Check exit - should block and increment
        should_exit = hook.check_exit("TASK_001")

        assert should_exit is False

        # Verify iteration incremented
        updated_state = json.loads(state_file.read_text())
        assert updated_state["iteration"] == 2

    def test_complete_flow_task_done(self, vault_path, state_path, sample_state):
        """Test complete flow when task is done"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # Create task in Done
        done_file = Path(sample_state["done_file"])
        done_file.write_text("---\ntype: email\n---\nContent")

        hook = RalphWiggumHook(state_path=str(state_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        # Check exit - should allow
        should_exit = hook.check_exit("TASK_001")

        assert should_exit is True

    def test_complete_flow_max_iterations(self, vault_path, state_path, sample_state):
        """Test complete flow when max iterations reached"""
        from src.ralph_wiggum.stop_hook import RalphWiggumHook

        # Create task in In_Progress
        task_file = Path(sample_state["task_file"])
        task_file.write_text("---\ntype: email\n---\nContent")

        sample_state["iteration"] = 10
        sample_state["max_iterations"] = 10

        hook = RalphWiggumHook(state_path=str(state_path), vault_path=str(vault_path))
        state_file = state_path / "TASK_001.json"
        state_file.write_text(json.dumps(sample_state))

        # Check exit - should allow after handling failure
        should_exit = hook.check_exit("TASK_001")

        assert should_exit is True

        # Verify failure handling
        failed_file = vault_path / "Needs_Action" / "FAILED_EMAIL_001.md"
        assert failed_file.exists()
