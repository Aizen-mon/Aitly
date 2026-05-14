"""
Cache service for storing and retrieving API responses to reduce Tally queries.
Uses SQLite for local persistence.
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class CacheService:
    """Local SQLite cache for API responses and query results."""

    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize cache database tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Cache table for API responses
        c.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        # Query history for analytics
        c.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                intent TEXT,
                timestamp REAL NOT NULL,
                source TEXT DEFAULT 'user'
            )
        """)

        # Recent transactions for activity log
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL,
                description TEXT,
                timestamp REAL NOT NULL,
                tally_id TEXT
            )
        """)

        conn.commit()
        conn.close()

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Store a value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (default 5 minutes)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        now = time.time()
        expires_at = now + ttl_seconds
        value_json = json.dumps(value)

        c.execute("""
            INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
            VALUES (?, ?, ?, ?)
        """, (key, value_json, expires_at, now))

        conn.commit()
        conn.close()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        now = time.time()
        c.execute("""
            SELECT value FROM cache
            WHERE key = ? AND expires_at > ?
        """, (key, now))

        result = c.fetchone()
        conn.close()

        if result:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return None

        return None

    def delete(self, key: str):
        """Delete a cache entry."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    def clear_expired(self):
        """Remove expired cache entries."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = time.time()
        c.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
        conn.commit()
        conn.close()

    def add_query(self, query_text: str, intent: str = None, source: str = "user"):
        """
        Log a user query for history and analytics.

        Args:
            query_text: The user's query text
            intent: Detected intent
            source: Source of query (user, system, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO query_history (query_text, intent, timestamp, source)
            VALUES (?, ?, ?, ?)
        """, (query_text, intent, time.time(), source))

        conn.commit()
        conn.close()

    def get_query_history(self, limit: int = 20) -> list:
        """Get recent query history."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            SELECT query_text, intent, timestamp
            FROM query_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        results = c.fetchall()
        conn.close()

        return [
            {
                "query": r[0],
                "intent": r[1],
                "timestamp": datetime.fromtimestamp(r[2]).isoformat()
            }
            for r in results
        ]

    def add_transaction(self, txn_type: str, amount: float = None,
                       description: str = None, tally_id: str = None):
        """
        Log a transaction for activity tracking.

        Args:
            txn_type: Type of transaction (invoice, payment, return, etc.)
            amount: Transaction amount
            description: Human-readable description
            tally_id: Tally reference ID
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO transactions (type, amount, description, timestamp, tally_id)
            VALUES (?, ?, ?, ?, ?)
        """, (txn_type, amount, description, time.time(), tally_id))

        conn.commit()
        conn.close()

    def get_recent_transactions(self, limit: int = 10,
                               hours: int = 24) -> list:
        """Get recent transactions within specified hours."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        cutoff_time = time.time() - (hours * 3600)

        c.execute("""
            SELECT type, amount, description, timestamp, tally_id
            FROM transactions
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (cutoff_time, limit))

        results = c.fetchall()
        conn.close()

        return [
            {
                "type": r[0],
                "amount": r[1],
                "description": r[2],
                "timestamp": datetime.fromtimestamp(r[3]).isoformat(),
                "tally_id": r[4]
            }
            for r in results
        ]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Active cache entries
        now = time.time()
        c.execute("SELECT COUNT(*) FROM cache WHERE expires_at > ?", (now,))
        active_entries = c.fetchone()[0]

        # Expired entries
        c.execute("SELECT COUNT(*) FROM cache WHERE expires_at <= ?", (now,))
        expired_entries = c.fetchone()[0]

        # Query history
        c.execute("SELECT COUNT(*) FROM query_history")
        total_queries = c.fetchone()[0]

        # Transaction count today
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        c.execute("""
            SELECT COUNT(*) FROM transactions WHERE timestamp >= ?
        """, (today_start,))
        today_transactions = c.fetchone()[0]

        conn.close()

        return {
            "active_cache_entries": active_entries,
            "expired_cache_entries": expired_entries,
            "total_queries": total_queries,
            "today_transactions": today_transactions
        }
