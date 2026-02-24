"""Phase 4: Integration Tests - End-to-end workflow testing"""
from pathlib import Path
import tempfile
import time
from datetime import datetime
import pytest


def test_complete_file_workflow_invoice():
    """Test complete file processing workflow for invoice"""
    from src.watchers.filesystem_watcher import organize_file_complete
    from src.utils.vault_management import read_vault_file, count_vault_items
    from src.utils.dashboard_updater import update_dashboard_complete

    with tempfile.TemporaryDirectory() as tmp:
        # Create test invoice file
        test_file = Path(tmp) / "URGENT_Invoice_AcmeCorp_5000.pdf"
        test_file.write_text("PDF content - Invoice for $5000")

        # Process the file
        result = organize_file_complete(test_file)

        # Verify result
        assert result['status'] == 'success'
        assert result['category']['category'] == 'invoice'
        assert result['category']['priority'] == 'urgent'
        # Handle both Windows and Unix path separators
        assert 'Needs_Action' in result['markdown_path'] and 'urgent' in result['markdown_path']

        # Verify files were created
        assert Path(result['markdown_path']).exists()
        assert Path(result['file_path']).exists()

        # Verify markdown content - read directly from the path
        md_content = Path(result['markdown_path']).read_text(encoding='utf-8')
        assert 'invoice' in md_content.lower()
        assert '**Priority:** URGENT' in md_content

        # Update dashboard
        dashboard_result = update_dashboard_complete()
        assert dashboard_result['status'] == 'success'

        # Verify counts
        urgent_count = count_vault_items("Needs_Action/urgent", recursive=False)
        assert urgent_count >= 1


def test_complete_file_workflow_receipt():
    """Test complete file processing workflow for receipt"""
    from src.watchers.filesystem_watcher import organize_file_complete
    from src.utils.vault_management import read_vault_file

    with tempfile.TemporaryDirectory() as tmp:
        # Create test receipt file
        test_file = Path(tmp) / "receipt_amazon_purchase.pdf"
        test_file.write_text("PDF content - Receipt")

        # Process the file
        result = organize_file_complete(test_file)

        # Verify result
        assert result['status'] == 'success'
        assert result['category']['category'] == 'receipt'
        assert result['category']['priority'] == 'normal'
        # Handle both Windows and Unix path separators
        assert 'Needs_Action' in result['markdown_path'] and 'normal' in result['markdown_path']

        # Verify markdown content - read directly from the path
        md_content = Path(result['markdown_path']).read_text(encoding='utf-8')
        assert 'receipt' in md_content.lower()


def test_dashboard_updates_correctly():
    """Test that dashboard reflects accurate counts"""
    from src.utils.dashboard_updater import (update_dashboard_complete,
                                             calculate_vault_counts)
    from src.utils.vault_management import write_vault_file

    # Get initial counts
    initial_counts = calculate_vault_counts()

    # Add test files to vault
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Add to urgent
    write_vault_file(f"Needs_Action/urgent/test_urgent_{timestamp}.md",
                     "# Test Urgent\n\nTest content")

    # Add to normal
    write_vault_file(f"Needs_Action/normal/test_normal_{timestamp}.md",
                     "# Test Normal\n\nTest content")

    # Update dashboard
    result = update_dashboard_complete()
    assert result['status'] == 'success'

    # Read dashboard
    from src.utils.vault_management import read_vault_file
    dashboard = read_vault_file("Dashboard.md")

    # Verify dashboard content
    assert "AI Employee Dashboard" in dashboard
    assert "Today's Summary" in dashboard
    assert "System Status" in dashboard

    # Verify new counts are reflected
    new_counts = calculate_vault_counts()
    assert new_counts['needs_action']['urgent'] >= initial_counts['needs_action']['urgent'] + 1
    assert new_counts['needs_action']['normal'] >= initial_counts['needs_action']['normal'] + 1


def test_log_generation():
    """Test that logs are generated properly"""
    from src.utils.vault_management import write_log
    from datetime import datetime

    # Write test log entries
    write_log("INFO", "TestIntegration", "Test info message")
    write_log("WARN", "TestIntegration", "Test warning message")
    write_log("ERROR", "TestIntegration", "Test error message")

    # Check log file
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = Path(f'AI_Employee_Vault/Logs/{today}.log')
    assert log_file.exists()

    content = log_file.read_text()
    assert "[INFO] [TestIntegration] Test info message" in content
    assert "[WARN] [TestIntegration] Test warning message" in content
    assert "[ERROR] [TestIntegration] Test error message" in content


def test_activity_tracking():
    """Test activity tracking and display"""
    from src.utils.dashboard_updater import add_activity, get_recent_activities

    # Add test activities
    add_activity("Test activity 1")
    time.sleep(0.1)
    add_activity("Test activity 2")
    time.sleep(0.1)
    add_activity("Test activity 3")

    # Get activities
    activities = get_recent_activities()

    # Verify activities are tracked
    assert "Test activity 1" in activities
    assert "Test activity 2" in activities
    assert "Test activity 3" in activities


def test_daily_stats_tracking():
    """Test daily statistics tracking"""
    from src.utils.dashboard_updater import (update_daily_stats,
                                             load_daily_stats,
                                             get_daily_stats_formatted)

    # Get initial stats
    initial_stats = load_daily_stats()
    initial_files = initial_stats['files_organized']

    # Update stats
    update_daily_stats('file')
    update_daily_stats('file')
    update_daily_stats('email')

    # Verify stats
    new_stats = load_daily_stats()
    assert new_stats['files_organized'] == initial_files + 2
    assert new_stats['emails_processed'] >= 1

    # Verify formatted output
    formatted = get_daily_stats_formatted()
    assert "Files Organized:" in formatted
    assert "Emails Processed:" in formatted


def test_error_recovery():
    """Test system continues working after errors"""
    from src.watchers.filesystem_watcher import organize_file_complete
    from src.utils.vault_management import write_log

    # This should not crash the system
    write_log("ERROR", "TestIntegration", "Simulated error for testing")

    # System should continue working
    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "test_document_after_error.pdf"
        test_file.write_text("Test content")

        result = organize_file_complete(test_file)
        assert result['status'] == 'success'


def test_vault_file_operations_integration():
    """Test vault file read/write/list/count operations"""
    from src.utils.vault_management import (write_vault_file, read_vault_file,
                                            list_vault_directory, count_vault_items)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Test write
    test_content = f"# Integration Test\n\nTimestamp: {timestamp}"
    assert write_vault_file(f"test_integration_{timestamp}.md", test_content) is True

    # Test read
    read_content = read_vault_file(f"test_integration_{timestamp}.md")
    assert read_content == test_content

    # Test list
    files = list_vault_directory(".", pattern=f"test_integration_{timestamp}.md")
    assert f"test_integration_{timestamp}.md" in files

    # Test count
    count_before = count_vault_items(".", recursive=True)

    # Add another file
    write_vault_file(f"test_integration_2_{timestamp}.md", test_content)

    count_after = count_vault_items(".", recursive=True)
    assert count_after >= count_before + 1

    # Cleanup
    Path(f'AI_Employee_Vault/test_integration_{timestamp}.md').unlink()
    Path(f'AI_Employee_Vault/test_integration_2_{timestamp}.md').unlink()


def test_end_to_end_multiple_files():
    """Test processing multiple files sequentially"""
    from src.watchers.filesystem_watcher import organize_file_complete
    from src.utils.vault_management import count_vault_items
    from src.utils.dashboard_updater import update_dashboard_complete

    with tempfile.TemporaryDirectory() as tmp:
        # Create multiple test files
        files = [
            ("invoice_company_a.pdf", "invoice", "urgent"),
            ("receipt_store_b.pdf", "receipt", "normal"),
            ("contract_client_c.pdf", "contract", "urgent"),
            ("report_quarterly.pdf", "report", "normal"),
        ]

        results = []
        for filename, expected_type, expected_priority in files:
            test_file = Path(tmp) / filename
            test_file.write_text(f"Content for {filename}")

            result = organize_file_complete(test_file)
            results.append((result, expected_type, expected_priority))

        # Verify all succeeded with correct categorization
        urgent_count = 0
        normal_count = 0
        for result, expected_type, expected_priority in results:
            assert result['status'] == 'success'
            assert result['category']['category'] == expected_type
            assert result['category']['priority'] == expected_priority

            # Count by priority
            if expected_priority == 'urgent':
                urgent_count += 1
            else:
                normal_count += 1

            # Verify files were created
            assert Path(result['markdown_path']).exists()
            assert Path(result['file_path']).exists()

        # Update dashboard
        update_dashboard_complete()

        # Verify we processed the expected number of each priority
        assert urgent_count == 2  # invoice and contract
        assert normal_count == 2  # receipt and report


def test_vault_structure_integrity():
    """Test that vault structure remains intact during operations"""
    from src.utils.vault_management import (count_vault_items, list_vault_directory)

    # Verify all required directories exist and are accessible
    assert count_vault_items("Inbox", recursive=True) >= 0
    assert count_vault_items("Needs_Action/urgent", recursive=False) >= 0
    assert count_vault_items("Needs_Action/normal", recursive=False) >= 0
    assert count_vault_items("Done", recursive=True) >= 0
    assert count_vault_items("Logs", recursive=False) >= 0

    # Verify Dashboard and Handbook exist
    dashboard = list_vault_directory(".", pattern="Dashboard.md")
    assert "Dashboard.md" in dashboard

    handbook = list_vault_directory(".", pattern="Company_Handbook.md")
    assert "Company_Handbook.md" in handbook


@pytest.mark.parametrize("file_type,expected_category,expected_priority", [
    ("invoice_acme.pdf", "invoice", "urgent"),
    ("receipt_amazon.pdf", "receipt", "normal"),
    ("contract_nda.pdf", "contract", "urgent"),
    ("report_quarterly.pdf", "report", "normal"),
    ("document_general.pdf", "document", "normal"),
])
def test_categorization_integration(file_type, expected_category, expected_priority):
    """Test file categorization for different file types"""
    from src.watchers.filesystem_watcher import organize_file_complete

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / file_type
        test_file.write_text("Test content")

        result = organize_file_complete(test_file)

        assert result['status'] == 'success'
        assert result['category']['category'] == expected_category
        assert result['category']['priority'] == expected_priority
