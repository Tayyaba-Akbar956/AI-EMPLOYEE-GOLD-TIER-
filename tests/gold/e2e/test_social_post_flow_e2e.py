"""
E2E test for social media posting workflow
Tests: Task created → Orchestrator → Approval → Post → Done
"""
import pytest
from pathlib import Path
import shutil
import json
from datetime import datetime


@pytest.fixture
def vault_path(tmp_path):
    """Create temporary vault structure"""
    vault = tmp_path / "AI_Employee_Vault"
    vault.mkdir()

    # Create all required folders
    (vault / "Needs_Action").mkdir()
    (vault / "In_Progress").mkdir()
    (vault / "Pending_Approval").mkdir()
    (vault / "Approved").mkdir()
    (vault / "Rejected").mkdir()
    (vault / "Done").mkdir()
    (vault / "Logs").mkdir()
    (vault / ".claude" / "skills" / "social-media-manager").mkdir(parents=True)

    # Create skill file
    skill_content = """# Social Media Manager Skill
Manage posts across Facebook, Instagram, Twitter, LinkedIn."""
    (vault / ".claude" / "skills" / "social-media-manager" / "SKILL.md").write_text(skill_content)

    return vault


class TestSocialMediaFlowE2E:
    """Test complete social media posting workflow end-to-end"""

    def test_facebook_post_workflow(self, vault_path, monkeypatch):
        """Test complete Facebook post flow"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))
        monkeypatch.setenv('RALPH_STATE_PATH', str(vault_path / 'ralph_state'))

        # Step 1: Create social media task
        task_content = """---
type: facebook_post
platform: facebook
scheduled: false
---

Exciting news! We're launching our new product next week. Stay tuned! 🚀
"""
        task_file = vault_path / "Needs_Action" / "SOCIAL_FB_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Step 2: Orchestrator claims task
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Simulate Claude creating approval file
            approval_content = """---
type: facebook_post
platform: facebook
visibility: public
---

Exciting news! We're launching our new product next week. Stay tuned! 🚀
"""
            approval_file = vault_path / "Pending_Approval" / "SOCIAL_FB_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify task claimed and approval created
        assert (vault_path / "In_Progress" / "SOCIAL_FB_001.md").exists()
        assert (vault_path / "Pending_Approval" / "SOCIAL_FB_001_approval.md").exists()

        # Step 3: Human approves
        approval_file = vault_path / "Pending_Approval" / "SOCIAL_FB_001_approval.md"
        approved_file = vault_path / "Approved" / "SOCIAL_FB_001_approval.md"
        shutil.move(str(approval_file), str(approved_file))

        # Step 4: Orchestrator executes post
        def mock_facebook_post(content, frontmatter):
            return True

        orch._execute_facebook_post = mock_facebook_post
        orch.process_approved()

        # Verify posted and moved to Done
        assert (vault_path / "Done" / "SOCIAL_FB_001_approval.md").exists()

        # Verify logs
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = vault_path / "Logs" / f"{today}.json"
        assert log_file.exists()

    def test_twitter_post_with_character_limit(self, vault_path, monkeypatch):
        """Test Twitter post with 280 character limit enforcement"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create task with long content
        long_content = "A" * 300  # Exceeds 280 chars
        task_content = f"""---
type: twitter_post
platform: twitter
---

{long_content}
"""
        task_file = vault_path / "Needs_Action" / "SOCIAL_TW_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Claude should truncate to 280 chars
            truncated = long_content[:277] + "..."
            approval_content = f"""---
type: twitter_post
platform: twitter
---

{truncated}
"""
            approval_file = vault_path / "Pending_Approval" / "SOCIAL_TW_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify approval file has truncated content
        approval_file = vault_path / "Pending_Approval" / "SOCIAL_TW_001_approval.md"
        content = approval_file.read_text(encoding='utf-8')

        # Extract body after frontmatter
        body = content.split('---')[2].strip()
        assert len(body) <= 280
        assert body.endswith("...")

    def test_instagram_post_workflow(self, vault_path, monkeypatch):
        """Test Instagram post with image"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create Instagram task
        task_content = """---
type: instagram_post
platform: instagram
has_image: true
image_path: /path/to/image.jpg
---

Beautiful sunset today! 🌅 #nature #photography
"""
        task_file = vault_path / "Needs_Action" / "SOCIAL_IG_001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            approval_content = """---
type: instagram_post
platform: instagram
has_image: true
image_path: /path/to/image.jpg
---

Beautiful sunset today! 🌅 #nature #photography
"""
            approval_file = vault_path / "Pending_Approval" / "SOCIAL_IG_001_approval.md"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify approval created
        assert (vault_path / "Pending_Approval" / "SOCIAL_IG_001_approval.md").exists()

        # Approve and execute
        approval_file = vault_path / "Pending_Approval" / "SOCIAL_IG_001_approval.md"
        approved_file = vault_path / "Approved" / "SOCIAL_IG_001_approval.md"
        shutil.move(str(approval_file), str(approved_file))

        def mock_instagram_post(content, frontmatter):
            return True

        orch._execute_instagram_post = mock_instagram_post
        orch.process_approved()

        # Verify completed
        assert (vault_path / "Done" / "SOCIAL_IG_001_approval.md").exists()

    def test_multi_platform_posting(self, vault_path, monkeypatch):
        """Test posting to multiple platforms simultaneously"""
        from src.orchestrator.orchestrator import Orchestrator

        monkeypatch.setenv('VAULT_PATH', str(vault_path))

        # Create tasks for all platforms
        platforms = ['facebook', 'twitter', 'instagram']
        for platform in platforms:
            task_content = f"""---
type: {platform}_post
platform: {platform}
---

Multi-platform announcement! Check out our new website.
"""
            task_file = vault_path / "Needs_Action" / f"SOCIAL_{platform.upper()[:2]}_multi.md"
            task_file.write_text(task_content, encoding='utf-8')

        # Orchestrator processes all
        orch = Orchestrator(vault_path=str(vault_path))

        def mock_trigger_claude(task_filename, skill_content):
            # Extract platform from filename
            if 'FB' in task_filename:
                platform = 'facebook'
            elif 'TW' in task_filename:
                platform = 'twitter'
            else:
                platform = 'instagram'

            approval_content = f"""---
type: {platform}_post
platform: {platform}
---

Multi-platform announcement! Check out our new website.
"""
            approval_file = vault_path / "Pending_Approval" / f"{task_filename.replace('.md', '_approval.md')}"
            approval_file.write_text(approval_content, encoding='utf-8')
            return True

        orch.trigger_claude = mock_trigger_claude
        orch.run_once()

        # Verify all approval files created
        approval_files = list((vault_path / "Pending_Approval").glob("SOCIAL_*_approval.md"))
        assert len(approval_files) == 3

        # Verify all tasks claimed
        in_progress_files = list((vault_path / "In_Progress").glob("SOCIAL_*.md"))
        assert len(in_progress_files) == 3
