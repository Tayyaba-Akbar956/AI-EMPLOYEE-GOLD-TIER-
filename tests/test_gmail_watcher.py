"""Phase 3: Gmail Watcher Tests"""
from pathlib import Path
import pytest
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


def test_gmail_watcher_module_exists():
    """Gmail watcher module must exist"""
    watcher_path = Path('src/watchers/gmail_watcher.py')
    assert watcher_path.exists(), "gmail_watcher.py not found"


def test_extract_email_body_plain_text():
    """Extract plain text body from email payload"""
    from src.watchers.gmail_watcher import extract_email_body

    # Mock plain text payload
    payload = {
        'body': {
            'data': 'SGVsbG8gV29ybGQh'  # base64 of "Hello World!"
        }
    }

    result = extract_email_body(payload)
    assert 'Hello World!' in result


def test_extract_email_body_html():
    """Extract and convert HTML body from email payload"""
    from src.watchers.gmail_watcher import extract_email_body

    # Mock HTML payload with parts
    import base64
    html_content = '<html><body><p>Hello World!</p></body></html>'
    encoded = base64.urlsafe_b64encode(html_content.encode()).decode()

    payload = {
        'parts': [
            {
                'mimeType': 'text/html',
                'body': {'data': encoded}
            }
        ]
    }

    result = extract_email_body(payload)
    assert 'Hello World!' in result
    assert '<html>' not in result  # HTML tags should be stripped


def test_extract_email_body_multipart():
    """Extract body from multipart email"""
    from src.watchers.gmail_watcher import extract_email_body
    import base64

    text_content = 'Plain text content'
    encoded = base64.urlsafe_b64encode(text_content.encode()).decode()

    payload = {
        'parts': [
            {
                'mimeType': 'text/plain',
                'body': {'data': encoded}
            },
            {
                'mimeType': 'text/html',
                'body': {'data': encoded}
            }
        ]
    }

    result = extract_email_body(payload)
    assert 'Plain text content' in result


def test_parse_email_headers():
    """Parse email headers correctly"""
    from src.watchers.gmail_watcher import parse_email_headers

    headers = [
        {'name': 'From', 'value': 'sender@example.com'},
        {'name': 'To', 'value': 'recipient@example.com'},
        {'name': 'Subject', 'value': 'Test Subject'},
        {'name': 'Date', 'value': 'Mon, 15 Feb 2026 10:30:00 GMT'},
        {'name': 'Cc', 'value': 'cc@example.com'}
    ]

    result = parse_email_headers(headers)

    assert result['from'] == 'sender@example.com'
    assert result['to'] == 'recipient@example.com'
    assert result['subject'] == 'Test Subject'
    assert result['date'] == 'Mon, 15 Feb 2026 10:30:00 GMT'
    assert result['cc'] == 'cc@example.com'


def test_parse_email_headers_partial():
    """Parse headers with missing fields"""
    from src.watchers.gmail_watcher import parse_email_headers

    headers = [
        {'name': 'From', 'value': 'sender@example.com'},
        {'name': 'Subject', 'value': 'Test Subject'}
    ]

    result = parse_email_headers(headers)

    assert result['from'] == 'sender@example.com'
    assert result['subject'] == 'Test Subject'
    assert 'to' not in result
    assert 'date' not in result


def test_categorize_email_urgent_keywords():
    """Categorize email with urgent keywords"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'test@example.com'}
    body = 'This is an urgent matter that requires immediate action'
    subject = 'Urgent: Action Required'

    result = categorize_email(headers, body, subject)

    assert result['category'] == 'urgent'
    assert result['priority'] == 'urgent'
    assert 'Needs_Action/urgent/' in result['destination']
    assert 'urgent keywords' in result['reason'].lower()


def test_categorize_email_financial_sender():
    """Categorize email from financial institution"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'notifications@paypal.com'}
    body = 'Your payment has been processed'
    subject = 'Payment Confirmation'

    result = categorize_email(headers, body, subject)

    assert result['category'] == 'financial'
    assert result['priority'] == 'urgent'
    assert 'Needs_Action/urgent/' in result['destination']
    assert 'High priority sender' in result['reason']


def test_categorize_email_promotional():
    """Categorize promotional/marketing email"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'marketing@shop.com'}
    body = 'Click here to unsubscribe from our newsletter'
    subject = 'Special Offer!'

    result = categorize_email(headers, body, subject)

    assert result['category'] == 'promotional'
    assert result['priority'] == 'low'
    assert 'Done/' in result['destination']
    assert 'Promotional' in result['reason']


def test_categorize_email_general():
    """Categorize regular general email"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'friend@example.com'}
    body = 'Hey, just wanted to catch up'
    subject = 'Hello!'

    result = categorize_email(headers, body, subject)

    assert result['category'] == 'general'
    assert result['priority'] == 'normal'
    assert 'Needs_Action/normal/' in result['destination']
    assert 'Standard' in result['reason']


def test_generate_safe_filename():
    """Generate safe filename from email data"""
    from src.watchers.gmail_watcher import generate_safe_filename

    date_str = 'Mon, 15 Feb 2026 10:30:00 GMT'
    subject = 'RE: Important Meeting Notes'
    sender = 'John Doe <john@example.com>'

    result = generate_safe_filename(date_str, subject, sender)

    # Should start with date
    assert result.startswith('2026-02-15')
    # Should contain email indicator
    assert 'email' in result
    # Should end with .md
    assert result.endswith('.md')
    # Should not have special characters
    assert ':' not in result
    assert '<' not in result
    assert '>' not in result


def test_generate_safe_filename_no_subject():
    """Generate filename when subject is empty"""
    from src.watchers.gmail_watcher import generate_safe_filename

    date_str = 'Mon, 15 Feb 2026 10:30:00 GMT'
    subject = None
    sender = 'Test User'

    result = generate_safe_filename(date_str, subject, sender)

    assert 'No-Subject' in result or 'email' in result
    assert result.endswith('.md')


def test_generate_email_markdown():
    """Generate markdown content for email"""
    from src.watchers.gmail_watcher import generate_email_markdown

    msg_data = {'id': '12345', 'threadId': 'thread123'}
    headers = {
        'from': 'sender@example.com',
        'to': 'recipient@example.com',
        'subject': 'Test Email',
        'date': 'Mon, 15 Feb 2026 10:30:00 GMT'
    }
    body = 'This is the email body content'
    category = {
        'category': 'general',
        'priority': 'normal',
        'destination': 'Needs_Action/normal/',
        'reason': 'Standard email'
    }

    result = generate_email_markdown(msg_data, headers, body, category)

    # Check all required sections
    assert '# Email: Test Email' in result
    assert '**From:** sender@example.com' in result
    assert '**To:** recipient@example.com' in result
    assert '**Priority:** NORMAL' in result
    assert '**Category:** general' in result
    assert '## Content Preview' in result
    assert 'This is the email body content' in result
    assert '## Actions Needed' in result
    assert '- [ ]' in result  # Checkboxes
    assert '**Email ID:** 12345' in result
    assert '**Thread ID:** thread123' in result
    assert '## Metadata' in result


def test_generate_email_markdown_urgent():
    """Generate markdown for urgent email with special actions"""
    from src.watchers.gmail_watcher import generate_email_markdown

    msg_data = {'id': '12345', 'threadId': 'thread123'}
    headers = {
        'from': 'bank@example.com',
        'to': 'recipient@example.com',
        'subject': 'Urgent: Account Alert',
        'date': 'Mon, 15 Feb 2026 10:30:00 GMT'
    }
    body = 'Your account requires immediate attention'
    category = {
        'category': 'urgent',
        'priority': 'urgent',
        'destination': 'Needs_Action/urgent/',
        'reason': 'Urgent keywords'
    }

    result = generate_email_markdown(msg_data, headers, body, category)

    assert '**Priority:** URGENT' in result
    assert '- [ ] Respond within 24 hours' in result
    assert '- [ ] Take immediate action if required' in result


def test_generate_email_markdown_financial():
    """Generate markdown for financial email (urgent priority)"""
    from src.watchers.gmail_watcher import generate_email_markdown

    msg_data = {'id': '12345', 'threadId': 'thread123'}
    headers = {
        'from': 'paypal@example.com',
        'to': 'recipient@example.com',
        'subject': 'Payment Received',
        'date': 'Mon, 15 Feb 2026 10:30:00 GMT'
    }
    body = 'You received a payment of $100'
    category = {
        'category': 'financial',
        'priority': 'urgent',  # Financial emails marked as urgent get urgent actions
        'destination': 'Needs_Action/urgent/',
        'reason': 'High priority sender'
    }

    result = generate_email_markdown(msg_data, headers, body, category)

    assert '**Category:** financial' in result
    # Financial emails with urgent priority get urgent action items
    assert '- [ ] Respond within 24 hours' in result
    assert '- [ ] Take immediate action if required' in result


def test_process_new_emails_no_messages():
    """Process emails when inbox is empty"""
    from src.watchers.gmail_watcher import process_new_emails

    # Mock service with no messages
    mock_service = Mock()
    mock_service.users().messages().list.return_value.execute.return_value = {'messages': []}

    result = process_new_emails(mock_service)

    assert result == []
    # Verify the API was called with correct parameters
    mock_service.users().messages().list.assert_called_with(
        userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=10
    )


@patch('src.watchers.gmail_watcher.get_gmail_service')
def test_process_new_emails_with_messages(mock_get_service, tmp_path):
    """Process new unread emails"""
    from src.watchers.gmail_watcher import process_new_emails
    import base64

    # Create mock message
    mock_service = Mock()

    # Mock list response
    mock_service.users().messages().list().execute.return_value = {
        'messages': [{'id': 'msg123'}]
    }

    # Mock get response
    body_content = 'Test email body content'
    encoded_body = base64.urlsafe_b64encode(body_content.encode()).decode()

    mock_service.users().messages().get().execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'test@example.com'},
                {'name': 'To', 'value': 'me@example.com'},
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'Date', 'value': 'Mon, 15 Feb 2026 10:30:00 GMT'}
            ],
            'body': {
                'data': encoded_body
            }
        }
    }

    result = process_new_emails(mock_service)

    assert len(result) == 1
    assert result[0]['id'] == 'msg123'
    assert result[0]['subject'] == 'Test Subject'


def test_categorize_email_security_alert():
    """Categorize security alert emails as urgent"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'security@example.com'}
    body = 'We detected unauthorized access to your account'
    subject = 'Security Alert: Suspicious Activity'

    result = categorize_email(headers, body, subject)

    assert result['priority'] == 'urgent'
    assert result['category'] == 'urgent'


def test_categorize_email_invoice():
    """Categorize invoice emails as urgent"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'billing@company.com'}
    body = 'Your invoice is attached. Payment due date: tomorrow'
    subject = 'Invoice #12345 - Payment Due'

    result = categorize_email(headers, body, subject)

    assert result['priority'] == 'urgent'
    assert 'invoice' in result['reason'].lower() or 'urgent' in result['category']


def test_categorize_email_deadline():
    """Categorize deadline emails as urgent"""
    from src.watchers.gmail_watcher import categorize_email

    headers = {'from': 'project@example.com'}
    body = 'The deadline for this project is approaching'
    subject = 'Project Deadline Tomorrow'

    result = categorize_email(headers, body, subject)

    assert result['priority'] == 'urgent'


def test_generate_safe_filename_long_subject():
    """Truncate long subjects in filename"""
    from src.watchers.gmail_watcher import generate_safe_filename

    date_str = 'Mon, 15 Feb 2026 10:30:00 GMT'
    subject = 'A' * 100  # Very long subject
    sender = 'Test'

    result = generate_safe_filename(date_str, subject, sender)

    # Filename should be reasonable length
    assert len(result) < 100
    assert result.endswith('.md')


def test_generate_safe_filename_special_chars():
    """Handle special characters in subject and sender"""
    from src.watchers.gmail_watcher import generate_safe_filename

    date_str = 'Mon, 15 Feb 2026 10:30:00 GMT'
    subject = 'RE: Fwd: Important!!! [Action Required]'
    sender = 'User Name (Company) <user@example.com>'

    result = generate_safe_filename(date_str, subject, sender)

    # Should not contain special characters
    assert '[' not in result
    assert ']' not in result
    assert '!' not in result
    assert '@' not in result
    assert '(' not in result
    assert ')' not in result
    assert '<' not in result
    assert '>' not in result


def test_body_length_limit():
    """Body should be limited to 2000 characters"""
    from src.watchers.gmail_watcher import extract_email_body
    import base64

    long_content = 'A' * 5000
    encoded = base64.urlsafe_b64encode(long_content.encode()).decode()

    payload = {
        'body': {
            'data': encoded
        }
    }

    result = extract_email_body(payload)

    assert len(result) <= 2000
