"""Phase 2: Skill Validation Tests - Verify skills have valid YAML frontmatter"""
from pathlib import Path
import pytest
import yaml


SKILLS_DIR = Path('AI_Employee_Vault/.claude/skills')
REQUIRED_SKILLS = [
    'vault-management',
    'email-processor',
    'file-organizer',
    'dashboard-updater'
]


def extract_yaml_frontmatter(content: str) -> dict:
    """Extract and parse YAML frontmatter from markdown content"""
    parts = content.split('---')
    if len(parts) < 3:
        raise ValueError("No YAML frontmatter found")
    return yaml.safe_load(parts[1])


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_skill_file_exists(skill_name):
    """Each skill must have a SKILL.md file"""
    skill_file = SKILLS_DIR / skill_name / 'SKILL.md'
    assert skill_file.exists(), f"Skill file {skill_file} not found"


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_skill_has_yaml_frontmatter(skill_name):
    """Each skill must have valid YAML frontmatter"""
    skill_file = SKILLS_DIR / skill_name / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8')

    parts = content.split('---')
    assert len(parts) >= 3, f"{skill_name}: Must have YAML frontmatter"

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        pytest.fail(f"{skill_name}: Invalid YAML: {e}")

    assert frontmatter is not None, f"{skill_name}: YAML frontmatter is empty"


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_skill_has_name_field(skill_name):
    """Each skill must have a 'name' field in YAML"""
    skill_file = SKILLS_DIR / skill_name / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8')
    frontmatter = extract_yaml_frontmatter(content)

    assert 'name' in frontmatter, f"{skill_name}: Missing 'name' field"
    assert frontmatter['name'] == skill_name, f"{skill_name}: Name mismatch"


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_skill_has_description_field(skill_name):
    """Each skill must have a 'description' field in YAML"""
    skill_file = SKILLS_DIR / skill_name / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8')
    frontmatter = extract_yaml_frontmatter(content)

    assert 'description' in frontmatter, f"{skill_name}: Missing 'description' field"
    assert len(frontmatter['description']) > 50, f"{skill_name}: Description too short"


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_skill_description_has_trigger(skill_name):
    """Each skill description should indicate when to use it"""
    skill_file = SKILLS_DIR / skill_name / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8')
    frontmatter = extract_yaml_frontmatter(content)

    description = frontmatter['description'].lower()
    assert 'use when' in description or 'use this' in description, \
        f"{skill_name}: Description should include usage trigger"


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_skill_has_documentation(skill_name):
    """Each skill must have substantial documentation"""
    skill_file = SKILLS_DIR / skill_name / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8')

    # Skip frontmatter
    parts = content.split('---')
    body = '---'.join(parts[2:]) if len(parts) > 2 else content

    assert len(body) > 500, f"{skill_name}: Documentation too short"
    assert '# ' in body, f"{skill_name}: Missing main heading"


def test_vault_management_skill():
    """Vault management skill has correct content"""
    skill_file = SKILLS_DIR / 'vault-management' / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8').lower()

    assert 'read_vault_file' in content or 'file' in content
    assert 'write_vault_file' in content or 'write' in content
    assert 'dashboard' in content or 'log' in content


def test_email_processor_skill():
    """Email processor skill has correct content"""
    skill_file = SKILLS_DIR / 'email-processor' / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8').lower()

    assert 'email' in content
    assert 'urgent' in content or 'priority' in content
    assert 'inbox' in content or 'needs_action' in content


def test_file_organizer_skill():
    """File organizer skill has correct content"""
    skill_file = SKILLS_DIR / 'file-organizer' / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8').lower()

    assert 'file' in content
    assert 'categorize' in content or 'organize' in content
    assert 'pdf' in content or 'document' in content


def test_dashboard_updater_skill():
    """Dashboard updater skill has correct content"""
    skill_file = SKILLS_DIR / 'dashboard-updater' / 'SKILL.md'
    content = skill_file.read_text(encoding='utf-8').lower()

    assert 'dashboard' in content
    assert 'count' in content or 'update' in content
    assert 'status' in content or 'activity' in content
