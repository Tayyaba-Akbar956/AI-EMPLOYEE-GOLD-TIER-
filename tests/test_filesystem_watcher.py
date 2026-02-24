"""Phase 3: Filesystem Watcher Tests"""
from pathlib import Path
import pytest
import tempfile
import time
import shutil


def test_watcher_module_exists():
    """Watcher module must exist"""
    watcher_path = Path('src/watchers/filesystem_watcher.py')
    assert watcher_path.exists(), "filesystem_watcher.py not found"


def test_vault_management_module_exists():
    """Vault management module must exist"""
    vm_path = Path('src/utils/vault_management.py')
    assert vm_path.exists(), "vault_management.py not found"


def test_detect_file_type():
    """File type detection works correctly"""
    from src.watchers.filesystem_watcher import detect_file_type

    # Test PDF
    result = detect_file_type(Path("test.pdf"))
    assert result['type'] == 'document'
    assert result['category'] == 'pdf'

    # Test DOCX
    result = detect_file_type(Path("test.docx"))
    assert result['type'] == 'document'
    assert result['category'] == 'word'

    # Test TXT
    result = detect_file_type(Path("test.txt"))
    assert result['type'] == 'text'
    assert result['category'] == 'plain_text'

    # Test unknown
    result = detect_file_type(Path("test.xyz"))
    assert result['type'] == 'unknown'


def test_extract_file_metadata(tmp_path):
    """Metadata extraction works"""
    from src.watchers.filesystem_watcher import extract_file_metadata

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    metadata = extract_file_metadata(test_file)

    assert metadata['name'] == 'test.txt'
    assert metadata['extension'] == '.txt'
    assert 'size' in metadata
    assert 'created' in metadata
    assert 'modified' in metadata


def test_categorize_file_invoice():
    """Correctly categorizes invoice files"""
    from src.watchers.filesystem_watcher import categorize_file, detect_file_type, extract_file_metadata

    with tempfile.TemporaryDirectory() as tmp:
        invoice_file = Path(tmp) / "invoice_acme_2026.pdf"
        invoice_file.write_text("test")

        file_type = detect_file_type(invoice_file)
        metadata = extract_file_metadata(invoice_file)
        category = categorize_file(invoice_file, file_type, metadata)

        assert category['category'] == 'invoice'
        assert category['priority'] == 'urgent'
        assert 'Needs_Action/urgent/' in category['destination']


def test_categorize_file_receipt():
    """Correctly categorizes receipt files"""
    from src.watchers.filesystem_watcher import categorize_file, detect_file_type, extract_file_metadata

    with tempfile.TemporaryDirectory() as tmp:
        receipt_file = Path(tmp) / "receipt_amazon.pdf"
        receipt_file.write_text("test")

        file_type = detect_file_type(receipt_file)
        metadata = extract_file_metadata(receipt_file)
        category = categorize_file(receipt_file, file_type, metadata)

        assert category['category'] == 'receipt'
        assert category['priority'] == 'normal'


def test_categorize_file_contract():
    """Correctly categorizes contract files"""
    from src.watchers.filesystem_watcher import categorize_file, detect_file_type, extract_file_metadata

    with tempfile.TemporaryDirectory() as tmp:
        contract_file = Path(tmp) / "contract_nda.pdf"
        contract_file.write_text("test")

        file_type = detect_file_type(contract_file)
        metadata = extract_file_metadata(contract_file)
        category = categorize_file(contract_file, file_type, metadata)

        assert category['category'] == 'contract'
        assert category['priority'] == 'urgent'


def test_generate_safe_filename():
    """Safe filename generation works"""
    from src.watchers.filesystem_watcher import generate_safe_filename

    path = Path("My Invoice #123.pdf")
    safe_name = generate_safe_filename(path)

    # Should start with date
    assert len(safe_name) > 10
    assert 'invoice' in safe_name.lower()
    assert safe_name.endswith('.pdf')
    # Should not have special chars
    assert '#' not in safe_name


def test_generate_file_markdown():
    """Markdown generation works"""
    from src.watchers.filesystem_watcher import (generate_file_markdown,
                                                  detect_file_type, extract_file_metadata,
                                                  categorize_file)

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "invoice_test.pdf"
        test_file.write_text("test content")

        file_type = detect_file_type(test_file)
        metadata = extract_file_metadata(test_file)
        category = categorize_file(test_file, file_type, metadata)

        markdown = generate_file_markdown(test_file, metadata, file_type, category)

        assert '# File:' in markdown
        assert 'invoice_test.pdf' in markdown
        assert '**Priority:**' in markdown
        assert '## Metadata' in markdown


def test_organize_file_complete(tmp_path):
    """Complete file organization pipeline works"""
    from src.watchers.filesystem_watcher import organize_file_complete

    # Ensure vault exists
    vault_path = Path('AI_Employee_Vault')
    vault_path.mkdir(exist_ok=True)
    (vault_path / 'Needs_Action' / 'urgent').mkdir(parents=True, exist_ok=True)

    # Create test invoice
    test_file = tmp_path / "invoice_test_company.pdf"
    test_file.write_text("PDF content here")

    # Organize
    result = organize_file_complete(test_file)

    assert result['status'] == 'success'
    assert 'markdown_path' in result
    assert 'file_path' in result
    assert result['category']['category'] == 'invoice'

    # Check files were created
    assert Path(result['markdown_path']).exists()
    assert Path(result['file_path']).exists()


def test_vault_file_operations(tmp_path):
    """Vault file operations work"""
    from src.utils.vault_management import read_vault_file, write_vault_file, list_vault_directory

    # Write test file
    test_content = "# Test Content\n\nThis is a test."
    result = write_vault_file("test_file.md", test_content)
    assert result is True

    # Read test file
    read_content = read_vault_file("test_file.md")
    assert read_content == test_content

    # List directory
    files = list_vault_directory(".", pattern="test_*.md")
    assert "test_file.md" in files

    # Clean up
    Path('AI_Employee_Vault/test_file.md').unlink()


def test_write_log():
    """Logging works"""
    from src.utils.vault_management import write_log
    from datetime import datetime

    write_log("INFO", "TestComponent", "Test message")

    # Check log file was created
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = Path(f'AI_Employee_Vault/Logs/{today}.log')
    assert log_file.exists()

    content = log_file.read_text()
    assert "[INFO]" in content
    assert "[TestComponent]" in content
    assert "Test message" in content
