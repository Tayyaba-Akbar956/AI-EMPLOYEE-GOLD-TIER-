"""WhatsApp Processor for AI Employee Silver Tier.

Processes WhatsApp messages, detects urgency, categorizes content,
and generates structured markdown summaries.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WhatsAppProcessor:
    """Processes WhatsApp messages into structured vault entries.

    Handles message parsing, urgency detection, categorization,
    markdown generation, and file management.
    """

    def __init__(self, vault_path: str, config: Optional[Dict] = None):
        """Initialize WhatsApp processor.

        Args:
            vault_path: Path to AI_Employee_Vault
            config: Optional configuration overrides
        """
        self.vault_path = Path(vault_path)

        # Default configuration
        self.config = {
            'urgent_keywords': [
                'urgent', 'asap', 'emergency', 'immediately', 'critical',
                'invoice', 'payment', 'due', 'overdue', 'deadline'
            ],
            'business_keywords': [
                'invoice', 'receipt', 'contract', 'payment', 'proposal',
                'quote', 'order', 'delivery', 'meeting', 'project'
            ],
            'important_contacts': []  # Can be populated from config
        }

        if config:
            self.config.update(config)

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure required folders exist."""
        folders = [
            'Inbox/whatsapp',
            'Needs_Action/urgent',
            'Needs_Action/normal'
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    def parse_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse WhatsApp message data into structured format.

        Args:
            message_data: Raw message data from watcher

        Returns:
            Dictionary with parsed message details
        """
        parsed = {
            'sender_number': message_data.get('from', 'Unknown'),
            'sender_name': message_data.get('name', 'Unknown'),
            'body': message_data.get('body', ''),
            'timestamp': message_data.get('timestamp', datetime.now().isoformat()),
            'chat_type': message_data.get('chat_type', 'direct'),
            'has_media': message_data.get('has_media', False)
        }

        # Add group info if applicable
        if parsed['chat_type'] == 'group':
            parsed['group_name'] = message_data.get('group_name', 'Unknown Group')

        # Add media info if present
        if parsed['has_media']:
            parsed['media_type'] = message_data.get('media_type', 'unknown')
            parsed['media_filename'] = message_data.get('media_filename', 'media')

        return parsed

    def detect_urgency(self, message_body: str) -> str:
        """Detect urgency level from message content.

        Args:
            message_body: Message text content

        Returns:
            'urgent', 'normal', or 'low'
        """
        body_lower = message_body.lower()

        # Check for urgent keywords
        for keyword in self.config['urgent_keywords']:
            if keyword in body_lower:
                return 'urgent'

        return 'normal'

    def categorize_message(self, message_data: Dict[str, Any]) -> str:
        """Categorize message based on content.

        Args:
            message_data: Message data dictionary

        Returns:
            Category string (invoice, receipt, contract, general)
        """
        body = message_data.get('body', '').lower()

        # Check for specific categories
        if 'invoice' in body:
            return 'invoice'
        elif 'receipt' in body:
            return 'receipt'
        elif 'contract' in body or 'agreement' in body:
            return 'contract'
        else:
            return 'general'

    def generate_markdown(self, parsed_data: Dict[str, Any], urgency: str, media_files: List[str]) -> str:
        """Generate markdown summary for message.

        Args:
            parsed_data: Parsed message data
            urgency: Urgency level (urgent/normal/low)
            media_files: List of media file paths

        Returns:
            Markdown formatted string
        """
        # Priority badge
        priority_badge = {
            'urgent': '🔴 URGENT',
            'normal': '🟡 NORMAL',
            'low': '🔵 LOW'
        }.get(urgency, '🟡 NORMAL')

        # Build markdown
        markdown = f"# WhatsApp: Message from {parsed_data['sender_name']}\n\n"
        markdown += f"**Priority:** {priority_badge}\n"
        markdown += f"**From:** {parsed_data['sender_name']}\n"
        markdown += f"**Number:** {parsed_data['sender_number']}\n"
        markdown += f"**Date:** {parsed_data['timestamp']}\n"
        markdown += f"**Chat Type:** {parsed_data['chat_type'].title()}\n"

        # Add group info if applicable
        if parsed_data['chat_type'] == 'group':
            markdown += f"**Group:** {parsed_data.get('group_name', 'Unknown')}\n"

        markdown += "\n---\n\n"
        markdown += "## Message\n\n"
        markdown += f"{parsed_data['body']}\n\n"

        # Add attachments section if media present
        if media_files:
            markdown += "## Attachments\n\n"
            for media_file in media_files:
                filename = os.path.basename(media_file)
                markdown += f"- [{filename}]({filename})\n"
            markdown += "\n"

        # Add action items section
        markdown += "## Action Items\n\n"
        markdown += "- [ ] Review message\n"
        markdown += "- [ ] Respond if needed\n"
        markdown += "- [ ] Archive when complete\n\n"

        # Add metadata
        markdown += "---\n\n"
        markdown += f"*Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        markdown += "*Source: WhatsApp*\n"

        return markdown

    def should_process_message(self, message_data: Dict[str, Any]) -> bool:
        """Determine if message should be processed.

        Args:
            message_data: Message data dictionary

        Returns:
            True if message should be processed, False otherwise
        """
        body = message_data.get('body', '').lower()
        chat_type = message_data.get('chat_type', 'direct')
        has_media = message_data.get('has_media', False)

        # Always process if has media
        if has_media:
            return True

        # Check for urgent keywords
        for keyword in self.config['urgent_keywords']:
            if keyword in body:
                return True

        # Check for business keywords
        for keyword in self.config['business_keywords']:
            if keyword in body:
                return True

        # For group messages, only process if mentioned
        if chat_type == 'group':
            mentioned = message_data.get('mentioned', False)
            if not mentioned:
                return False
            # If mentioned, process
            return True

        # Skip casual messages (short, no keywords)
        if len(body) < 20 and not has_media:
            casual_phrases = ['hey', 'hi', 'hello', 'how are you', 'thanks', 'ok', 'yes', 'no']
            if any(phrase in body for phrase in casual_phrases):
                return False

        # Default: don't process casual messages
        return False

    def save_markdown(self, markdown: str, parsed_data: Dict[str, Any], urgency: str) -> str:
        """Save markdown to appropriate location.

        Args:
            markdown: Markdown content
            parsed_data: Parsed message data
            urgency: Urgency level

        Returns:
            Path to saved file
        """
        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        sender_name = parsed_data['sender_name'].replace(' ', '-').replace('/', '-')
        # Remove special characters
        sender_name = ''.join(c for c in sender_name if c.isalnum() or c == '-')
        filename = f"{timestamp}_whatsapp_{sender_name}.md"

        # Save to Inbox/whatsapp initially
        inbox_path = self.vault_path / 'Inbox' / 'whatsapp'
        filepath = inbox_path / filename

        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

        logger.info(f"Saved WhatsApp message to {filepath}")

        return str(filepath)

    def process_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process complete WhatsApp message.

        Args:
            message_data: Raw message data from watcher

        Returns:
            Dictionary with processing results
        """
        try:
            # Check if should process
            if not self.should_process_message(message_data):
                return {
                    'success': True,
                    'processed': False,
                    'reason': 'Message filtered out (casual/non-business)'
                }

            # Parse message
            parsed_data = self.parse_message(message_data)

            # Detect urgency
            urgency = self.detect_urgency(parsed_data['body'])

            # Categorize
            category = self.categorize_message(message_data)

            # Generate markdown
            media_files = message_data.get('media_files', [])
            markdown = self.generate_markdown(parsed_data, urgency, media_files)

            # Save markdown
            filepath = self.save_markdown(markdown, parsed_data, urgency)

            return {
                'success': True,
                'processed': True,
                'filepath': filepath,
                'urgency': urgency,
                'category': category,
                'sender': parsed_data['sender_name']
            }

        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}")
            return {
                'success': False,
                'processed': False,
                'error': str(e)
            }
