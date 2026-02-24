"""LinkedIn Processor for AI Employee Silver Tier.

Processes LinkedIn messages, detects job opportunities, extracts salary/location,
and generates structured opportunity summaries.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LinkedInProcessor:
    """Processes LinkedIn content into structured vault entries.

    Handles job opportunity detection, salary extraction, location parsing,
    and opportunity summary generation.
    """

    def __init__(self, vault_path: str, config: Optional[Dict] = None):
        """Initialize LinkedIn processor.

        Args:
            vault_path: Path to AI_Employee_Vault
            config: Optional configuration overrides
        """
        self.vault_path = Path(vault_path)

        # Default configuration
        self.config = {
            'job_keywords': [
                'opportunity', 'position', 'role', 'job', 'opening',
                'hire', 'hiring', 'recruit', 'candidate'
            ],
            'networking_keywords': [
                'connect', 'network', 'collaboration', 'partnership'
            ],
            'business_keywords': [
                'partnership', 'business', 'inquiry', 'proposal', 'deal'
            ],
            'spam_keywords': [
                'webinar', 'course', 'training', 'promotion', 'discount'
            ],
            'minimum_salary': 0
        }

        if config:
            self.config.update(config)

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure required folders exist."""
        folders = [
            'Inbox/linkedin',
            'Needs_Action/urgent',
            'Needs_Action/normal'
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    def parse_linkedin_content(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LinkedIn content into structured format.

        Args:
            message_data: Raw message data from watcher

        Returns:
            Dictionary with parsed content details
        """
        parsed = {
            'sender_name': message_data.get('sender_name', 'Unknown'),
            'sender_profile': message_data.get('sender_profile', ''),
            'company': message_data.get('company', 'Unknown'),
            'body': message_data.get('body', ''),
            'timestamp': message_data.get('timestamp', datetime.now().isoformat()),
            'message_type': message_data.get('message_type', 'direct')
        }

        return parsed

    def identify_job_opportunity(self, content: str) -> bool:
        """Detect if content is a job opportunity.

        Args:
            content: Message text content

        Returns:
            True if job-related, False otherwise
        """
        content_lower = content.lower()

        # Check for job keywords
        for keyword in self.config['job_keywords']:
            if keyword in content_lower:
                return True

        return False

    def extract_salary_info(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract salary information from content.

        Args:
            content: Message text content

        Returns:
            Dictionary with salary details or None
        """
        # Pattern for salary range: $120,000 - $150,000 or $120k - $150k
        range_pattern = r'\$(\d{1,3}(?:,\d{3})*|\d+)k?\s*-\s*\$?(\d{1,3}(?:,\d{3})*|\d+)k?'
        range_match = re.search(range_pattern, content, re.IGNORECASE)

        if range_match:
            min_val = range_match.group(1).replace(',', '')
            max_val = range_match.group(2).replace(',', '')

            # Handle 'k' notation
            if 'k' in range_match.group(0).lower():
                min_val = int(min_val) * 1000
                max_val = int(max_val) * 1000
            else:
                min_val = int(min_val)
                max_val = int(max_val)

            return {
                'min': min_val,
                'max': max_val,
                'currency': 'USD'
            }

        # Pattern for single salary: $120,000 or $120k
        single_pattern = r'\$(\d{1,3}(?:,\d{3})*|\d+)k?'
        single_match = re.search(single_pattern, content, re.IGNORECASE)

        if single_match:
            amount = single_match.group(1).replace(',', '')

            # Handle 'k' notation
            if 'k' in single_match.group(0).lower():
                amount = int(amount) * 1000
            else:
                amount = int(amount)

            return {
                'amount': amount,
                'currency': 'USD'
            }

        return None

    def extract_job_details(self, content: str) -> Dict[str, Any]:
        """Extract job details from content.

        Args:
            content: Message text content

        Returns:
            Dictionary with job details
        """
        details = {
            'title': '',
            'location': '',
            'salary': None
        }

        # Extract location
        content_lower = content.lower()

        # Check for hybrid first (more specific)
        if 'hybrid' in content_lower:
            details['location'] = 'Hybrid'
        elif 'remote' in content_lower:
            details['location'] = 'Remote'
        else:
            # Try to find city names (simple pattern)
            city_pattern = r'(?:in|based in|located in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z]{2})?)'
            city_match = re.search(city_pattern, content)
            if city_match:
                details['location'] = city_match.group(1)
            else:
                details['location'] = 'Not specified'

        # Extract job title (look for common patterns)
        title_patterns = [
            r'(Senior|Junior|Lead|Staff|Principal)?\s*(Software|Full Stack|Backend|Frontend|DevOps)?\s*(Engineer|Developer|Architect)',
            r'(Senior|Junior|Lead)?\s*(Product|Project|Engineering)\s*Manager',
            r'(Senior|Junior)?\s*Developer'
        ]

        for pattern in title_patterns:
            title_match = re.search(pattern, content, re.IGNORECASE)
            if title_match:
                details['title'] = title_match.group(0)
                break

        if not details['title']:
            details['title'] = 'Position'

        # Extract salary
        details['salary'] = self.extract_salary_info(content)

        return details

    def generate_opportunity_summary(self, parsed_data: Dict[str, Any], job_details: Dict[str, Any]) -> str:
        """Generate markdown summary for opportunity.

        Args:
            parsed_data: Parsed message data
            job_details: Extracted job details

        Returns:
            Markdown formatted string
        """
        # Build markdown
        markdown = f"# LinkedIn: Job Opportunity from {parsed_data['sender_name']}\n\n"
        markdown += f"**From:** {parsed_data['sender_name']}\n"
        markdown += f"**Company:** {parsed_data['company']}\n"
        markdown += f"**Date:** {parsed_data['timestamp']}\n"

        if parsed_data.get('sender_profile'):
            markdown += f"**Profile:** {parsed_data['sender_profile']}\n"

        markdown += "\n---\n\n"

        # Job details
        markdown += "## Position Details\n\n"
        markdown += f"**Title:** {job_details['title']}\n"
        markdown += f"**Location:** {job_details['location']}\n"

        # Salary information
        if job_details.get('salary'):
            salary = job_details['salary']
            if 'min' in salary and 'max' in salary:
                markdown += f"**Salary:** ${salary['min']:,} - ${salary['max']:,} {salary['currency']}\n"
            elif 'amount' in salary:
                markdown += f"**Salary:** ${salary['amount']:,} {salary['currency']}\n"

        markdown += "\n---\n\n"

        # Message body
        markdown += "## Message\n\n"
        markdown += f"{parsed_data['body']}\n\n"

        # Action items
        markdown += "## Action Items\n\n"
        markdown += "- [ ] Review opportunity\n"
        markdown += "- [ ] Research company\n"
        markdown += "- [ ] Prepare response\n"
        markdown += "- [ ] Update resume if interested\n\n"

        # Metadata
        markdown += "---\n\n"
        markdown += f"*Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        markdown += "*Source: LinkedIn*\n"

        return markdown

    def categorize_linkedin_content(self, content: str) -> str:
        """Categorize LinkedIn content.

        Args:
            content: Message text content

        Returns:
            Category string
        """
        content_lower = content.lower()

        # Check for spam first (highest priority to filter out)
        for keyword in self.config['spam_keywords']:
            if keyword in content_lower:
                return 'spam'

        # Check for business inquiry first (more specific patterns)
        # Business keywords like "partnership" should be checked before job keywords
        business_match = False
        for keyword in self.config['business_keywords']:
            if keyword in content_lower:
                business_match = True
                break

        # Check for job opportunity
        job_match = self.identify_job_opportunity(content)

        # If both match, prioritize business if it has business-specific terms
        if business_match and job_match:
            # If message has "partnership", "business", "inquiry", "proposal", "deal" - it's business
            if any(word in content_lower for word in ['partnership', 'business', 'inquiry', 'proposal', 'deal']):
                return 'business_inquiry'
            else:
                return 'job_opportunity'
        elif business_match:
            return 'business_inquiry'
        elif job_match:
            return 'job_opportunity'

        # Check for networking (but exclude very short casual messages)
        for keyword in self.config['networking_keywords']:
            if keyword in content_lower:
                # If message is very short and casual (like "Thanks for the connection!"), it's general
                if len(content) < 50 and any(casual in content_lower for casual in ['thanks', 'thank you', 'appreciate']):
                    return 'general_message'
                return 'networking_request'

        return 'general_message'

    def should_process_content(self, content_data: Dict[str, Any]) -> bool:
        """Determine if content should be processed.

        Args:
            content_data: Content data dictionary

        Returns:
            True if should be processed, False otherwise
        """
        body = content_data.get('body', '').lower()

        # Check for job opportunity
        if self.identify_job_opportunity(body):
            return True

        # Check for business keywords
        for keyword in self.config['business_keywords']:
            if keyword in body:
                return True

        # Check for spam keywords (skip if spam)
        for keyword in self.config['spam_keywords']:
            if keyword in body:
                return False

        # Skip very short messages
        if len(body) < 20:
            return False

        return False

    def save_opportunity(self, summary: str, parsed_data: Dict[str, Any]) -> str:
        """Save opportunity summary to vault.

        Args:
            summary: Markdown summary content
            parsed_data: Parsed message data

        Returns:
            Path to saved file
        """
        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        sender_name = parsed_data['sender_name'].replace(' ', '-').replace('/', '-')
        # Remove special characters
        sender_name = ''.join(c for c in sender_name if c.isalnum() or c == '-')
        filename = f"{timestamp}_linkedin_{sender_name}.md"

        # Save to Inbox/linkedin
        inbox_path = self.vault_path / 'Inbox' / 'linkedin'
        filepath = inbox_path / filename

        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)

        logger.info(f"Saved LinkedIn opportunity to {filepath}")

        return str(filepath)

    def process_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process complete LinkedIn content.

        Args:
            content_data: Raw content data from watcher

        Returns:
            Dictionary with processing results
        """
        try:
            # Check if should process
            if not self.should_process_content(content_data):
                return {
                    'success': True,
                    'processed': False,
                    'reason': 'Content filtered out (not relevant)'
                }

            # Parse content
            parsed_data = self.parse_linkedin_content(content_data)

            # Categorize
            category = self.categorize_linkedin_content(parsed_data['body'])

            # Extract job details if job opportunity
            job_details = None
            if category == 'job_opportunity':
                job_details = self.extract_job_details(parsed_data['body'])

            # Generate summary
            if job_details:
                summary = self.generate_opportunity_summary(parsed_data, job_details)
            else:
                # For non-job content, create simple summary
                summary = f"# LinkedIn: {category.replace('_', ' ').title()} from {parsed_data['sender_name']}\n\n"
                summary += f"**From:** {parsed_data['sender_name']}\n"
                summary += f"**Company:** {parsed_data['company']}\n\n"
                summary += f"## Message\n\n{parsed_data['body']}\n"

            # Save summary
            filepath = self.save_opportunity(summary, parsed_data)

            return {
                'success': True,
                'processed': True,
                'filepath': filepath,
                'category': category,
                'sender': parsed_data['sender_name']
            }

        except Exception as e:
            logger.error(f"Error processing LinkedIn content: {e}")
            return {
                'success': False,
                'processed': False,
                'error': str(e)
            }
