#!/usr/bin/env python3
"""
LinkedIn Watcher for AI Employee
Monitors LinkedIn messages, job opportunities, and important posts
"""

import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import requests
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv

load_dotenv()

# Disable OAuth HTTPS requirement for localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configuration
VAULT_PATH = Path("AI_Employee_Vault")
INBOX_PATH = VAULT_PATH / "Inbox" / "linkedin"
LOGS_PATH = VAULT_PATH / "Logs" / "daily"

CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/callback'

# LinkedIn API endpoints
AUTHORIZATION_BASE_URL = 'https://www.linkedin.com/oauth/v2/authorization'
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'
API_BASE = 'https://api.linkedin.com/v2'

# Ensure directories exist
INBOX_PATH.mkdir(parents=True, exist_ok=True)
LOGS_PATH.mkdir(parents=True, exist_ok=True)


class LinkedInWatcher:
    def __init__(self):
        self.access_token = self.load_token()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'X-Restli-Protocol-Version': '2.0.0'
        })

    def load_token(self) -> str:
        """Load access token from file or initiate OAuth flow"""
        token_file = Path('.linkedin_token.json')

        if token_file.exists():
            try:
                with open(token_file) as f:
                    token_data = json.load(f)
                    # Check if token has access_token and is not expired
                    if 'access_token' in token_data and token_data.get('expires_at', 0) > time.time():
                        return token_data['access_token']
            except (json.JSONDecodeError, KeyError):
                print("[WARN] Corrupted token file, re-authenticating...")
                token_file.unlink()  # Delete corrupted file

        # Need to authenticate
        return self.authenticate()

    def authenticate(self) -> str:
        """Perform OAuth authentication"""
        print("[AUTH] LinkedIn authentication required")
        print("[INFO] Opening browser for login...\n")

        # Debug: Check if credentials are loaded
        if not CLIENT_ID or not CLIENT_SECRET:
            print(f"[ERROR] CLIENT_ID={CLIENT_ID}, CLIENT_SECRET={'***' if CLIENT_SECRET else 'None'}")
            raise ValueError("LinkedIn credentials not found in .env file")

        # Use only basic scopes that are available by default
        oauth = OAuth2Session(
            CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=['openid', 'profile', 'email']
        )

        authorization_url, state = oauth.authorization_url(AUTHORIZATION_BASE_URL)

        print(f"Please visit this URL to authorize:\n{authorization_url}\n")
        print("After authorization, you'll be redirected to localhost.")
        print("Copy the ENTIRE redirect URL and paste it here:")

        redirect_response = input("\nPaste redirect URL: ").strip()

        # Extract authorization code from URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(redirect_response)
        code = parse_qs(parsed.query).get('code', [None])[0]

        if not code:
            raise ValueError("No authorization code found in redirect URL")

        print("[OK] Authorization code received")

        # Exchange code for token using direct POST request
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        try:
            response = requests.post(TOKEN_URL, data=token_data)
            response.raise_for_status()
            token = response.json()
        except Exception as e:
            print(f"[ERROR] Token exchange failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"[INFO] Response: {e.response.text}")
            raise

        # Debug: Print token structure
        print(f"[DEBUG] Token response keys: {list(token.keys())}")

        # Check if access_token exists
        if 'access_token' not in token:
            print("[ERROR] Token response missing 'access_token'")
            print(f"[INFO] Full token response: {json.dumps(token, indent=2)}")
            raise ValueError("Failed to obtain access token from LinkedIn")

        # Save token
        token['expires_at'] = time.time() + token.get('expires_in', 3600)
        with open('.linkedin_token.json', 'w') as f:
            json.dump(token, f)

        print("[OK] Authentication successful!\n")
        return token['access_token']

    def get_profile(self) -> Dict:
        """Get user profile (OpenID Connect userinfo endpoint)"""
        # Use OpenID Connect userinfo endpoint instead of LinkedIn v2 API
        response = self.session.get('https://api.linkedin.com/v2/userinfo')
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': response.status_code,
                'message': response.json() if response.text else 'No response'
            }

    def get_messages(self) -> List[Dict]:
        """Get recent messages (if Messaging API is available)"""
        try:
            response = self.session.get(f'{API_BASE}/messages')
            if response.status_code == 200:
                return response.json().get('elements', [])
            return []
        except Exception as e:
            self.log_error(f"Failed to fetch messages: {e}")
            return []

    def check_important_content(self) -> List[Dict]:
        """Check for important LinkedIn activity"""
        important_items = []

        # Note: LinkedIn API is limited for consumer apps
        # Most robust features require additional permissions

        # For now, we'll focus on what's available:
        # 1. Profile changes
        # 2. Shares/posts (if available)

        try:
            self.get_profile()
            # Check if profile has been updated recently
            # ... process profile data

            messages = self.get_messages()
            for message in messages:
                if self.is_important_message(message):
                    important_items.append({
                        'type': 'message',
                        'data': message
                    })

        except Exception as e:
            self.log_error(f"Error checking LinkedIn: {e}")

        return important_items

    def is_important_message(self, message: Dict) -> bool:
        """Determine if message is important"""
        # Check for job-related keywords
        job_keywords = ['job', 'opportunity', 'position', 'role', 'hire', 'recruit']
        urgent_keywords = ['urgent', 'asap', 'important']

        text = message.get('text', {}).get('text', '').lower()

        return any(kw in text for kw in job_keywords + urgent_keywords)

    def process_message(self, message: Dict):
        """Process and save LinkedIn message"""
        timestamp = datetime.now().isoformat()
        safe_timestamp = timestamp.replace(':', '-').split('.')[0]

        # Extract sender info
        sender = message.get('from', {})
        sender_name = sender.get('firstName', '') + ' ' + sender.get('lastName', '')

        # Create filename
        filename = f"{safe_timestamp}_linkedin_{sender_name.replace(' ', '-')}.md"
        filepath = INBOX_PATH / filename

        # Determine priority
        text = message.get('text', {}).get('text', '')
        is_urgent = any(kw in text.lower() for kw in ['urgent', 'job', 'opportunity'])

        # Create markdown
        markdown = f"# LinkedIn: Message from {sender_name}\n\n"
        markdown += f"**From:** {sender_name}\n"
        markdown += f"**Date:** {timestamp}\n"
        markdown += f"**Priority:** {'URGENT' if is_urgent else 'NORMAL'}\n"
        markdown += "**Type:** Message\n\n"
        markdown += f"## Message\n\n{text}\n\n"
        markdown += "## Profile\n"
        markdown += f"- LinkedIn: [View Profile]({sender.get('profileUrl', '')})\n\n"
        markdown += "## Actions Needed\n"
        markdown += "- [ ] Review message\n"
        markdown += "- [ ] Respond if interested\n"
        markdown += "- [ ] Archive when complete\n\n"
        markdown += "---\n"
        markdown += f"*Processed by linkedin-processor skill at {timestamp}*\n"

        # Save
        filepath.write_text(markdown)

        print(f"  [OK] Saved: {filename}")
        print(f"  [INFO] Priority: {'URGENT' if is_urgent else 'NORMAL'}")

    def log_error(self, message: str):
        """Log error to daily log file"""
        log_file = LOGS_PATH / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        log_entry = f"[{datetime.now().isoformat()}] [ERROR] [LinkedInWatcher] {message}\n"

        with open(log_file, 'a') as f:
            f.write(log_entry)

    def run(self, interval: int = 300):
        """Run watcher loop"""
        print("LinkedIn watcher started")
        print(f"Checking every {interval} seconds")
        print("Monitoring for important LinkedIn activity...\n")

        try:
            while True:
                try:
                    important_items = self.check_important_content()

                    for item in important_items:
                        if item['type'] == 'message':
                            self.process_message(item['data'])

                    if important_items:
                        print(f"[OK] Processed {len(important_items)} items")

                except Exception as e:
                    print(f"[ERROR] Error in check loop: {e}")
                    self.log_error(str(e))

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nLinkedIn watcher stopped")


def main():
    # Check for credentials
    if not os.getenv('LINKEDIN_CLIENT_ID') or not os.getenv('LINKEDIN_CLIENT_SECRET'):
        print("[ERROR] LinkedIn credentials not found!")
        print("\nPlease add to .env file:")
        print("LINKEDIN_CLIENT_ID=your_client_id")
        print("LINKEDIN_CLIENT_SECRET=your_client_secret")
        print("\nGet credentials from: https://www.linkedin.com/developers/")
        return

    watcher = LinkedInWatcher()
    watcher.run(interval=300)  # Check every 5 minutes


if __name__ == '__main__':
    main()
