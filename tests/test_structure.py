"""Phase 1: Structure Tests - Verify vault and folder structure exists"""
from pathlib import Path
import pytest


def test_vault_exists():
    """AI_Employee_Vault directory must exist"""
    assert Path('AI_Employee_Vault').exists(), "Vault directory not found"


def test_vault_is_directory():
    """AI_Employee_Vault must be a directory"""
    assert Path('AI_Employee_Vault').is_dir(), "Vault is not a directory"


def test_inbox_emails_folder():
    """Inbox/emails folder must exist"""
    assert Path('AI_Employee_Vault/Inbox/emails').exists(), "Inbox/emails not found"
    assert Path('AI_Employee_Vault/Inbox/emails').is_dir()


def test_inbox_files_folder():
    """Inbox/files folder must exist"""
    assert Path('AI_Employee_Vault/Inbox/files').exists(), "Inbox/files not found"
    assert Path('AI_Employee_Vault/Inbox/files').is_dir()


def test_needs_action_urgent_folder():
    """Needs_Action/urgent folder must exist"""
    assert Path('AI_Employee_Vault/Needs_Action/urgent').exists()
    assert Path('AI_Employee_Vault/Needs_Action/urgent').is_dir()


def test_needs_action_normal_folder():
    """Needs_Action/normal folder must exist"""
    assert Path('AI_Employee_Vault/Needs_Action/normal').exists()
    assert Path('AI_Employee_Vault/Needs_Action/normal').is_dir()


def test_done_folder():
    """Done folder must exist"""
    assert Path('AI_Employee_Vault/Done').exists()
    assert Path('AI_Employee_Vault/Done').is_dir()


def test_logs_folder():
    """Logs folder must exist"""
    assert Path('AI_Employee_Vault/Logs').exists()
    assert Path('AI_Employee_Vault/Logs').is_dir()


def test_dashboard_exists():
    """Dashboard.md must exist"""
    assert Path('AI_Employee_Vault/Dashboard.md').exists(), "Dashboard.md not found"
    assert Path('AI_Employee_Vault/Dashboard.md').is_file()


def test_handbook_exists():
    """Company_Handbook.md must exist"""
    assert Path('AI_Employee_Vault/Company_Handbook.md').exists()
    assert Path('AI_Employee_Vault/Company_Handbook.md').is_file()


def test_skills_directory():
    """.claude/skills/ must exist with all four skills"""
    skills_dir = Path('AI_Employee_Vault/.claude/skills')
    assert skills_dir.exists(), ".claude/skills directory not found"

    # Check each skill has a SKILL.md file
    required_skills = [
        'vault-management',
        'email-processor',
        'file-organizer',
        'dashboard-updater'
    ]

    for skill_name in required_skills:
        skill_file = skills_dir / skill_name / 'SKILL.md'
        assert skill_file.exists(), f"Skill {skill_name}/SKILL.md not found"


def test_dashboard_has_required_content():
    """Dashboard.md must have required content"""
    dashboard_path = Path('AI_Employee_Vault/Dashboard.md')
    if dashboard_path.exists():
        content = dashboard_path.read_text(encoding='utf-8')
        assert 'AI Employee Dashboard' in content, "Dashboard title missing"
        assert 'Last Updated:' in content, "Last Updated field missing"
        assert "Inbox:" in content, "Inbox count missing"
        assert "Needs Action:" in content, "Needs Action count missing"


def test_handbook_has_required_content():
    """Company_Handbook.md must have required content"""
    handbook_path = Path('AI_Employee_Vault/Company_Handbook.md')
    if handbook_path.exists():
        content = handbook_path.read_text(encoding='utf-8')
        assert 'Company Handbook' in content, "Handbook title missing"
