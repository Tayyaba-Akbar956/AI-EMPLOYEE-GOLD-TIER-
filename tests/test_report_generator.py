"""Tests for Report Generator - Phase 8 Silver Tier."""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from src.skills.report_generator import ReportGenerator


class TestWeeklyReports:
    """Test weekly report generation."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        vault_dir = tempfile.mkdtemp()
        generator = ReportGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_generate_weekly_report(self, generator):
        """Test generating weekly report."""
        result = generator.generate_weekly_report()

        assert result['success'] is True
        assert result['filepath'] is not None
        assert os.path.exists(result['filepath'])

    def test_weekly_report_content(self, generator):
        """Test weekly report contains required sections."""
        result = generator.generate_weekly_report()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Weekly Activity Report' in content
        assert 'Items by Source' in content
        assert 'Top Categories' in content

    def test_weekly_report_date_range(self, generator):
        """Test weekly report covers correct date range."""
        result = generator.generate_weekly_report()

        # Should cover last 7 days
        assert result['date_range'] is not None
        assert 'start_date' in result['date_range']
        assert 'end_date' in result['date_range']


class TestMonthlyReports:
    """Test monthly report generation."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        vault_dir = tempfile.mkdtemp()
        generator = ReportGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_generate_monthly_report(self, generator):
        """Test generating monthly report."""
        result = generator.generate_monthly_report()

        assert result['success'] is True
        assert result['filepath'] is not None
        assert os.path.exists(result['filepath'])

    def test_monthly_report_content(self, generator):
        """Test monthly report contains required sections."""
        result = generator.generate_monthly_report()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Monthly Financial Report' in content
        assert 'Invoices' in content or 'invoices' in content.lower()
        assert 'Expenses' in content or 'expenses' in content.lower()

    def test_monthly_report_csv_export(self, generator):
        """Test monthly report CSV export."""
        result = generator.generate_monthly_report()

        # Should also create CSV file
        csv_path = result['filepath'].replace('.md', '.csv')
        assert os.path.exists(csv_path)


class TestCustomReports:
    """Test custom report generation."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        vault_dir = tempfile.mkdtemp()
        generator = ReportGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_generate_custom_report(self, generator):
        """Test generating custom report."""
        start_date = '2026-02-01'
        end_date = '2026-02-18'

        result = generator.generate_custom_report(start_date, end_date)

        assert result['success'] is True
        assert result['filepath'] is not None

    def test_custom_report_date_range(self, generator):
        """Test custom report respects date range."""
        start_date = '2026-02-01'
        end_date = '2026-02-15'

        result = generator.generate_custom_report(start_date, end_date)

        assert result['date_range']['start_date'] == start_date
        assert result['date_range']['end_date'] == end_date


class TestReportFormatting:
    """Test report formatting."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        vault_dir = tempfile.mkdtemp()
        generator = ReportGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_markdown_formatting(self, generator):
        """Test markdown formatting."""
        result = generator.generate_weekly_report()
        filepath = result['filepath']

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for markdown elements
        assert '#' in content  # Headers
        assert '**' in content or '*' in content  # Bold or emphasis

    def test_report_file_location(self, generator):
        """Test report saved to correct location."""
        result = generator.generate_weekly_report()
        filepath = result['filepath']

        assert 'Reports' in filepath
        assert 'weekly' in filepath

    def test_monthly_report_location(self, generator):
        """Test monthly report saved to correct location."""
        result = generator.generate_monthly_report()
        filepath = result['filepath']

        assert 'Reports' in filepath
        assert 'monthly' in filepath


class TestDataAggregation:
    """Test data aggregation for reports."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        vault_dir = tempfile.mkdtemp()
        generator = ReportGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_aggregate_by_source(self, generator):
        """Test aggregating items by source."""
        data = generator.aggregate_by_source('2026-02-01', '2026-02-18')

        assert isinstance(data, dict)
        # Should have source categories
        assert 'email' in data or 'whatsapp' in data or 'linkedin' in data or len(data) == 0

    def test_aggregate_by_category(self, generator):
        """Test aggregating items by category."""
        data = generator.aggregate_by_category('2026-02-01', '2026-02-18')

        assert isinstance(data, dict)

    def test_calculate_time_saved(self, generator):
        """Test calculating time saved."""
        time_saved = generator.calculate_time_saved('2026-02-01', '2026-02-18')

        assert isinstance(time_saved, (int, float))
        assert time_saved >= 0


class TestCSVExport:
    """Test CSV export functionality."""

    @pytest.fixture
    def generator(self):
        """Create report generator."""
        vault_dir = tempfile.mkdtemp()
        generator = ReportGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_export_to_csv(self, generator):
        """Test exporting data to CSV."""
        data = {
            'Category': ['Meals', 'Travel', 'Supplies'],
            'Amount': [100, 200, 50]
        }

        csv_path = generator.export_to_csv(data, 'test_export')

        assert os.path.exists(csv_path)
        assert csv_path.endswith('.csv')

    def test_csv_content(self, generator):
        """Test CSV file content."""
        data = {
            'Category': ['Meals', 'Travel'],
            'Amount': [100, 200]
        }

        csv_path = generator.export_to_csv(data, 'test_export')

        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Category' in content
        assert 'Amount' in content
        assert 'Meals' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
