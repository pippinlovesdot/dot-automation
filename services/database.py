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
                    tools_used TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Add tools_used column if it doesn't exist (for existing tables)
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'mentions' AND column_name = 'tools_used'
                    ) THEN
                        ALTER TABLE mentions ADD COLUMN tools_used TEXT;
                    END IF;
                END $$;
            """)

            # Bot state table (for storing last_mention_id, etc.)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    key VARCHAR(50) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Actions table (unified agent - posts + replies)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id SERIAL PRIMARY KEY,
                    action_type VARCHAR(20) NOT NULL,
                    text TEXT NOT NULL,
                    tweet_id VARCHAR(50),
                    include_picture BOOLEAN DEFAULT FALSE,
                    reply_to_tweet_id VARCHAR(50),
                    reply_to_author VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create indexes for actions table
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_created_at ON actions(created_at DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type)
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
        action: str,
        tools_used: str | None = None
    ) -> int:
        """
        Save a processed mention to database.

        Args:
            tweet_id: Original tweet ID.
            author_handle: Twitter handle of the author.
            author_text: Text of the mention.
            our_reply: Our reply text (None if ignored).
            action: Action taken ('replied', 'ignored', 'agent_replied').
            tools_used: Comma-separated list of tools used (e.g., 'web_search,generate_image').

        Returns:
            Database ID of the saved mention.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mentions (tweet_id, author_handle, author_text, our_reply, action, tools_used)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                tweet_id,
                author_handle,
                author_text,
                our_reply,
                action,
                tools_used
            )
            logger.info(f"Saved mention {row['id']} with action '{action}', tools: {tools_used}")
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
                WHERE LOWER(author_handle) = LOWER($1) AND our_reply IS NOT NULL
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

    async def mention_exists(self, tweet_id: str, include_pending: bool = False) -> bool:
        """
        Check if a mention has already been processed.

        Args:
            tweet_id: Tweet ID to check.
            include_pending: If False, pending mentions are not counted as "existing".

        Returns:
            True if mention exists in database (and is processed if include_pending=False).
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            if include_pending:
                row = await conn.fetchrow(
                    "SELECT 1 FROM mentions WHERE tweet_id = $1",
                    tweet_id
                )
            else:
                row = await conn.fetchrow(
                    "SELECT 1 FROM mentions WHERE tweet_id = $1 AND action != 'pending'",
                    tweet_id
                )
            return row is not None

    async def get_pending_mention(self, tweet_id: str) -> dict | None:
        """
        Get a pending mention by tweet_id.

        Returns:
            Dict with mention data or None.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT author_handle, author_text FROM mentions WHERE tweet_id = $1",
                tweet_id
            )
            if row:
                return {"author": row["author_handle"], "text": row["author_text"]}
            return None

    async def update_mention(
        self,
        tweet_id: str,
        our_reply: str,
        action: str = "agent_replied",
        tools_used: str | None = None
    ) -> None:
        """
        Update a pending mention with our reply.

        Args:
            tweet_id: Tweet ID to update.
            our_reply: Our reply text.
            action: New action status.
            tools_used: Comma-separated list of tools used.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE mentions
                SET our_reply = $2, action = $3, tools_used = $4
                WHERE tweet_id = $1
                """,
                tweet_id, our_reply, action, tools_used
            )
            logger.info(f"Updated mention {tweet_id} with action '{action}', tools: {tools_used}")

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

    # ==================== Unified Agent Methods ====================

    async def get_recent_actions_formatted(self, limit: int = 20) -> str:
        """
        Get recent actions (posts + replies) formatted for LLM context.

        Args:
            limit: Maximum number of actions to retrieve.

        Returns:
            Formatted string with numbered actions.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT action_type, text, include_picture, reply_to_author, created_at
                FROM actions
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )

            if not rows:
                return "No previous actions."

            lines = []
            for i, row in enumerate(reversed(rows), 1):  # Oldest first
                action_type = row["action_type"]
                text = row["text"]
                has_pic = row["include_picture"]

                if action_type == "post":
                    lines.append(f"{i}. POST (pic: {has_pic}): {text}")
                elif action_type == "reply":
                    author = row["reply_to_author"] or "unknown"
                    lines.append(f"{i}. REPLY to @{author} (pic: {has_pic}): {text}")

            return "\n".join(lines)

    async def save_action(
        self,
        action_type: str,
        text: str,
        tweet_id: str | None = None,
        include_picture: bool = False,
        reply_to_tweet_id: str | None = None,
        reply_to_author: str | None = None
    ) -> int:
        """
        Save an action (post or reply) to database.

        Args:
            action_type: 'post' or 'reply'
            text: The text content
            tweet_id: Our tweet ID
            include_picture: Whether action includes an image
            reply_to_tweet_id: Original tweet ID (for replies)
            reply_to_author: Original author handle (for replies)

        Returns:
            Database ID of the created action.
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO actions (
                    action_type, text, tweet_id, include_picture,
                    reply_to_tweet_id, reply_to_author
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                action_type, text, tweet_id, include_picture,
                reply_to_tweet_id, reply_to_author
            )
            logger.info(f"Saved action {row['id']}: {action_type} (pic={include_picture})")
            return row["id"]

    async def get_user_actions_history(self, author_handle: str, limit: int = 10) -> str:
        """
        Get recent reply history with a specific user from actions table.

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
                SELECT text, reply_to_author, created_at
                FROM actions
                WHERE LOWER(reply_to_author) = LOWER($1) AND action_type = 'reply'
                ORDER BY created_at DESC
                LIMIT $2
                """,
                author_handle, limit
            )

            if not rows:
                return "No previous conversations with this user."

            history = []
            for row in reversed(rows):  # Oldest first
                history.append(f"You replied to @{row['reply_to_author']}: {row['text']}")

            return "\n".join(history)

    async def count_actions_today(self, action_type: str | None = None) -> int:
        """
        Get number of actions created today.

        Args:
            action_type: Optional filter by type ('post' or 'reply')

        Returns:
            Count of actions today.
        """
        if not self.pool:
            return 0

        async with self.pool.acquire() as conn:
            if action_type:
                return await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM actions
                    WHERE created_at >= CURRENT_DATE AND action_type = $1
                    """,
                    action_type
                )
            else:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM actions WHERE created_at >= CURRENT_DATE"
                )
