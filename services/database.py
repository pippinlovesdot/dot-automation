"""
Database service using asyncpg for PostgreSQL.

Handles storage and retrieval of posts and mentions.
"""

import logging
from typing import Any

import asyncpg

from config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """Async PostgreSQL database client using asyncpg."""

    def __init__(self):
        """Initialize database client."""
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """
        Connect to PostgreSQL and create tables if needed.

        Establishes connection pool and initializes schema.
        """
        logger.info("Connecting to database...")
        self.pool = await asyncpg.create_pool(settings.database_url)

        # Create tables if they don't exist
        async with self.pool.acquire() as conn:
            # Posts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    tweet_id VARCHAR(50),
                    include_picture BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Add include_picture column if it doesn't exist (for existing tables)
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'posts' AND column_name = 'include_picture'
                    ) THEN
                        ALTER TABLE posts ADD COLUMN include_picture BOOLEAN DEFAULT FALSE;
                    END IF;
                END $$;
            """)

            # Mentions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mentions (
                    id SERIAL PRIMARY KEY,
                    tweet_id VARCHAR(50) UNIQUE,
                    author_handle VARCHAR(50),
                    author_text TEXT,
                    our_reply TEXT,
                    action VARCHAR(20),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Bot state table (for storing last_mention_id, etc.)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    key VARCHAR(50) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

        logger.info("Database connected and tables created")

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    async def get_recent_posts_formatted(self, limit: int = 50) -> str:
        """
        Get recent posts formatted for LLM context.

        Args:
            limit: Maximum number of posts to retrieve.

        Returns:
            Formatted string with numbered posts.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                WITH numbered AS (
                    SELECT
                        text,
                        include_picture,
                        row_number() OVER (ORDER BY created_at ASC) AS rn
                    FROM posts
                )
                SELECT
                    COALESCE(
                        string_agg(
                            'post ' || rn || ' (pic: ' || include_picture || '): ' || text,
                            E'\n' ORDER BY rn
                        ),
                        'No previous posts'
                    ) AS texts
                FROM numbered
                WHERE rn > (SELECT COUNT(*) FROM posts) - $1
            """, limit)
            return row["texts"]

    async def get_recent_posts(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent posts from database.

        Args:
            limit: Maximum number of posts to retrieve.

        Returns:
            List of post dictionaries.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, text, tweet_id, include_picture, created_at FROM posts ORDER BY created_at DESC LIMIT $1",
                limit
            )
            return [dict(row) for row in rows]

    async def save_post(self, text: str, tweet_id: str, include_picture: bool) -> int:
        """
        Save a new post to database.

        Args:
            text: Post text content.
            tweet_id: Twitter tweet ID.
            include_picture: Whether post includes an image.

        Returns:
            Database ID of the created post.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO posts (text, tweet_id, include_picture) VALUES ($1, $2, $3) RETURNING id",
                text, tweet_id, include_picture
            )
            logger.info(f"Saved post {row['id']} with tweet_id {tweet_id}, include_picture={include_picture}")
            return row["id"]

    async def save_mention(
        self,
        tweet_id: str,
        author_handle: str,
        author_text: str,
        our_reply: str | None,
        action: str
    ) -> int:
        """
        Save a processed mention to database.

        Args:
            tweet_id: Original tweet ID.
            author_handle: Twitter handle of the author.
            author_text: Text of the mention.
            our_reply: Our reply text (None if ignored).
            action: Action taken ('replied', 'ignored', 'tool_used').

        Returns:
            Database ID of the saved mention.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mentions (tweet_id, author_handle, author_text, our_reply, action)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                tweet_id,
                author_handle,
                author_text,
                our_reply,
                action
            )
            logger.info(f"Saved mention {row['id']} with action '{action}'")
            return row["id"]

    async def get_user_mention_history(self, author_handle: str, limit: int = 5) -> str:
        """
        Get recent mention history with a specific user.

        Args:
            author_handle: Twitter handle of the user.
            limit: Maximum number of interactions to retrieve.

        Returns:
            Formatted string with conversation history.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT author_text, our_reply, created_at
                FROM mentions
                WHERE author_handle = $1 AND our_reply IS NOT NULL
                ORDER BY created_at DESC
                LIMIT $2
                """,
                author_handle, limit
            )

            if not rows:
                return "No previous conversations with this user."

            history = []
            for row in reversed(rows):  # Oldest first
                history.append(f"@{author_handle}: {row['author_text']}")
                history.append(f"You replied: {row['our_reply']}")

            return "\n".join(history)

    async def get_recent_mentions_formatted(self, limit: int = 15) -> str:
        """
        Get recent mentions formatted for LLM context.

        Args:
            limit: Maximum number of mentions to retrieve.

        Returns:
            Formatted string with recent mentions and replies.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT author_handle, author_text, our_reply, action
                FROM mentions
                WHERE our_reply IS NOT NULL
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )

            if not rows:
                return "No previous mention replies."

            history = []
            for i, row in enumerate(reversed(rows), 1):  # Oldest first
                history.append(f"{i}. @{row['author_handle']}: {row['author_text']}")
                history.append(f"   Your reply: {row['our_reply']}")

            return "\n".join(history)

    async def get_state(self, key: str) -> str | None:
        """
        Get a value from bot_state table.

        Args:
            key: State key.

        Returns:
            Value or None if not found.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM bot_state WHERE key = $1",
                key
            )
            return row["value"] if row else None

    async def set_state(self, key: str, value: str) -> None:
        """
        Set a value in bot_state table.

        Args:
            key: State key.
            value: Value to store.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_state (key, value, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()
                """,
                key, value
            )
            logger.info(f"Set state {key} = {value}")

    async def mention_exists(self, tweet_id: str) -> bool:
        """
        Check if a mention has already been processed.

        Args:
            tweet_id: Tweet ID to check.

        Returns:
            True if mention exists in database.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM mentions WHERE tweet_id = $1",
                tweet_id
            )
            return row is not None

    # ==================== Metrics Methods ====================

    async def ping(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if database is reachable.
        """
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False

    async def count_posts(self) -> int:
        """Get total number of posts."""
        if not self.pool:
            return 0

        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM posts")

    async def count_posts_today(self) -> int:
        """Get number of posts created today."""
        if not self.pool:
            return 0

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM posts WHERE created_at >= CURRENT_DATE"
            )

    async def count_mentions(self) -> int:
        """Get total number of processed mentions."""
        if not self.pool:
            return 0

        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM mentions")

    async def count_mentions_today(self) -> int:
        """Get number of mentions processed today."""
        if not self.pool:
            return 0

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM mentions WHERE created_at >= CURRENT_DATE"
            )

    async def get_last_post_time(self) -> str | None:
        """Get timestamp of the last post."""
        if not self.pool:
            return None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT created_at FROM posts ORDER BY created_at DESC LIMIT 1"
            )
            if row:
                return row["created_at"].isoformat()
            return None

    async def get_last_mention_time(self) -> str | None:
        """Get timestamp of the last processed mention."""
        if not self.pool:
            return None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT created_at FROM mentions ORDER BY created_at DESC LIMIT 1"
            )
            if row:
                return row["created_at"].isoformat()
            return None
