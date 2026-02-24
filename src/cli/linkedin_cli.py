#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LinkedIn Poster CLI - Command-line interface for autonomous LinkedIn posting.

Usage:
    python -m src.cli.linkedin_cli create "Post content" --importance normal
    python -m src.cli.linkedin_cli schedule "Post content" --time "2026-02-21 10:00"
    python -m src.cli.linkedin_cli list pending
    python -m src.cli.linkedin_cli approve <post_id>
    python -m src.cli.linkedin_cli reject <post_id> --reason "Not appropriate"
    python -m src.cli.linkedin_cli status <post_id>
    python -m src.cli.linkedin_cli retry <post_id>
    python -m src.cli.linkedin_cli post-now <post_id>
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.db_manager import DatabaseManager
from src.skills.linkedin_poster import LinkedInPoster


def setup_poster(headless: bool = False) -> LinkedInPoster:
    """Initialize database and poster.

    Args:
        headless: Run browser in headless mode (default: False, visible browser)
    """
    vault_path = Path(__file__).parent.parent.parent / 'AI_Employee_Vault'
    db_manager = DatabaseManager()
    config = {'headless': headless}
    return LinkedInPoster(db_manager, str(vault_path), config=config)


def cmd_create(args):
    """Create a new LinkedIn post."""
    poster = setup_poster()

    try:
        # Parse media paths
        media_paths = args.media.split(',') if args.media else None

        # Parse scheduled time
        scheduled_time = None
        if args.time:
            scheduled_time = datetime.fromisoformat(args.time)

        post_id = poster.create_post(
            content=args.content,
            importance_level=args.importance,
            media_paths=media_paths,
            link_url=args.link,
            document_path=args.document,
            scheduled_time=scheduled_time,
            smart_schedule=args.smart_schedule
        )

        print(f"✓ Post created successfully!")
        print(f"  Post ID: {post_id}")
        print(f"  Importance: {args.importance}")

        if args.importance in ['high', 'critical']:
            print(f"  Status: Pending approval")
            print(f"  → Check Pending_Approval/linkedin_posts/ folder")
        else:
            print(f"  Status: Approved (will post at scheduled time)")

        return 0

    except Exception as e:
        print(f"✗ Error creating post: {e}", file=sys.stderr)
        return 1


def cmd_schedule(args):
    """Schedule a post with smart scheduling."""
    args.smart_schedule = True
    return cmd_create(args)


def cmd_list(args):
    """List posts by status."""
    poster = setup_poster()

    try:
        if args.filter == 'pending':
            posts = poster.db.get_linkedin_posts_needing_approval()
            title = "Posts Pending Approval"
        elif args.filter == 'approved':
            posts = poster.db.get_linkedin_posts_by_status('approved')
            title = "Approved Posts (Ready to Post)"
        elif args.filter == 'posted':
            posts = poster.db.get_linkedin_posts_by_status('posted')
            title = "Posted"
        elif args.filter == 'failed':
            posts = poster.db.get_failed_linkedin_posts()
            title = "Failed Posts (Can Retry)"
        else:
            print(f"✗ Invalid filter: {args.filter}", file=sys.stderr)
            return 1

        print(f"\n{title}")
        print("=" * 60)

        if not posts:
            print("  (No posts found)")
            return 0

        for post in posts:
            print(f"\n  ID: {post['id'][:8]}...")
            print(f"  Content: {post['content'][:50]}...")
            print(f"  Importance: {post['importance_level']}")
            print(f"  Status: {post['status']}")

            if post['scheduled_time']:
                scheduled = datetime.fromisoformat(post['scheduled_time'])
                print(f"  Scheduled: {scheduled.strftime('%Y-%m-%d %H:%M')}")

            if post['posted_time']:
                posted = datetime.fromisoformat(post['posted_time'])
                print(f"  Posted: {posted.strftime('%Y-%m-%d %H:%M')}")

            if post['error_message']:
                print(f"  Error: {post['error_message']}")

            if post['retry_count'] > 0:
                print(f"  Retries: {post['retry_count']}/{post['max_retries']}")

        print(f"\n  Total: {len(posts)} posts")
        return 0

    except Exception as e:
        print(f"✗ Error listing posts: {e}", file=sys.stderr)
        return 1


def cmd_approve(args):
    """Approve a pending post."""
    poster = setup_poster()

    try:
        result = poster.approve_post(args.post_id)

        if result['success']:
            print(f"✓ Post approved successfully!")
            print(f"  Post ID: {args.post_id}")
            print(f"  → Will post at scheduled time")
        else:
            print(f"✗ Failed to approve: {result['error']}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"✗ Error approving post: {e}", file=sys.stderr)
        return 1


def cmd_reject(args):
    """Reject a pending post."""
    poster = setup_poster()

    try:
        result = poster.reject_post(args.post_id, args.reason)

        if result['success']:
            print(f"✓ Post rejected")
            print(f"  Post ID: {args.post_id}")
            print(f"  Reason: {args.reason}")
        else:
            print(f"✗ Failed to reject: {result['error']}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"✗ Error rejecting post: {e}", file=sys.stderr)
        return 1


def cmd_status(args):
    """Show detailed post status."""
    poster = setup_poster()

    try:
        post = poster.db.get_linkedin_post(args.post_id)

        if not post:
            print(f"✗ Post not found: {args.post_id}", file=sys.stderr)
            return 1

        print(f"\nLinkedIn Post Status")
        print("=" * 60)
        print(f"  ID: {post['id']}")
        print(f"  Status: {post['status']}")
        print(f"  Importance: {post['importance_level']}")
        print(f"\n  Content:")
        print(f"  {post['content']}\n")

        if post['media_paths']:
            media = json.loads(post['media_paths'])
            print(f"  Media: {len(media)} file(s)")
            for path in media:
                print(f"    - {path}")

        if post['link_url']:
            print(f"  Link: {post['link_url']}")

        if post['document_path']:
            print(f"  Document: {post['document_path']}")

        if post['scheduled_time']:
            scheduled = datetime.fromisoformat(post['scheduled_time'])
            print(f"\n  Scheduled: {scheduled.strftime('%Y-%m-%d %H:%M:%S')}")

        if post['posted_time']:
            posted = datetime.fromisoformat(post['posted_time'])
            print(f"  Posted: {posted.strftime('%Y-%m-%d %H:%M:%S')}")

        if post['error_message']:
            print(f"\n  Error: {post['error_message']}")

        if post['retry_count'] > 0:
            print(f"  Retries: {post['retry_count']}/{post['max_retries']}")

        created = datetime.fromisoformat(post['created_at'])
        print(f"\n  Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")

        return 0

    except Exception as e:
        print(f"✗ Error getting status: {e}", file=sys.stderr)
        return 1


def cmd_retry(args):
    """Retry a failed post."""
    poster = setup_poster()

    try:
        result = poster.retry_post(args.post_id)

        if result['success']:
            print(f"✓ Post retry initiated")
            print(f"  Post ID: {args.post_id}")
            print(f"  Retry attempt: {result['retry_count']}")
            print(f"  → Will attempt to post at scheduled time")
        else:
            print(f"✗ Failed to retry: {result['error']}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"✗ Error retrying post: {e}", file=sys.stderr)
        return 1


def cmd_post_now(args):
    """Post immediately (bypass schedule)."""
    headless = getattr(args, 'headless', False)
    poster = setup_poster(headless=headless)

    try:
        print(f"Posting to LinkedIn...")
        if not headless:
            print(f"  Browser will open visibly - complete any verification if prompted")
        result = poster.post_to_linkedin(args.post_id)

        if result['success']:
            print(f"✓ Posted successfully to LinkedIn!")
            print(f"  Post ID: {args.post_id}")
        else:
            print(f"✗ Failed to post: {result['error']}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"✗ Error posting: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='LinkedIn Poster CLI - Autonomous LinkedIn posting',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new post')
    create_parser.add_argument('content', help='Post content (max 3000 chars)')
    create_parser.add_argument('--importance', choices=['low', 'normal', 'high', 'critical'],
                              default='normal', help='Importance level (default: normal)')
    create_parser.add_argument('--media', help='Comma-separated image paths')
    create_parser.add_argument('--link', help='URL to share')
    create_parser.add_argument('--document', help='Document path (PDF, etc.)')
    create_parser.add_argument('--time', help='Schedule time (ISO format: 2026-02-21T10:00:00)')
    create_parser.add_argument('--smart-schedule', action='store_true',
                              help='Auto-schedule at optimal time')
    create_parser.set_defaults(func=cmd_create)

    # Schedule command (alias for create with smart-schedule)
    schedule_parser = subparsers.add_parser('schedule', help='Schedule post at optimal time')
    schedule_parser.add_argument('content', help='Post content')
    schedule_parser.add_argument('--importance', choices=['low', 'normal', 'high', 'critical'],
                                default='normal', help='Importance level')
    schedule_parser.add_argument('--media', help='Comma-separated image paths')
    schedule_parser.add_argument('--link', help='URL to share')
    schedule_parser.add_argument('--document', help='Document path')
    schedule_parser.set_defaults(func=cmd_schedule, smart_schedule=True, time=None)

    # List command
    list_parser = subparsers.add_parser('list', help='List posts')
    list_parser.add_argument('filter', choices=['pending', 'approved', 'posted', 'failed'],
                            help='Filter by status')
    list_parser.set_defaults(func=cmd_list)

    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve a pending post')
    approve_parser.add_argument('post_id', help='Post ID to approve')
    approve_parser.set_defaults(func=cmd_approve)

    # Reject command
    reject_parser = subparsers.add_parser('reject', help='Reject a pending post')
    reject_parser.add_argument('post_id', help='Post ID to reject')
    reject_parser.add_argument('--reason', default='No reason provided',
                              help='Rejection reason')
    reject_parser.set_defaults(func=cmd_reject)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show post status')
    status_parser.add_argument('post_id', help='Post ID')
    status_parser.set_defaults(func=cmd_status)

    # Retry command
    retry_parser = subparsers.add_parser('retry', help='Retry a failed post')
    retry_parser.add_argument('post_id', help='Post ID to retry')
    retry_parser.set_defaults(func=cmd_retry)

    # Post now command
    post_now_parser = subparsers.add_parser('post-now', help='Post immediately')
    post_now_parser.add_argument('post_id', help='Post ID to post now')
    post_now_parser.add_argument('--headless', action='store_true',
                                help='Run browser in headless mode (default: visible)')
    post_now_parser.set_defaults(func=cmd_post_now)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
