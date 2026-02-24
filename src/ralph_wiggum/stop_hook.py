"""
Ralph Wiggum Stop Hook - Gold Tier Feature 2
Intercepts Claude Code exit, checks if task is in /Done/, re-injects prompt if not
Tracks iterations, stops at max with FAILED alert
"""
import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager


class RalphWiggumHook:
    """
    Stop hook that prevents Claude Code from exiting until task is complete.
    Named after Ralph Wiggum's persistence: "I'm helping!"
    """

    def __init__(self, state_path: Optional[str] = None, vault_path: Optional[str] = None):
        """Initialize Ralph Wiggum hook"""
        if state_path is None:
            state_path = os.environ.get('RALPH_STATE_PATH', '/tmp/ralph_state')

        if vault_path is None:
            vault_path = os.environ.get('VAULT_PATH', str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault'))

        self.state_path = Path(state_path)
        self.vault_path = Path(vault_path)
        self.state_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = self.vault_path / "Database" / "ai_employee.db"
        if db_path.exists():
            self.db = DatabaseManager(str(db_path))
        else:
            self.db = None

    def check_exit(self, task_id: str) -> bool:
        """
        Check if Claude Code should be allowed to exit.
        Returns True to allow exit, False to block and re-inject.
        """
        state = self.load_state(task_id)
        if state is None:
            # No state file - allow exit
            return True

        # Check if task is complete
        if self.is_task_complete(state):
            self.log_action(
                action_type="ralph_exit_allowed",
                actor="ralph_wiggum",
                target=task_id,
                result="success"
            )
            return True

        # Check if max iterations reached
        if self.is_max_iterations_reached(task_id):
            self.handle_failure(task_id)
            return True

        # Task not complete and below max iterations - block exit and re-inject
        self.increment_iteration(task_id, "Task not complete, re-injecting")
        self.log_action(
            action_type="ralph_exit_blocked",
            actor="ralph_wiggum",
            target=task_id,
            result="success",
            parameters={"iteration": state["iteration"] + 1}
        )
        return False

    def is_task_complete(self, state: Dict[str, Any]) -> bool:
        """
        Check if task file exists in /Done/ folder.
        Returns True if complete, False otherwise.
        """
        done_file = Path(state["done_file"])
        return done_file.exists()

    def is_max_iterations_reached(self, task_id: str) -> bool:
        """
        Check if maximum iterations have been reached.
        Returns True if at or above max, False otherwise.
        """
        state = self.load_state(task_id)
        if state is None:
            return False

        return state["iteration"] >= state["max_iterations"]

    def increment_iteration(self, task_id: str, output: str):
        """
        Increment iteration count and add output to history.
        """
        state = self.load_state(task_id)
        if state is None:
            return

        state["iteration"] += 1

        # Add timestamped output
        timestamp = datetime.now().isoformat()
        state["previous_outputs"].append(f"[{timestamp}] Iteration {state['iteration'] - 1}: {output}")

        self.save_state(task_id, state)

    def build_reinjection_prompt(self, state: Dict[str, Any]) -> str:
        """
        Build prompt for re-injection with context from previous iterations.
        """
        prompt_parts = [
            f"# Task Re-injection - Iteration {state['iteration']}",
            "",
            "## Original Task",
            state["original_prompt"],
            "",
            "## Previous Attempts",
        ]

        for output in state["previous_outputs"]:
            prompt_parts.append(f"- {output}")

        prompt_parts.extend([
            "",
            "## Instructions",
            "Continue from where you left off. The task is not yet in /Done/.",
            "Check what's blocking completion and take the next action.",
            f"This is iteration {state['iteration']} of {state['max_iterations']}.",
        ])

        return "\n".join(prompt_parts)

    def handle_failure(self, task_id: str):
        """
        Handle task failure when max iterations reached.
        Moves task to FAILED, creates system alert, logs to database.
        """
        state = self.load_state(task_id)
        if state is None:
            return

        # Move task file to Needs_Action with FAILED prefix
        task_file = Path(state["task_file"])
        if task_file.exists():
            task_filename = task_file.name
            failed_filename = f"FAILED_{task_filename}"
            failed_path = self.vault_path / "Needs_Action" / failed_filename

            shutil.move(str(task_file), str(failed_path))

        # Create system alert
        self.create_system_alert(state)

        # Log failure
        self.log_action(
            action_type="ralph_failure",
            actor="ralph_wiggum",
            target=task_id,
            result="failure",
            parameters={
                "iterations": state["iteration"],
                "max_iterations": state["max_iterations"],
                "duration": self._calculate_duration(state["started"])
            }
        )

    def create_system_alert(self, state: Dict[str, Any]):
        """
        Create a system alert file for failed task.
        """
        timestamp = datetime.now().isoformat()
        alert_filename = f"SYSTEM_ALERT_{state['task_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        alert_path = self.vault_path / "Needs_Action" / alert_filename

        task_filename = Path(state["task_file"]).name
        duration = self._calculate_duration(state["started"])

        alert_content = f"""---
type: system_alert
service: ralph_wiggum
error: Max iterations reached
timestamp: {timestamp}
action_required: true
task_id: {state['task_id']}
---

## Alert

Task {state['task_id']} failed to complete after {state['max_iterations']} iterations.

**Original Task**: {task_filename}
**Started**: {state['started']}
**Duration**: {duration}

## What Happened

Claude Code was unable to complete this task within the maximum iteration limit. The task has been moved to `/Needs_Action/FAILED_{task_filename}` for manual review.

## Previous Attempts

"""

        for i, output in enumerate(state["previous_outputs"], 1):
            alert_content += f"{i}. {output}\n"

        alert_content += """
## What to Do

1. Review the failed task file: `/Needs_Action/FAILED_{task_filename}`
2. Check if there's a blocker (missing approval, external dependency)
3. Either:
   - Manually complete the task
   - Fix the blocker and move back to `/Needs_Action/`
   - Archive if no longer needed
"""

        alert_path.write_text(alert_content, encoding='utf-8')

    def _calculate_duration(self, started_iso: str) -> str:
        """Calculate human-readable duration from start time"""
        try:
            started = datetime.fromisoformat(started_iso)
            duration = datetime.now() - started
            hours = duration.total_seconds() / 3600
            if hours < 1:
                return f"{int(duration.total_seconds() / 60)} minutes"
            elif hours < 24:
                return f"{hours:.1f} hours"
            else:
                return f"{hours / 24:.1f} days"
        except:
            return "unknown"

    def load_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Load state from JSON file.
        Returns state dict or None if not found.
        """
        state_file = self.state_path / f"{task_id}.json"
        if not state_file.exists():
            return None

        try:
            return json.loads(state_file.read_text(encoding='utf-8'))
        except Exception:
            return None

    def save_state(self, task_id: str, state: Dict[str, Any]):
        """
        Save state to JSON file.
        """
        state_file = self.state_path / f"{task_id}.json"
        try:
            state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
        except Exception as e:
            print(f"Error saving state: {e}")

    def log_action(
        self,
        action_type: str,
        actor: str,
        target: str,
        result: str,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Log action to database.
        """
        if self.db is None:
            return

        timestamp = datetime.now().isoformat()

        try:
            self.db.log_activity({
                "timestamp": timestamp,
                "level": "INFO" if result == "success" else "ERROR",
                "component": actor,
                "action": action_type,
                "item_id": target,
                "details": f"{actor} -> {target}: {result}"
            })
        except Exception as e:
            print(f"Error logging to database: {e}")


def main():
    """
    Main entry point for testing Ralph Wiggum hook.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Wiggum Stop Hook')
    parser.add_argument('--task-id', type=str, required=True, help='Task ID to check')
    parser.add_argument('--state-path', type=str, help='Path to state files')
    parser.add_argument('--vault-path', type=str, help='Path to vault')

    args = parser.parse_args()

    hook = RalphWiggumHook(state_path=args.state_path, vault_path=args.vault_path)
    should_exit = hook.check_exit(args.task_id)

    if should_exit:
        print(f"Task {args.task_id} complete or failed. Allowing exit.")
        sys.exit(0)
    else:
        print(f"Task {args.task_id} not complete. Blocking exit and re-injecting.")
        sys.exit(1)


if __name__ == '__main__':
    main()
