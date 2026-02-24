"""Database Manager for AI Employee Silver Tier.

Provides centralized database operations with connection pooling,
transaction management, and comprehensive CRUD operations for all
Silver Tier entities.
"""

import sqlite3
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for AI Employee.

    Handles all database interactions with proper connection management,
    transaction support, and error handling.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file. Defaults to vault Database folder.
        """
        if db_path is None:
            vault_path = Path(__file__).parent.parent.parent / 'AI_Employee_Vault'
            db_path = vault_path / 'Database' / 'ai_employee.db'

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _init_database(self):
        """Create all required tables if they don't exist."""
        schema = """
        -- Items table: All processed items from all sources
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,  -- gmail, filesystem, whatsapp, linkedin
            type TEXT NOT NULL,    -- email, file, message, post
            category TEXT,         -- invoice, receipt, contract, etc.
            priority TEXT DEFAULT 'normal',  -- urgent, normal, low
            amount REAL,
            status TEXT DEFAULT 'pending',  -- pending, approved, rejected, done
            file_path TEXT,
            metadata TEXT,         -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        );

        -- Approvals table: Approval workflow tracking
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decided_at TIMESTAMP,
            decision TEXT,  -- approved, rejected, expired
            reason TEXT,
            auto_decided BOOLEAN DEFAULT 0,
            deadline TIMESTAMP,
            reminder_sent BOOLEAN DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        );

        -- Plans table: AI-generated execution plans
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            complexity TEXT,  -- simple, detailed
            status TEXT DEFAULT 'pending_approval',  -- pending_approval, active, completed
            steps_total INTEGER DEFAULT 0,
            steps_completed INTEGER DEFAULT 0,
            estimated_hours REAL,
            actual_hours REAL,
            budget REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        );

        -- Workflows table: Workflow execution state
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            workflow_type TEXT NOT NULL,  -- invoice, receipt, research, etc.
            item_id TEXT,
            current_step INTEGER DEFAULT 1,
            total_steps INTEGER DEFAULT 1,
            status TEXT DEFAULT 'running',  -- running, paused, completed, failed
            state_data TEXT,  -- JSON string for workflow-specific data
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
        );

        -- Financial records table: Money tracking
        CREATE TABLE IF NOT EXISTS financial_records (
            id TEXT PRIMARY KEY,
            item_id TEXT,
            record_type TEXT NOT NULL,  -- invoice, payment, receipt, expense
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            vendor TEXT,
            payee TEXT,
            due_date TIMESTAMP,
            payment_status TEXT DEFAULT 'pending',  -- pending, paid, overdue
            paid_at TIMESTAMP,
            category TEXT,
            receipt_path TEXT,
            tax_deductible BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
        );

        -- Activity log table: Audit trail
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT DEFAULT 'INFO',  -- DEBUG, INFO, WARN, ERROR
            component TEXT NOT NULL,    -- which skill/watcher
            action TEXT NOT NULL,
            item_id TEXT,
            details TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
        );

        -- LinkedIn posts table: Autonomous posting queue
        CREATE TABLE IF NOT EXISTS linkedin_posts (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            media_paths TEXT,  -- JSON array of file paths
            link_url TEXT,
            document_path TEXT,
            scheduled_time TIMESTAMP,
            posted_time TIMESTAMP,
            status TEXT DEFAULT 'pending',  -- pending, approved, posted, failed
            importance_level TEXT DEFAULT 'normal',  -- low, normal, high, critical
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 2,
            error_message TEXT,
            approval_id TEXT,  -- Link to approvals table if needed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE SET NULL
        );

        -- Create indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
        CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
        CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
        CREATE INDEX IF NOT EXISTS idx_approvals_decision ON approvals(decision);
        CREATE INDEX IF NOT EXISTS idx_approvals_deadline ON approvals(deadline);
        CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
        CREATE INDEX IF NOT EXISTS idx_financial_status ON financial_records(payment_status);
        CREATE INDEX IF NOT EXISTS idx_financial_due_date ON financial_records(due_date);
        CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_linkedin_posts_status ON linkedin_posts(status);
        CREATE INDEX IF NOT EXISTS idx_linkedin_posts_scheduled ON linkedin_posts(scheduled_time);
        """

        with self._get_connection() as conn:
            conn.executescript(schema)
            conn.commit()
            logger.info("Database initialized successfully")

    # === Items Operations ===

    def create_item(self, item_data: Dict[str, Any]) -> bool:
        """Create a new item record."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(item_data.keys())
                placeholders = ', '.join(['?' for _ in item_data])
                query = f"INSERT INTO items ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(item_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating item: {e}")
            return False

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM items WHERE id = ?",
                    (item_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting item: {e}")
            return None

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update item fields."""
        try:
            with self._get_connection() as conn:
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                query = f"UPDATE items SET {set_clause} WHERE id = ?"
                conn.execute(query, list(updates.values()) + [item_id])
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating item: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """Delete item by ID."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting item: {e}")
            return False

    def get_items_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Get all items from a specific source."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM items WHERE source = ? ORDER BY created_at DESC",
                    (source,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting items by source: {e}")
            return []

    def get_items_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all items with a specific status."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM items WHERE status = ? ORDER BY created_at DESC",
                    (status,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting items by status: {e}")
            return []

    # === Approvals Operations ===

    def create_approval(self, approval_data: Dict[str, Any]) -> bool:
        """Create a new approval record."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(approval_data.keys())
                placeholders = ', '.join(['?' for _ in approval_data])
                query = f"INSERT INTO approvals ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(approval_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating approval: {e}")
            return False

    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Get approval by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM approvals WHERE id = ?",
                    (approval_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting approval: {e}")
            return None

    def update_approval(self, approval_id: str, updates: Dict[str, Any]) -> bool:
        """Update approval fields."""
        try:
            with self._get_connection() as conn:
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                query = f"UPDATE approvals SET {set_clause} WHERE id = ?"
                conn.execute(query, list(updates.values()) + [approval_id])
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating approval: {e}")
            return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals with item details."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT a.*, i.source, i.type, i.category, i.amount, i.file_path
                    FROM approvals a
                    JOIN items i ON a.item_id = i.id
                    WHERE a.decision IS NULL
                    ORDER BY a.deadline ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending approvals: {e}")
            return []

    def get_overdue_approvals(self) -> List[Dict[str, Any]]:
        """Get approvals past their deadline."""
        try:
            with self._get_connection() as conn:
                # Use CURRENT_TIMESTAMP for comparison
                cursor = conn.execute("""
                    SELECT a.*, i.source, i.type, i.category, i.amount
                    FROM approvals a
                    JOIN items i ON a.item_id = i.id
                    WHERE a.decision IS NULL AND a.deadline < CURRENT_TIMESTAMP
                    ORDER BY a.deadline ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting overdue approvals: {e}")
            return []

    # === Plans Operations ===

    def create_plan(self, plan_data: Dict[str, Any]) -> bool:
        """Create a new plan record."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(plan_data.keys())
                placeholders = ', '.join(['?' for _ in plan_data])
                query = f"INSERT INTO plans ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(plan_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating plan: {e}")
            return False

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get plan by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM plans WHERE id = ?",
                    (plan_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting plan: {e}")
            return None

    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> bool:
        """Update plan fields."""
        try:
            with self._get_connection() as conn:
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                query = f"UPDATE plans SET {set_clause} WHERE id = ?"
                conn.execute(query, list(updates.values()) + [plan_id])
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating plan: {e}")
            return False

    def get_active_plans(self) -> List[Dict[str, Any]]:
        """Get all active plans."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM plans WHERE status = 'active' ORDER BY started_at DESC"
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting active plans: {e}")
            return []

    # === Workflows Operations ===

    def create_workflow(self, workflow_data: Dict[str, Any]) -> bool:
        """Create a new workflow record."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(workflow_data.keys())
                placeholders = ', '.join(['?' for _ in workflow_data])
                query = f"INSERT INTO workflows ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(workflow_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating workflow: {e}")
            return False

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM workflows WHERE id = ?",
                    (workflow_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting workflow: {e}")
            return None

    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> bool:
        """Update workflow fields."""
        try:
            with self._get_connection() as conn:
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                query = f"UPDATE workflows SET {set_clause} WHERE id = ?"
                conn.execute(query, list(updates.values()) + [workflow_id])
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating workflow: {e}")
            return False

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM workflows WHERE status IN ('running', 'paused') ORDER BY started_at DESC"
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting active workflows: {e}")
            return []

    # === Financial Records Operations ===

    def create_financial_record(self, record_data: Dict[str, Any]) -> bool:
        """Create a new financial record."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(record_data.keys())
                placeholders = ', '.join(['?' for _ in record_data])
                query = f"INSERT INTO financial_records ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(record_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating financial record: {e}")
            return False

    def get_financial_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get financial record by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM financial_records WHERE id = ?",
                    (record_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting financial record: {e}")
            return None

    def update_financial_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update financial record fields."""
        try:
            with self._get_connection() as conn:
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                query = f"UPDATE financial_records SET {set_clause} WHERE id = ?"
                conn.execute(query, list(updates.values()) + [record_id])
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating financial record: {e}")
            return False

    def get_pending_invoices(self) -> List[Dict[str, Any]]:
        """Get all pending invoices."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM financial_records
                    WHERE record_type = 'invoice' AND payment_status = 'pending'
                    ORDER BY due_date ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending invoices: {e}")
            return []

    def get_overdue_invoices(self) -> List[Dict[str, Any]]:
        """Get overdue invoices."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM financial_records
                    WHERE record_type = 'invoice'
                    AND payment_status = 'pending'
                    AND due_date < date('now')
                    ORDER BY due_date ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting overdue invoices: {e}")
            return []

    def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary for dashboard."""
        try:
            with self._get_connection() as conn:
                # Pending invoices
                cursor = conn.execute("""
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM financial_records
                    WHERE record_type = 'invoice' AND payment_status = 'pending'
                """)
                pending_count, pending_amount = cursor.fetchone()

                # Paid this month
                cursor = conn.execute("""
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM financial_records
                    WHERE record_type = 'invoice' AND payment_status = 'paid'
                    AND strftime('%Y-%m', paid_at) = strftime('%Y-%m', 'now')
                """)
                paid_count, paid_amount = cursor.fetchone()

                # Expenses this month
                cursor = conn.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM financial_records
                    WHERE record_type = 'expense'
                    AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                """)
                expenses = cursor.fetchone()[0]

                return {
                    'pending_invoices_count': pending_count,
                    'pending_invoices_amount': pending_amount,
                    'paid_this_month_count': paid_count,
                    'paid_this_month_amount': paid_amount,
                    'expenses_this_month': expenses
                }
        except sqlite3.Error as e:
            logger.error(f"Error getting financial summary: {e}")
            return {}

    # === Activity Log Operations ===

    def log_activity(self, log_data: Dict[str, Any]) -> bool:
        """Log an activity."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(log_data.keys())
                placeholders = ', '.join(['?' for _ in log_data])
                query = f"INSERT INTO activity_log ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(log_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error logging activity: {e}")
            return False

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity log entries."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting recent activity: {e}")
            return []

    # === Utility Methods ===

    def get_tables(self) -> List[str]:
        """Get list of all tables in database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting tables: {e}")
            return []

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                stats = {}
                for table in ['items', 'approvals', 'plans', 'workflows', 'financial_records', 'activity_log', 'linkedin_posts']:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                return stats
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    # === LinkedIn Posts Operations ===

    def create_linkedin_post(self, post_data: Dict[str, Any]) -> bool:
        """Create a new LinkedIn post record."""
        try:
            with self._get_connection() as conn:
                fields = ', '.join(post_data.keys())
                placeholders = ', '.join(['?' for _ in post_data])
                query = f"INSERT INTO linkedin_posts ({fields}) VALUES ({placeholders})"
                conn.execute(query, list(post_data.values()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating LinkedIn post: {e}")
            return False

    def get_linkedin_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get LinkedIn post by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM linkedin_posts WHERE id = ?",
                    (post_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting LinkedIn post: {e}")
            return None

    def update_linkedin_post(self, post_id: str, updates: Dict[str, Any]) -> bool:
        """Update LinkedIn post fields."""
        try:
            with self._get_connection() as conn:
                # Always update updated_at timestamp
                updates['updated_at'] = datetime.now().isoformat()
                set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                query = f"UPDATE linkedin_posts SET {set_clause} WHERE id = ?"
                conn.execute(query, list(updates.values()) + [post_id])
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating LinkedIn post: {e}")
            return False

    def get_pending_linkedin_posts(self) -> List[Dict[str, Any]]:
        """Get all pending LinkedIn posts (approved and ready to post)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM linkedin_posts
                    WHERE status = 'approved'
                    AND scheduled_time <= CURRENT_TIMESTAMP
                    ORDER BY scheduled_time ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending LinkedIn posts: {e}")
            return []

    def get_linkedin_posts_needing_approval(self) -> List[Dict[str, Any]]:
        """Get LinkedIn posts that need approval."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM linkedin_posts
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting LinkedIn posts needing approval: {e}")
            return []

    def get_failed_linkedin_posts(self) -> List[Dict[str, Any]]:
        """Get failed LinkedIn posts that can be retried."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM linkedin_posts
                    WHERE status = 'failed'
                    AND retry_count < max_retries
                    ORDER BY updated_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting failed LinkedIn posts: {e}")
            return []

    def get_linkedin_posts_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get LinkedIn posts by status."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM linkedin_posts WHERE status = ? ORDER BY created_at DESC",
                    (status,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting LinkedIn posts by status: {e}")
            return []
