"""Gmail Watcher - Monitor Gmail inbox and organize emails into vault"""
import os
import base64
import re
from datetime import datetime
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"Google API libraries not installed: {e}")
    print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    raise

# Import vault management
try:
    from src.utils.vault_management import write_log, write_vault_file
    from src.utils.dashboard_updater import log_and_update
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.utils.vault_management import write_log, write_vault_file
    from src.utils.dashboard_updater import log_and_update


# Gmail API scope - read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service():
    """
    Authenticate and return Gmail API service.

    Returns:
        Gmail API service object
    """
    creds = None
    token_path = Path('token.json')
    credentials_path = Path('credentials.json')

    # Check for credentials file
    if not credentials_path.exists():
        print("❌ credentials.json not found!")
        print("\nTo set up Gmail API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select existing")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download JSON and save as 'credentials.json' in project root")
        print("\nSee: https://developers.google.com/gmail/api/quickstart/python")
        return None

    # Load existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def extract_email_body(payload):
    """Extract text body from email payload"""
    body = ""

    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
            elif part['mimeType'] == 'text/html' and not body:
                if 'data' in part['body']:
                    data = part['body']['data']
                    html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    # Simple HTML to text conversion
                    body = re.sub(r'<[^>]+>', ' ', html)
                    body = re.sub(r'\s+', ' ', body).strip()
    elif 'body' in payload and 'data' in payload['body']:
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    return body[:2000]  # Limit body length


def parse_email_headers(headers):
    """Extract key headers from email"""
    result = {}
    for header in headers:
        name = header['name'].lower()
        if name == 'from':
            result['from'] = header['value']
        elif name == 'to':
            result['to'] = header['value']
        elif name == 'subject':
            result['subject'] = header['value']
        elif name == 'date':
            result['date'] = header['value']
        elif name == 'cc':
            result['cc'] = header['value']
    return result


def categorize_email(headers, body, subject):
    """
    Categorize email based on content and patterns.

    Returns:
        Dictionary with priority and destination
    """
    text = f"{subject} {body}".lower()
    sender = headers.get('from', '').lower()

    # Check if LinkedIn email
    if 'linkedin.com' in sender:
        return categorize_linkedin_email(subject, sender, body)

    # Urgent patterns
    urgent_patterns = [
        'urgent', 'asap', 'immediate', 'action required',
        'deadline', 'overdue', 'payment due', 'invoice',
        'suspended', 'terminate', 'legal', 'lawsuit',
        'security alert', 'breach', 'unauthorized'
    ]

    # High priority senders
    urgent_senders = [
        'bank', 'paypal', 'stripe', 'irs', 'gov',
        'amazon', 'aws', 'azure', 'legal', 'attorney'
    ]

    # Check for urgent keywords
    if any(pattern in text for pattern in urgent_patterns):
        return {
            'category': 'urgent',
            'priority': 'urgent',
            'destination': 'Needs_Action/urgent/',
            'reason': 'Contains urgent keywords'
        }

    # Check sender
    if any(sender_type in sender for sender_type in urgent_senders):
        return {
            'category': 'financial',
            'priority': 'urgent',
            'destination': 'Needs_Action/urgent/',
            'reason': 'High priority sender'
        }

    # Newsletter/promotional patterns
    promo_patterns = ['unsubscribe', 'promotional', 'marketing', 'newsletter', 'no-reply']
    if any(pattern in text for pattern in promo_patterns):
        return {
            'category': 'promotional',
            'priority': 'low',
            'destination': 'Done/',
            'reason': 'Promotional email'
        }

    # Default
    return {
        'category': 'general',
        'priority': 'normal',
        'destination': 'Needs_Action/normal/',
        'reason': 'Standard email'
    }


def categorize_linkedin_email(subject, sender, body):
    """
    Categorize LinkedIn notification emails.

    Returns:
        Dictionary with priority and destination
    """
    subject_lower = subject.lower()

    # Skip promotional/digest emails
    skip_keywords = [
        'weekly digest', 'daily rundown', 'news', 'trending',
        'people you may know', 'jobs you might be interested',
        'update your profile', 'complete your profile',
        'recommendations'
    ]

    if any(kw in subject_lower for kw in skip_keywords):
        return {
            'category': 'linkedin_promotional',
            'priority': 'low',
            'destination': 'Done/',
            'reason': 'LinkedIn promotional email',
            'is_linkedin': False
        }

    # Important LinkedIn notifications
    if 'message' in subject_lower or 'sent you a message' in subject_lower:
        return {
            'category': 'linkedin_message',
            'priority': 'urgent',
            'destination': 'Inbox/linkedin/',
            'reason': 'LinkedIn direct message',
            'is_linkedin': True
        }

    if 'job' in subject_lower or 'opportunity' in subject_lower:
        return {
            'category': 'linkedin_job',
            'priority': 'urgent',
            'destination': 'Inbox/linkedin/',
            'reason': 'LinkedIn job opportunity',
            'is_linkedin': True
        }

    if 'connection request' in subject_lower or 'wants to connect' in subject_lower:
        return {
            'category': 'linkedin_connection',
            'priority': 'normal',
            'destination': 'Inbox/linkedin/',
            'reason': 'LinkedIn connection request',
            'is_linkedin': True
        }

    if 'mentioned you' in subject_lower or 'tagged you' in subject_lower:
        return {
            'category': 'linkedin_mention',
            'priority': 'urgent',
            'destination': 'Inbox/linkedin/',
            'reason': 'LinkedIn mention',
            'is_linkedin': True
        }

    if 'invitation' in subject_lower or 'invite' in subject_lower:
        return {
            'category': 'linkedin_invitation',
            'priority': 'normal',
            'destination': 'Inbox/linkedin/',
            'reason': 'LinkedIn invitation',
            'is_linkedin': True
        }

    # Default LinkedIn notification
    return {
        'category': 'linkedin_notification',
        'priority': 'normal',
        'destination': 'Inbox/linkedin/',
        'reason': 'LinkedIn notification',
        'is_linkedin': True
    }


def generate_safe_filename(date_str, subject, sender):
    """Generate safe filename from email data"""
    # Parse date
    try:
        date = datetime.strptime(date_str[:16], '%a, %d %b %Y')
        date_prefix = date.strftime('%Y-%m-%d')
    except:
        date_prefix = datetime.now().strftime('%Y-%m-%d')

    # Clean subject
    clean_subject = re.sub(r'[^\w\s-]', '', subject or 'No Subject')
    clean_subject = re.sub(r'[-\s]+', '-', clean_subject)[:40].strip('-')

    # Clean sender
    clean_sender = re.sub(r'[^\w\s-]', '', sender.split('<')[0].strip())[:20].strip()

    return f"{date_prefix}_email_{clean_sender}_{clean_subject}.md"


def generate_email_markdown(msg_data, headers, body, category):
    """Generate markdown summary of email"""
    timestamp = datetime.now().isoformat()
    subject = headers.get('subject', 'No Subject')
    sender = headers.get('from', 'Unknown')
    date = headers.get('date', 'Unknown')
    to = headers.get('to', '')
    cc = headers.get('cc', '')

    # If LinkedIn email, generate LinkedIn-specific markdown
    if category.get('is_linkedin', False):
        return generate_linkedin_markdown(subject, sender, body, category, timestamp)

    # Generate action items
    actions = ["- [ ] Review email content"]
    if category['priority'] == 'urgent':
        actions.extend([
            "- [ ] Respond within 24 hours",
            "- [ ] Take immediate action if required"
        ])
    elif category['category'] == 'financial':
        actions.extend([
            "- [ ] Review financial details",
            "- [ ] Update records if needed"
        ])
    else:
        actions.append("- [ ] Archive when complete")

    markdown = f"""# Email: {subject}

**From:** {sender}
**To:** {to}
**Date:** {date}
**Priority:** {category['priority'].upper()}

## Classification
- **Category:** {category['category']}
- **Destination:** {category['destination']}
- **Reason:** {category['reason']}

## Content Preview

### Subject
{subject}

### Body
```
{body[:1000]}
```

## Actions Needed
{chr(10).join(actions)}

## Metadata
- **Email ID:** {msg_data.get('id', 'N/A')}
- **Thread ID:** {msg_data.get('threadId', 'N/A')}
- **Processed:** {timestamp}

---
*Processed by email-processor at {timestamp}*
"""
    return markdown


def generate_linkedin_markdown(subject, sender, body, category, timestamp):
    """Generate LinkedIn-specific markdown"""
    # Extract sender name from subject
    sender_name = "LinkedIn User"
    if 'message' in subject.lower():
        match = re.search(r'^(.+?)\s+sent you a message', subject, re.IGNORECASE)
        if match:
            sender_name = match.group(1)
    elif 'connection' in subject.lower():
        match = re.search(r'^(.+?)\s+(?:wants to connect|sent you a connection)', subject, re.IGNORECASE)
        if match:
            sender_name = match.group(1)
    elif 'mentioned' in subject.lower():
        match = re.search(r'^(.+?)\s+mentioned you', subject, re.IGNORECASE)
        if match:
            sender_name = match.group(1)

    # Extract LinkedIn URL
    action_url = None
    url_match = re.search(r'https://www\.linkedin\.com/[^\s<>"]+', body)
    if url_match:
        action_url = url_match.group(0)

    # Clean body preview
    clean_body = re.sub(r'<[^>]+>', '', body)
    clean_body = re.sub(r'This email was intended for.*', '', clean_body)
    clean_body = re.sub(r'You\'re receiving.*', '', clean_body)
    clean_body = clean_body.strip()[:500]

    # Generate actions based on type
    actions = []
    if category['category'] == 'linkedin_message':
        actions = [
            "- [ ] Read full message on LinkedIn",
            "- [ ] Respond if needed",
            "- [ ] Archive when complete"
        ]
    elif category['category'] == 'linkedin_job':
        actions = [
            "- [ ] Review job details",
            "- [ ] Check if interested",
            "- [ ] Apply if suitable",
            "- [ ] Archive when complete"
        ]
    elif category['category'] == 'linkedin_connection':
        actions = [
            "- [ ] Review profile",
            "- [ ] Accept or decline",
            "- [ ] Archive when complete"
        ]
    elif category['category'] == 'linkedin_mention':
        actions = [
            "- [ ] View post/comment",
            "- [ ] Respond if appropriate",
            "- [ ] Archive when complete"
        ]
    else:
        actions = [
            "- [ ] Review notification",
            "- [ ] Take action if needed",
            "- [ ] Archive when complete"
        ]

    markdown = f"""# LinkedIn: {category['category'].replace('linkedin_', '').replace('_', ' ').title()}

**Type:** {category['category']}
**Priority:** {category['priority'].upper()}
**Date:** {timestamp}
**From:** {sender_name}

## Subject

{subject}

## Preview

{clean_body}
"""

    if action_url:
        markdown += f"\n## Action Required\n\n[View on LinkedIn]({action_url})\n"

    markdown += f"""
## Actions Needed

{chr(10).join(actions)}

---
*Processed by linkedin-processor (email-based) at {timestamp}*
"""
    return markdown


def process_new_emails(service, max_results=10):
    """
    Fetch and process new unread emails.

    Args:
        service: Gmail API service
        max_results: Maximum emails to process

    Returns:
        List of processed email IDs
    """
    processed = []

    try:
        # Get unread messages
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print("📭 No new unread emails")
            return processed

        print(f"📧 Found {len(messages)} unread email(s)")

        for msg in messages:
            msg_id = msg['id']

            # Get full message details
            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            # Extract data
            payload = message['payload']
            headers = parse_email_headers(payload.get('headers', []))
            body = extract_email_body(payload)
            subject = headers.get('subject', 'No Subject')

            print(f"  Processing: {subject[:50]}...")

            # Categorize
            category = categorize_email(headers, body, subject)

            # Generate markdown
            markdown = generate_email_markdown(message, headers, body, category)

            # Save to vault
            vault_path = Path("AI_Employee_Vault")
            dest_dir = vault_path / category['destination']
            dest_dir.mkdir(parents=True, exist_ok=True)

            filename = generate_safe_filename(
                headers.get('date', ''),
                subject,
                headers.get('from', '')
            )

            markdown_path = dest_dir / filename
            markdown_path.write_text(markdown, encoding='utf-8')

            # Log
            write_log('INFO', 'EmailProcessor',
                      f"Processed email: {subject[:40]} -> {category['destination']}")

            processed.append({
                'id': msg_id,
                'subject': subject,
                'destination': str(category['destination']),
                'priority': category['priority']
            })

            print(f"    ✅ Saved to: {category['destination']}")

        return processed

    except Exception as e:
        print(f"❌ Error processing emails: {e}")
        write_log('ERROR', 'EmailProcessor', f"Failed to process emails: {e}")
        return processed


def start_email_watcher(check_interval=60):
    """
    Start watching Gmail for new emails.

    Args:
        check_interval: Seconds between checks (default: 60)
    """
    print("📧 Gmail Watcher Starting...")
    print("=" * 50)

    # Authenticate
    service = get_gmail_service()
    if not service:
        return

    # Get profile info
    try:
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Connected to: {profile.get('emailAddress', 'Unknown')}")
        print(f"⏱️  Checking every {check_interval} seconds")
        print("=" * 50)
    except Exception as e:
        print(f"⚠️ Could not get profile: {e}")

    # Main loop
    import time
    try:
        while True:
            processed = process_new_emails(service)

            if processed:
                print(f"\n📊 Processed {len(processed)} email(s)")
                for email in processed:
                    print(f"   - {email['subject'][:40]}... [{email['priority']}]")

            print(f"\n⏳ Next check in {check_interval} seconds...")
            print("(Press Ctrl+C to stop)\n")
            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n⏸️  Email watcher stopped")


def run_once():
    """Run email check once (for testing/cron)"""
    print("📧 Gmail Processor - Single Run")
    print("=" * 50)

    service = get_gmail_service()
    if not service:
        return

    processed = process_new_emails(service)

    if processed:
        print(f"\n✅ Processed {len(processed)} email(s)")
    else:
        print("\n📭 No new emails")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        run_once()
    else:
        start_email_watcher()
