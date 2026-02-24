"""Tests for LinkedIn processor - Phase 4 Silver Tier."""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from src.processors.linkedin_processor import LinkedInProcessor


class TestContentParsing:
    """Test LinkedIn content parsing."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_parse_job_message(self, processor):
        """Test parsing job opportunity message."""
        message_data = {
            'sender_name': 'Jane Recruiter',
            'sender_profile': 'https://linkedin.com/in/jane-recruiter',
            'company': 'Tech Corp',
            'body': 'We have an exciting Senior Developer position available',
            'timestamp': '2026-02-18T10:00:00Z',
            'message_type': 'direct'
        }

        result = processor.parse_linkedin_content(message_data)

        assert result['sender_name'] == 'Jane Recruiter'
        assert result['company'] == 'Tech Corp'
        assert result['message_type'] == 'direct'
        assert 'Senior Developer' in result['body']

    def test_parse_connection_request(self, processor):
        """Test parsing connection request."""
        message_data = {
            'sender_name': 'John Smith',
            'sender_profile': 'https://linkedin.com/in/john-smith',
            'company': 'Startup Inc',
            'body': 'I would like to connect with you',
            'timestamp': '2026-02-18T10:00:00Z',
            'message_type': 'connection_request'
        }

        result = processor.parse_linkedin_content(message_data)

        assert result['message_type'] == 'connection_request'
        assert result['sender_name'] == 'John Smith'


class TestJobOpportunityDetection:
    """Test job opportunity detection."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_detect_job_with_position_keyword(self, processor):
        """Test job detection with 'position' keyword."""
        content = "We have an open position for a Senior Engineer"
        is_job = processor.identify_job_opportunity(content)
        assert is_job is True

    def test_detect_job_with_opportunity_keyword(self, processor):
        """Test job detection with 'opportunity' keyword."""
        content = "Exciting opportunity to join our team as a Developer"
        is_job = processor.identify_job_opportunity(content)
        assert is_job is True

    def test_detect_job_with_role_keyword(self, processor):
        """Test job detection with 'role' keyword."""
        content = "Looking for someone to fill a technical role"
        is_job = processor.identify_job_opportunity(content)
        assert is_job is True

    def test_detect_job_with_hiring_keyword(self, processor):
        """Test job detection with 'hiring' keyword."""
        content = "We're hiring for multiple positions"
        is_job = processor.identify_job_opportunity(content)
        assert is_job is True

    def test_non_job_message(self, processor):
        """Test non-job message is not detected as job."""
        content = "Thanks for connecting! How have you been?"
        is_job = processor.identify_job_opportunity(content)
        assert is_job is False


class TestSalaryExtraction:
    """Test salary information extraction."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_extract_salary_range(self, processor):
        """Test extracting salary range."""
        content = "Position offers $120,000 - $150,000 per year"
        salary_info = processor.extract_salary_info(content)

        assert salary_info is not None
        assert salary_info['min'] == 120000
        assert salary_info['max'] == 150000
        assert salary_info['currency'] == 'USD'

    def test_extract_single_salary(self, processor):
        """Test extracting single salary amount."""
        content = "Compensation: $130,000 annually"
        salary_info = processor.extract_salary_info(content)

        assert salary_info is not None
        assert salary_info['amount'] == 130000
        assert salary_info['currency'] == 'USD'

    def test_extract_salary_with_k_notation(self, processor):
        """Test extracting salary with 'k' notation."""
        content = "Salary: $120k - $150k"
        salary_info = processor.extract_salary_info(content)

        assert salary_info is not None
        assert salary_info['min'] == 120000
        assert salary_info['max'] == 150000

    def test_no_salary_mentioned(self, processor):
        """Test when no salary is mentioned."""
        content = "Great opportunity to join our team"
        salary_info = processor.extract_salary_info(content)

        assert salary_info is None


class TestJobDetailsExtraction:
    """Test job details extraction."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_extract_remote_location(self, processor):
        """Test extracting remote work type."""
        content = "Senior Developer position - Remote work available"
        details = processor.extract_job_details(content)

        assert 'remote' in details['location'].lower()

    def test_extract_city_location(self, processor):
        """Test extracting city location."""
        content = "Position based in San Francisco, CA"
        details = processor.extract_job_details(content)

        assert 'San Francisco' in details['location']

    def test_extract_job_title(self, processor):
        """Test extracting job title."""
        content = "We're hiring a Senior Software Engineer"
        details = processor.extract_job_details(content)

        assert 'Senior Software Engineer' in details['title'] or 'Senior' in details['title']

    def test_extract_hybrid_work(self, processor):
        """Test extracting hybrid work type."""
        content = "Hybrid position - 3 days in office, 2 days remote"
        details = processor.extract_job_details(content)

        assert 'hybrid' in details['location'].lower()


class TestOpportunitySummaryGeneration:
    """Test opportunity summary generation."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_summary_has_header(self, processor):
        """Test summary has proper header."""
        parsed_data = {
            'sender_name': 'Jane Recruiter',
            'sender_profile': 'https://linkedin.com/in/jane-recruiter',
            'company': 'Tech Corp',
            'body': 'Senior Developer position available',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Senior Developer',
            'location': 'Remote',
            'salary': {'min': 120000, 'max': 150000, 'currency': 'USD'}
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)

        assert '# LinkedIn:' in summary
        assert 'Jane Recruiter' in summary

    def test_summary_includes_salary(self, processor):
        """Test summary includes salary information."""
        parsed_data = {
            'sender_name': 'Recruiter',
            'company': 'Company',
            'body': 'Job available',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Developer',
            'location': 'Remote',
            'salary': {'min': 120000, 'max': 150000, 'currency': 'USD'}
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)

        assert '120000' in summary or '120,000' in summary or '$120k' in summary

    def test_summary_includes_location(self, processor):
        """Test summary includes location."""
        parsed_data = {
            'sender_name': 'Recruiter',
            'company': 'Company',
            'body': 'Job available',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Developer',
            'location': 'San Francisco, CA',
            'salary': None
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)

        assert 'San Francisco' in summary


class TestContentCategorization:
    """Test content categorization."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_categorize_job_opportunity(self, processor):
        """Test job opportunity categorization."""
        content = "We have an exciting position for a Senior Developer"
        category = processor.categorize_linkedin_content(content)

        assert category == 'job_opportunity'

    def test_categorize_networking_request(self, processor):
        """Test networking request categorization."""
        content = "I'd like to connect and discuss potential collaboration"
        category = processor.categorize_linkedin_content(content)

        assert category == 'networking_request'

    def test_categorize_business_inquiry(self, processor):
        """Test business inquiry categorization."""
        content = "Interested in discussing a partnership opportunity"
        category = processor.categorize_linkedin_content(content)

        assert category == 'business_inquiry'

    def test_categorize_general_message(self, processor):
        """Test general message categorization."""
        content = "Thanks for the connection!"
        category = processor.categorize_linkedin_content(content)

        assert category == 'general_message'


class TestContentFiltering:
    """Test content filtering logic."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_should_process_job_opportunity(self, processor):
        """Test job opportunities should be processed."""
        content_data = {
            'body': 'Exciting opportunity for Senior Developer position',
            'sender_name': 'Tech Recruiter'
        }

        should_process = processor.should_process_content(content_data)
        assert should_process is True

    def test_should_skip_promotional_content(self, processor):
        """Test promotional content should be skipped."""
        content_data = {
            'body': 'Check out our latest webinar on marketing trends',
            'sender_name': 'Marketing Team'
        }

        should_process = processor.should_process_content(content_data)
        assert should_process is False

    def test_should_process_business_inquiry(self, processor):
        """Test business inquiries should be processed."""
        content_data = {
            'body': 'Would like to discuss a potential partnership',
            'sender_name': 'Business Development'
        }

        should_process = processor.should_process_content(content_data)
        assert should_process is True


class TestFileOperations:
    """Test file operations."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor with temp vault."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_save_opportunity_creates_file(self, processor):
        """Test saving opportunity creates file."""
        parsed_data = {
            'sender_name': 'Recruiter',
            'company': 'Tech Corp',
            'body': 'Senior Developer position',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Senior Developer',
            'location': 'Remote',
            'salary': {'min': 120000, 'max': 150000, 'currency': 'USD'}
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)
        filepath = processor.save_opportunity(summary, parsed_data)

        assert os.path.exists(filepath)
        assert filepath.endswith('.md')

    def test_save_opportunity_correct_location(self, processor):
        """Test opportunity saved to correct location."""
        parsed_data = {
            'sender_name': 'Recruiter',
            'company': 'Company',
            'body': 'Job',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Developer',
            'location': 'Remote',
            'salary': None
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)
        filepath = processor.save_opportunity(summary, parsed_data)

        # Should be in Inbox/linkedin
        assert 'Inbox' in filepath or 'linkedin' in filepath

    def test_save_opportunity_special_characters(self, processor):
        """Test saving opportunity with special characters in name."""
        parsed_data = {
            'sender_name': 'John/Doe (Recruiter)',
            'company': 'Company',
            'body': 'Job',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Developer',
            'location': 'Remote',
            'salary': None
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)
        filepath = processor.save_opportunity(summary, parsed_data)

        assert os.path.exists(filepath)
        # Special characters should be removed
        assert '/' not in os.path.basename(filepath)
        assert '(' not in os.path.basename(filepath)


class TestCustomConfiguration:
    """Test custom configuration."""

    def test_custom_config_override(self):
        """Test custom configuration overrides defaults."""
        vault_dir = tempfile.mkdtemp()
        custom_config = {
            'job_keywords': ['custom_job'],
            'minimum_salary': 100000
        }
        processor = LinkedInProcessor(vault_dir, config=custom_config)

        assert 'custom_job' in processor.config['job_keywords']
        assert processor.config['minimum_salary'] == 100000

        shutil.rmtree(vault_dir)


class TestSpamDetection:
    """Test spam detection."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_categorize_spam_content(self, processor):
        """Test spam content categorization."""
        content = "Join our exclusive webinar on marketing strategies"
        category = processor.categorize_linkedin_content(content)

        assert category == 'spam'

    def test_should_skip_spam_content(self, processor):
        """Test spam content should be skipped."""
        content_data = {
            'body': 'Check out our new training course with 50% discount',
            'sender_name': 'Marketing'
        }

        should_process = processor.should_process_content(content_data)
        assert should_process is False


class TestCompleteProcessing:
    """Test complete processing flow."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_process_job_opportunity_complete(self, processor):
        """Test complete job opportunity processing."""
        content_data = {
            'sender_name': 'Jane Recruiter',
            'sender_profile': 'https://linkedin.com/in/jane',
            'company': 'Tech Corp',
            'body': 'Exciting opportunity for Senior Developer position. Salary: $120k - $150k. Remote work.',
            'timestamp': '2026-02-18T10:00:00Z',
            'message_type': 'direct'
        }

        result = processor.process_content(content_data)

        assert result['success'] is True
        assert result['processed'] is True
        assert result['category'] == 'job_opportunity'
        assert 'filepath' in result
        assert os.path.exists(result['filepath'])

    def test_process_business_inquiry_complete(self, processor):
        """Test complete business inquiry processing."""
        content_data = {
            'sender_name': 'Business Partner',
            'company': 'Partner Inc',
            'body': 'Interested in discussing a potential partnership for our new project',
            'timestamp': '2026-02-18T10:00:00Z',
            'message_type': 'direct'
        }

        result = processor.process_content(content_data)

        assert result['success'] is True
        assert result['processed'] is True
        assert result['category'] == 'business_inquiry'

    def test_process_filtered_content(self, processor):
        """Test processing filtered content."""
        content_data = {
            'sender_name': 'Spammer',
            'company': 'Spam Inc',
            'body': 'Join our webinar',
            'timestamp': '2026-02-18T10:00:00Z',
            'message_type': 'direct'
        }

        result = processor.process_content(content_data)

        assert result['success'] is True
        assert result['processed'] is False
        assert 'not relevant' in result['reason'].lower()

    def test_process_content_error_handling(self, processor):
        """Test error handling in process_content."""
        # Create content that will pass filtering but fail during processing
        # by causing an exception in file writing
        content_data = {
            'sender_name': 'Test User',
            'company': 'Test Company',
            'body': 'Exciting job opportunity for Senior Developer',
            'timestamp': '2026-02-18T10:00:00Z',
            'message_type': 'direct'
        }

        # Make vault_path invalid to trigger error during save
        original_vault = processor.vault_path
        processor.vault_path = Path('/invalid/nonexistent/path/that/will/fail')

        result = processor.process_content(content_data)

        # Restore original path
        processor.vault_path = original_vault

        assert result['success'] is False
        assert result['processed'] is False
        assert 'error' in result


class TestSalaryFormatting:
    """Test salary formatting in summaries."""

    @pytest.fixture
    def processor(self):
        """Create LinkedIn processor."""
        vault_dir = tempfile.mkdtemp()
        processor = LinkedInProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_extract_single_salary_k_notation(self, processor):
        """Test extracting single salary with k notation."""
        content = "Salary: $130k annually"
        salary_info = processor.extract_salary_info(content)

        assert salary_info is not None
        assert salary_info['amount'] == 130000
        assert salary_info['currency'] == 'USD'

    def test_summary_with_single_salary(self, processor):
        """Test summary includes single salary amount."""
        parsed_data = {
            'sender_name': 'Recruiter',
            'company': 'Company',
            'body': 'Job available',
            'timestamp': '2026-02-18T10:00:00Z'
        }

        job_details = {
            'title': 'Developer',
            'location': 'Remote',
            'salary': {'amount': 130000, 'currency': 'USD'}
        }

        summary = processor.generate_opportunity_summary(parsed_data, job_details)

        assert '130,000' in summary or '$130k' in summary


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
