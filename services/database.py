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

            # Mentions table (for future use)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mentions (
                    id SERIAL PRIMARY KEY,
                    tweet_id VARCHAR(50),
                    author_handle VARCHAR(50),
                    author_text TEXT,
                    our_reply TEXT,
                    action VARCHAR(20),
                    created_at TIMESTAMP DEFAULT NOW()
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
