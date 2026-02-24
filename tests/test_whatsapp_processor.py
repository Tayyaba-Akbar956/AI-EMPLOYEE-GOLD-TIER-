"""Tests for WhatsApp processor - Phase 3 Silver Tier."""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from src.processors.whatsapp_processor import WhatsAppProcessor


class TestMessageParsing:
    """Test WhatsApp message parsing."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_parse_direct_message(self, processor):
        """Test parsing direct message."""
        message_data = {
            'from': '+1234567890',
            'name': 'John Doe',
            'body': 'Hello, this is a test message',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct',
            'has_media': False
        }

        result = processor.parse_message(message_data)

        assert result['sender_number'] == '+1234567890'
        assert result['sender_name'] == 'John Doe'
        assert result['body'] == 'Hello, this is a test message'
        assert result['chat_type'] == 'direct'
        assert result['has_media'] is False

    def test_parse_group_message(self, processor):
        """Test parsing group message."""
        message_data = {
            'from': '+1234567890',
            'name': 'Jane Smith',
            'body': '@me Please review this urgent invoice',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'group',
            'group_name': 'Project Team',
            'has_media': False
        }

        result = processor.parse_message(message_data)

        assert result['sender_name'] == 'Jane Smith'
        assert result['chat_type'] == 'group'
        assert result['group_name'] == 'Project Team'
        assert '@me' in result['body']

    def test_parse_message_with_media(self, processor):
        """Test parsing message with media."""
        message_data = {
            'from': '+1234567890',
            'name': 'Bob Wilson',
            'body': 'Here is the invoice',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct',
            'has_media': True,
            'media_type': 'image/jpeg',
            'media_filename': 'invoice.jpg'
        }

        result = processor.parse_message(message_data)

        assert result['has_media'] is True
        assert result['media_type'] == 'image/jpeg'
        assert result['media_filename'] == 'invoice.jpg'


class TestUrgencyDetection:
    """Test urgency detection."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_urgent_keyword_invoice(self, processor):
        """Test urgent detection for invoice keyword."""
        message = "Please review this invoice urgently"
        urgency = processor.detect_urgency(message)
        assert urgency == 'urgent'

    def test_urgent_keyword_asap(self, processor):
        """Test urgent detection for ASAP keyword."""
        message = "Need this ASAP please"
        urgency = processor.detect_urgency(message)
        assert urgency == 'urgent'

    def test_urgent_keyword_emergency(self, processor):
        """Test urgent detection for emergency keyword."""
        message = "This is an emergency situation"
        urgency = processor.detect_urgency(message)
        assert urgency == 'urgent'

    def test_urgent_keyword_payment(self, processor):
        """Test urgent detection for payment keyword."""
        message = "Payment is due today"
        urgency = processor.detect_urgency(message)
        assert urgency == 'urgent'

    def test_normal_message(self, processor):
        """Test normal priority for regular message."""
        message = "Hello, how are you doing today?"
        urgency = processor.detect_urgency(message)
        assert urgency == 'normal'

    def test_case_insensitive_urgency(self, processor):
        """Test urgency detection is case insensitive."""
        message = "URGENT: Please respond"
        urgency = processor.detect_urgency(message)
        assert urgency == 'urgent'


class TestMessageCategorization:
    """Test message categorization."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_categorize_invoice(self, processor):
        """Test invoice categorization."""
        message_data = {
            'body': 'Please find attached invoice for services',
            'has_media': True
        }
        category = processor.categorize_message(message_data)
        assert category == 'invoice'

    def test_categorize_receipt(self, processor):
        """Test receipt categorization."""
        message_data = {
            'body': 'Here is the receipt from the purchase',
            'has_media': False
        }
        category = processor.categorize_message(message_data)
        assert category == 'receipt'

    def test_categorize_contract(self, processor):
        """Test contract categorization."""
        message_data = {
            'body': 'Please review and sign this contract',
            'has_media': True
        }
        category = processor.categorize_message(message_data)
        assert category == 'contract'

    def test_categorize_general(self, processor):
        """Test general message categorization."""
        message_data = {
            'body': 'Just checking in on the project status',
            'has_media': False
        }
        category = processor.categorize_message(message_data)
        assert category == 'general'


class TestMarkdownGeneration:
    """Test markdown generation."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_markdown_has_header(self, processor):
        """Test markdown has proper header."""
        parsed_data = {
            'sender_name': 'John Doe',
            'sender_number': '+1234567890',
            'body': 'Test message',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct'
        }

        markdown = processor.generate_markdown(parsed_data, 'urgent', [])

        assert '# WhatsApp: Message from John Doe' in markdown
        assert 'John Doe' in markdown

    def test_markdown_includes_priority(self, processor):
        """Test markdown includes priority badge."""
        parsed_data = {
            'sender_name': 'Jane Smith',
            'sender_number': '+1234567890',
            'body': 'Urgent message',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct'
        }

        markdown = processor.generate_markdown(parsed_data, 'urgent', [])

        assert 'urgent' in markdown.lower() or '🔴' in markdown

    def test_markdown_includes_message_body(self, processor):
        """Test markdown includes message body."""
        parsed_data = {
            'sender_name': 'Bob Wilson',
            'sender_number': '+1234567890',
            'body': 'This is the message content',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct'
        }

        markdown = processor.generate_markdown(parsed_data, 'normal', [])

        assert 'This is the message content' in markdown

    def test_markdown_includes_group_info(self, processor):
        """Test markdown includes group information."""
        parsed_data = {
            'sender_name': 'Alice Brown',
            'sender_number': '+1234567890',
            'body': 'Group message',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'group',
            'group_name': 'Project Team'
        }

        markdown = processor.generate_markdown(parsed_data, 'normal', [])

        assert 'Project Team' in markdown
        assert 'group' in markdown.lower()

    def test_markdown_includes_attachments(self, processor):
        """Test markdown includes attachment links."""
        parsed_data = {
            'sender_name': 'Charlie Davis',
            'sender_number': '+1234567890',
            'body': 'See attached',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct'
        }

        media_files = ['invoice.pdf', 'receipt.jpg']
        markdown = processor.generate_markdown(parsed_data, 'normal', media_files)

        assert 'invoice.pdf' in markdown
        assert 'receipt.jpg' in markdown
        assert 'Attachments' in markdown or 'attachments' in markdown


class TestMessageFiltering:
    """Test message filtering logic."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_should_process_urgent_message(self, processor):
        """Test urgent messages should be processed."""
        message_data = {
            'body': 'URGENT: Please review invoice',
            'from': '+1234567890',
            'chat_type': 'direct'
        }

        should_process = processor.should_process_message(message_data)
        assert should_process is True

    def test_should_process_message_with_media(self, processor):
        """Test messages with media should be processed."""
        message_data = {
            'body': 'Here is the document',
            'from': '+1234567890',
            'chat_type': 'direct',
            'has_media': True
        }

        should_process = processor.should_process_message(message_data)
        assert should_process is True

    def test_should_skip_casual_message(self, processor):
        """Test casual messages should be skipped."""
        message_data = {
            'body': 'Hey, how are you?',
            'from': '+1234567890',
            'chat_type': 'direct',
            'has_media': False
        }

        should_process = processor.should_process_message(message_data)
        assert should_process is False

    def test_should_skip_group_without_mention(self, processor):
        """Test group messages without mention should be skipped."""
        message_data = {
            'body': 'General discussion in group',
            'from': '+1234567890',
            'chat_type': 'group',
            'mentioned': False
        }

        should_process = processor.should_process_message(message_data)
        assert should_process is False

    def test_should_process_group_with_mention(self, processor):
        """Test group messages with mention should be processed."""
        message_data = {
            'body': '@me Please review this',
            'from': '+1234567890',
            'chat_type': 'group',
            'mentioned': True
        }

        should_process = processor.should_process_message(message_data)
        assert should_process is True


class TestFileOperations:
    """Test file operations."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor with temp vault."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_save_markdown_creates_file(self, processor):
        """Test saving markdown creates file."""
        parsed_data = {
            'sender_name': 'Test User',
            'sender_number': '+1234567890',
            'body': 'Test message',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct'
        }

        markdown = processor.generate_markdown(parsed_data, 'normal', [])
        filepath = processor.save_markdown(markdown, parsed_data, 'normal')

        assert os.path.exists(filepath)
        assert filepath.endswith('.md')

    def test_save_markdown_correct_location(self, processor):
        """Test markdown saved to correct location based on urgency."""
        parsed_data = {
            'sender_name': 'Test User',
            'sender_number': '+1234567890',
            'body': 'Urgent message',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct'
        }

        markdown = processor.generate_markdown(parsed_data, 'urgent', [])
        filepath = processor.save_markdown(markdown, parsed_data, 'urgent')

        # Should be in Inbox/whatsapp for initial processing
        assert 'Inbox' in filepath or 'whatsapp' in filepath


class TestCompleteProcessing:
    """Test complete message processing."""

    @pytest.fixture
    def processor(self):
        """Create WhatsApp processor with temp vault."""
        vault_dir = tempfile.mkdtemp()
        processor = WhatsAppProcessor(vault_dir)
        yield processor
        shutil.rmtree(vault_dir)

    def test_process_urgent_message_complete(self, processor):
        """Test complete processing of urgent message."""
        message_data = {
            'from': '+1234567890',
            'name': 'John Doe',
            'body': 'URGENT: Please review this invoice immediately',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct',
            'has_media': False
        }

        result = processor.process_message(message_data)

        assert result['success'] is True
        assert result['processed'] is True
        assert result['urgency'] == 'urgent'
        assert result['category'] == 'invoice'
        assert 'filepath' in result
        assert os.path.exists(result['filepath'])

    def test_process_message_with_media(self, processor):
        """Test processing message with media attachments."""
        message_data = {
            'from': '+1234567890',
            'name': 'Jane Smith',
            'body': 'Here is the contract document',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct',
            'has_media': True,
            'media_type': 'application/pdf',
            'media_filename': 'contract.pdf',
            'media_files': ['contract.pdf']
        }

        result = processor.process_message(message_data)

        assert result['success'] is True
        assert result['processed'] is True
        assert result['category'] == 'contract'

    def test_process_casual_message_filtered(self, processor):
        """Test casual message is filtered out."""
        message_data = {
            'from': '+1234567890',
            'name': 'Bob Wilson',
            'body': 'Hey, how are you?',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'direct',
            'has_media': False
        }

        result = processor.process_message(message_data)

        assert result['success'] is True
        assert result['processed'] is False
        assert 'filtered' in result['reason'].lower()

    def test_process_group_message_with_mention(self, processor):
        """Test processing group message with mention."""
        message_data = {
            'from': '+1234567890',
            'name': 'Alice Brown',
            'body': '@me Please review the project proposal',
            'timestamp': '2026-02-18T10:00:00Z',
            'chat_type': 'group',
            'group_name': 'Project Team',
            'mentioned': True,
            'has_media': False
        }

        result = processor.process_message(message_data)

        assert result['success'] is True
        assert result['processed'] is True

    def test_process_message_error_handling(self, processor):
        """Test error handling in message processing."""
        # Invalid message data
        message_data = None

        result = processor.process_message(message_data)

        assert result['success'] is False
        assert result['processed'] is False
        assert 'error' in result

    def test_custom_config_urgent_keywords(self):
        """Test custom configuration for urgent keywords."""
        vault_dir = tempfile.mkdtemp()

        custom_config = {
            'urgent_keywords': ['critical', 'important', 'priority']
        }

        processor = WhatsAppProcessor(vault_dir, config=custom_config)

        message = "This is a critical issue"
        urgency = processor.detect_urgency(message)

        assert urgency == 'urgent'

        shutil.rmtree(vault_dir)

    def test_custom_config_business_keywords(self):
        """Test custom configuration for business keywords."""
        vault_dir = tempfile.mkdtemp()

        custom_config = {
            'business_keywords': ['deal', 'opportunity', 'client']
        }

        processor = WhatsAppProcessor(vault_dir, config=custom_config)

        message_data = {
            'body': 'New client opportunity available',
            'from': '+1234567890',
            'chat_type': 'direct',
            'has_media': False
        }

        should_process = processor.should_process_message(message_data)

        assert should_process is True

        shutil.rmtree(vault_dir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
