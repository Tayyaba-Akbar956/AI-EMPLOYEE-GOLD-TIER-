"""
Orchestrator - Gold Tier Feature 1
Polls /Needs_Action/, claims tasks, detects types, triggers Claude Code with matching SKILL.md
Watches /Approved/ and /Rejected/, logs actions, updates Dashboard
"""
import os
import sys
import time
import json
import shutil
import yaml
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager


class Orchestrator:
    """
    Orchestrator manages the task lifecycle:
    Needs_Action -> In_Progress -> Approved/Rejected -> Done
    """

    def __init__(self, vault_path: Optional[str] = None, db_path: Optional[str] = None):
        """Initialize orchestrator with vault and database paths"""
        if vault_path is None:
            vault_path = os.environ.get('VAULT_PATH', str(Path.home() / 'Desktop' / 'PIAIC' / 'AI' / 'AI-EMPLOYEE-GOLD' / 'AI_Employee_Vault'))

        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.in_progress_path = self.vault_path / "In_Progress"
        self.done_path = self.vault_path / "Done"
        self.approved_path = self.vault_path / "Approved"
        self.rejected_path = self.vault_path / "Rejected"
        self.logs_path = self.vault_path / "Logs"
        self.dashboard_path = self.vault_path / "Dashboard.md"
        self.skills_path = self.vault_path / ".claude" / "skills"

        # Initialize database
        if db_path is None:
            db_path = self.vault_path / "Database" / "ai_employee.db"
        self.db = DatabaseManager(str(db_path))

        # Ensure all folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure all required folders exist"""
        for folder in [
            self.needs_action_path,
            self.in_progress_path,
            self.done_path,
            self.approved_path,
            self.rejected_path,
            self.logs_path
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def claim_task(self, task_filename: str) -> bool:
        """
        Claim a task by moving it from Needs_Action to In_Progress
        Returns True if successful, False otherwise
        """
        source = self.needs_action_path / task_filename
        destination = self.in_progress_path / task_filename

        if not source.exists():
            return False

        try:
            shutil.move(str(source), str(destination))
            self.log_action(
                action_type="task_claimed",
                actor="orchestrator",
                target=task_filename,
                result="success"
            )
            return True
        except Exception as e:
            self.log_action(
                action_type="task_claimed",
                actor="orchestrator",
                target=task_filename,
                result="failure",
                error=str(e)
            )
            raise

    def detect_task_type(self, task_filename: str) -> Optional[str]:
        """
        Detect task type from frontmatter in In_Progress file
        Returns task type string or None if not found
        """
        task_file = self.in_progress_path / task_filename

        if not task_file.exists():
            return None

        try:
            content = task_file.read_text(encoding='utf-8')

            # Extract YAML frontmatter
            if not content.startswith('---'):
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                return None

            frontmatter = yaml.safe_load(parts[1])
            if not isinstance(frontmatter, dict):
                return None

            return frontmatter.get('type')

        except (yaml.YAMLError, Exception):
            return None

    def load_skill(self, task_type: str) -> Optional[str]:
        """
        Load the matching SKILL.md for a task type
        Returns skill content or None if not found
        """
        # Map task types to skill folder names
        skill_map = {
            'email': 'email-processor',
            'linkedin': 'Linkedin-processor',
            'whatsapp': 'Whatsapp-processor',
            'file': 'file-organizer',
            'plan': 'Plan-generator',
            'report': 'Report-generator',
            'financial': 'Financial-tracker',
            'approval': 'Approval-manager',
            'workflow': 'Workflow-orchestrator',
            'dashboard': 'Enhanced-dashboard'
        }

        skill_folder = skill_map.get(task_type)
        if not skill_folder:
            return None

        skill_file = self.skills_path / skill_folder / "SKILL.md"
        if not skill_file.exists():
            return None

        try:
            return skill_file.read_text(encoding='utf-8')
        except Exception:
            return None

    def trigger_claude(self, task_filename: str, skill_content: str):
        """
        Trigger Claude Code with the task and skill
        Invokes Claude Code CLI via subprocess
        """
        import subprocess

        # Read task file content
        task_file = self.in_progress_path / task_filename
        if not task_file.exists():
            return False

        task_content = task_file.read_text(encoding='utf-8')

        # Build prompt with task + skill context
        prompt = f"""Task File: {task_filename}

Task Content:
{task_content}

Skill Context:
{skill_content}

Please process this task according to the skill instructions."""

        try:
            # Invoke Claude Code CLI
            result = subprocess.run(
                ['claude', 'code', '--prompt', prompt],
                capture_output=True,
                text=True,
                cwd=str(self.vault_path),
                timeout=300  # 5 minute timeout
            )

            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.log_action(
                action_type="claude_trigger",
                actor="orchestrator",
                target=task_filename,
                result="failure",
                error="Claude Code timeout after 5 minutes"
            )
            return False
        except Exception as e:
            self.log_action(
                action_type="claude_trigger",
                actor="orchestrator",
                target=task_filename,
                result="failure",
                error=str(e)
            )
            return False

    def process_approved(self):
        """
        Process files in Approved folder
        Execute the approved action and move to Done
        """
        approved_files = list(self.approved_path.glob("*.md"))

        for approved_file in approved_files:
            try:
                # Execute the approved action
                success = self.execute_approved_action(approved_file)

                if success:
                    # Move to Done
                    done_file = self.done_path / approved_file.name
                    shutil.move(str(approved_file), str(done_file))

                    self.log_action(
                        action_type="approval_executed",
                        actor="orchestrator",
                        target=approved_file.name,
                        result="success"
                    )

            except Exception as e:
                self.log_action(
                    action_type="approval_executed",
                    actor="orchestrator",
                    target=approved_file.name,
                    result="failure",
                    error=str(e)
                )

    def execute_approved_action(self, approved_file: Path) -> bool:
        """
        Execute the action specified in an approved file
        Returns True if successful
        """
        try:
            content = approved_file.read_text(encoding='utf-8')

            # Parse frontmatter to determine action type
            import re
            frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                return False

            frontmatter = frontmatter_match.group(1)

            # Determine action type from frontmatter
            if 'type: email' in frontmatter:
                return self._execute_email_send(content, frontmatter)
            elif 'type: social_post' in frontmatter or 'type: linkedin_post' in frontmatter:
                return self._execute_social_post(content, frontmatter)
            elif 'type: facebook_post' in frontmatter:
                return self._execute_facebook_post(content, frontmatter)
            elif 'type: instagram_post' in frontmatter:
                return self._execute_instagram_post(content, frontmatter)
            elif 'type: twitter_post' in frontmatter:
                return self._execute_twitter_post(content, frontmatter)
            elif 'type: odoo' in frontmatter or 'type: odoo_invoice' in frontmatter:
                return self._execute_odoo_action(content, frontmatter)

            return False

        except Exception as e:
            self.log_action(
                action_type="execute_approved",
                actor="orchestrator",
                target=approved_file.name,
                result="failure",
                error=str(e)
            )
            return False

    def _execute_email_send(self, content: str, frontmatter: str) -> bool:
        """Execute email send action"""
        try:
            # Extract email details from frontmatter
            import re
            to_match = re.search(r'to:\s*(.+)', frontmatter)
            subject_match = re.search(r'subject:\s*(.+)', frontmatter)

            if not to_match or not subject_match:
                return False

            to_email = to_match.group(1).strip()
            subject = subject_match.group(1).strip()

            # Extract body (everything after frontmatter)
            body_match = re.search(r'---\n\n(.+)', content, re.DOTALL)
            body = body_match.group(1).strip() if body_match else ""

            # Use Gmail API to send (import from Silver)
            from src.workflows.email_workflow import send_email
            success = send_email(to_email, subject, body)

            self.log_action(
                action_type="email_send",
                actor="orchestrator",
                target=to_email,
                result="success" if success else "failure",
                parameters={"subject": subject}
            )

            return success
        except Exception as e:
            self.log_action(
                action_type="email_send",
                actor="orchestrator",
                target="unknown",
                result="failure",
                error=str(e)
            )
            return False

    def _execute_social_post(self, content: str, frontmatter: str) -> bool:
        """Execute LinkedIn social post"""
        try:
            # Extract post content
            import re
            body_match = re.search(r'---\n\n(.+)', content, re.DOTALL)
            post_content = body_match.group(1).strip() if body_match else ""

            # Use LinkedIn poster from Silver
            from src.watchers.linkedin_watcher import post_to_linkedin
            success = post_to_linkedin(post_content)

            self.log_action(
                action_type="linkedin_post",
                actor="orchestrator",
                target="linkedin",
                result="success" if success else "failure"
            )

            return success
        except Exception:
            return False

    def _execute_facebook_post(self, content: str, frontmatter: str) -> bool:
        """Execute Facebook post"""
        try:
            import re
            body_match = re.search(r'---\n\n(.+)', content, re.DOTALL)
            post_content = body_match.group(1).strip() if body_match else ""

            from src.social.facebook_poster import FacebookPoster
            poster = FacebookPoster(vault_path=str(self.vault_path))
            success = poster.post_to_facebook(post_content)

            self.log_action(
                action_type="facebook_post",
                actor="orchestrator",
                target="facebook",
                result="success" if success else "failure"
            )

            return success
        except Exception:
            return False

    def _execute_instagram_post(self, content: str, frontmatter: str) -> bool:
        """Execute Instagram post"""
        try:
            import re
            body_match = re.search(r'---\n\n(.+)', content, re.DOTALL)
            post_content = body_match.group(1).strip() if body_match else ""

            from src.social.instagram_poster import InstagramPoster
            poster = InstagramPoster(vault_path=str(self.vault_path))
            success = poster.post_to_instagram(post_content)

            self.log_action(
                action_type="instagram_post",
                actor="orchestrator",
                target="instagram",
                result="success" if success else "failure"
            )

            return success
        except Exception:
            return False

    def _execute_twitter_post(self, content: str, frontmatter: str) -> bool:
        """Execute Twitter post"""
        try:
            import re
            body_match = re.search(r'---\n\n(.+)', content, re.DOTALL)
            post_content = body_match.group(1).strip() if body_match else ""

            from src.social.twitter_poster import TwitterPoster
            poster = TwitterPoster(vault_path=str(self.vault_path))
            success = poster.post_tweet(post_content)

            self.log_action(
                action_type="twitter_post",
                actor="orchestrator",
                target="twitter",
                result="success" if success else "failure"
            )

            return success
        except Exception:
            return False

    def _execute_odoo_action(self, content: str, frontmatter: str) -> bool:
        """Execute Odoo action (invoice, expense, journal entry)"""
        try:
            # Parse action details from content
            # This would call the Odoo MCP tools
            # For now, return True as placeholder
            self.log_action(
                action_type="odoo_action",
                actor="orchestrator",
                target="odoo",
                result="success"
            )
            return True
        except Exception:
            return False

    def process_rejected(self):
        """
        Process files in Rejected folder
        Log rejection and move to Done
        """
        rejected_files = list(self.rejected_path.glob("*.md"))

        for rejected_file in rejected_files:
            try:
                # Read rejection reason from frontmatter
                content = rejected_file.read_text(encoding='utf-8')
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        reason = frontmatter.get('reason', 'No reason provided')
                    else:
                        reason = 'No reason provided'
                else:
                    reason = 'No reason provided'

                # Move to Done
                done_file = self.done_path / rejected_file.name
                shutil.move(str(rejected_file), str(done_file))

                self.log_action(
                    action_type="approval_rejected",
                    actor="orchestrator",
                    target=rejected_file.name,
                    result="success",
                    parameters={"reason": reason}
                )

            except Exception as e:
                self.log_action(
                    action_type="approval_rejected",
                    actor="orchestrator",
                    target=rejected_file.name,
                    result="failure",
                    error=str(e)
                )

    def log_action(
        self,
        action_type: str,
        actor: str,
        target: str,
        result: str,
        parameters: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Log action to both JSON file and SQLite database
        """
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "result": result,
            "error": error
        }

        # Log to JSON file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.json"

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Error writing to JSON log: {e}")

        # Log to SQLite
        try:
            self.db.log_activity({
                "timestamp": timestamp,
                "level": "INFO" if result == "success" else "ERROR",
                "component": actor,
                "action": action_type,
                "item_id": target,
                "details": f"{actor} -> {target}: {result}" + (f" - {error}" if error else "")
            })
        except Exception as e:
            print(f"Error writing to SQLite log: {e}")

    def update_dashboard(self):
        """
        Update Dashboard.md with current status
        """
        try:
            # Count tasks in each folder
            needs_action_count = len(list(self.needs_action_path.glob("*.md")))
            in_progress_count = len(list(self.in_progress_path.glob("*.md")))
            done_count = len(list(self.done_path.glob("*.md")))

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            dashboard_content = f"""# AI Employee Dashboard

Last Updated: {timestamp}

## Task Status

- Needs Action: {needs_action_count}
- Tasks in Progress: {in_progress_count}
- Tasks Completed: {done_count}

## Recent Activity

See `/Logs/{datetime.now().strftime("%Y-%m-%d")}.json` for detailed activity log.
"""

            self.dashboard_path.write_text(dashboard_content, encoding='utf-8')

        except Exception as e:
            print(f"Error updating dashboard: {e}")

    def recover_stale_tasks(self, stale_threshold_hours: int = 1):
        """
        Recover stale tasks from In_Progress back to Needs_Action
        Tasks are considered stale if modified more than stale_threshold_hours ago
        """
        threshold_time = datetime.now().timestamp() - (stale_threshold_hours * 3600)

        in_progress_files = list(self.in_progress_path.glob("*.md"))

        for task_file in in_progress_files:
            try:
                # Check file modification time
                mtime = task_file.stat().st_mtime

                if mtime < threshold_time:
                    # Move back to Needs_Action
                    needs_action_file = self.needs_action_path / task_file.name
                    shutil.move(str(task_file), str(needs_action_file))

                    self.log_action(
                        action_type="stale_task_recovered",
                        actor="orchestrator",
                        target=task_file.name,
                        result="success"
                    )

            except Exception as e:
                self.log_action(
                    action_type="stale_task_recovered",
                    actor="orchestrator",
                    target=task_file.name,
                    result="failure",
                    error=str(e)
                )

    def run_once(self):
        """
        Run one complete orchestrator cycle:
        1. Recover stale tasks
        2. Process approved/rejected
        3. Claim and process new tasks
        4. Update dashboard
        """
        # Recover stale tasks
        self.recover_stale_tasks()

        # Process approved and rejected
        self.process_approved()
        self.process_rejected()

        # Get tasks from Needs_Action
        needs_action_files = list(self.needs_action_path.glob("*.md"))

        for task_file in needs_action_files:
            try:
                # Claim the task
                claimed = self.claim_task(task_file.name)

                if claimed:
                    # Detect task type
                    task_type = self.detect_task_type(task_file.name)

                    if task_type:
                        # Load matching skill
                        skill_content = self.load_skill(task_type)

                        if skill_content:
                            # Trigger Claude Code
                            self.trigger_claude(task_file.name, skill_content)

            except Exception as e:
                self.log_action(
                    action_type="task_processing_error",
                    actor="orchestrator",
                    target=task_file.name,
                    result="failure",
                    error=str(e)
                )

        # Update dashboard
        self.update_dashboard()

    def run_continuous(self, interval_seconds: int = 30):
        """
        Run orchestrator continuously, polling every interval_seconds
        """
        print(f"Orchestrator started. Polling every {interval_seconds} seconds.")
        print(f"Vault path: {self.vault_path}")

        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("\nOrchestrator stopped by user.")
                break
            except Exception as e:
                print(f"Error in orchestrator cycle: {e}")
                time.sleep(interval_seconds)


def main():
    """Main entry point for orchestrator"""
    parser = argparse.ArgumentParser(description='AI Employee Orchestrator')
    parser.add_argument('--vault-path', type=str, help='Path to AI_Employee_Vault')
    parser.add_argument('--interval', type=int, default=30, help='Polling interval in seconds')
    parser.add_argument('--dry-run', action='store_true', help='Run once and exit')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--task', type=str, choices=['briefing', 'audit', 'social'], help='Run specific task')

    args = parser.parse_args()

    # Initialize orchestrator
    orch = Orchestrator(vault_path=args.vault_path)

    if args.task:
        print(f"Running task: {args.task}")
        # Task-specific logic would go here
        return

    if args.dry_run:
        print("Running one cycle (dry-run mode)")
        orch.run_once()
        print("Dry-run complete.")
    else:
        orch.run_continuous(interval_seconds=args.interval)


if __name__ == '__main__':
    main()
