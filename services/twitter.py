"""
Twitter client using tweepy for Twitter API v2.

Handles posting tweets, replies, media uploads, and fetching mentions.
"""

import logging
from typing import Any

import tweepy

from config.settings import settings

logger = logging.getLogger(__name__)


class TwitterClient:
    """Twitter API v2 client using tweepy."""

    def __init__(self):
        """Initialize Twitter client with credentials from settings."""
        # API v2 client for tweets
        self.client = tweepy.Client(
            bearer_token=settings.twitter_bearer_token,
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_secret,
            wait_on_rate_limit=True
        )

        # API v1.1 auth for media uploads (v2 doesn't support media upload yet)
        auth = tweepy.OAuth1UserHandler(
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_secret
        )
        self.api_v1 = tweepy.API(auth)

    async def post(
        self,
        text: str,
        media_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Post a new tweet.

        Args:
            text: Tweet text content (max 280 chars).
            media_ids: Optional list of media IDs to attach.

        Returns:
            Tweet data including id and text.
        """
        try:
            response = self.client.create_tweet(
                text=text,
                media_ids=media_ids
            )
            tweet_id = response.data["id"]
            logger.info(f"Posted tweet {tweet_id}: {text[:50]}...")
            return {"id": tweet_id, "text": text}
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            raise

    async def reply(
        self,
        text: str,
        reply_to_tweet_id: str,
        media_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Reply to a tweet.

        Args:
            text: Reply text content.
            reply_to_tweet_id: ID of tweet to reply to.
            media_ids: Optional list of media IDs to attach.

        Returns:
            Reply tweet data including id and text.
        """
        try:
            response = self.client.create_tweet(
                text=text,
                in_reply_to_tweet_id=reply_to_tweet_id,
                media_ids=media_ids
            )
            tweet_id = response.data["id"]
            logger.info(f"Replied with tweet {tweet_id} to {reply_to_tweet_id}")
            return {"id": tweet_id, "text": text, "reply_to": reply_to_tweet_id}
        except Exception as e:
            logger.error(f"Error replying to tweet: {e}")
            raise

    async def upload_media(self, image_bytes: bytes) -> str:
        """
        Upload media to Twitter.

        Uses v1.1 API as v2 doesn't support media uploads yet.

        Args:
            image_bytes: Raw image bytes to upload.

        Returns:
            Media ID string for use in tweets.
        """
        import io

        try:
            # Create file-like object from bytes
            file_obj = io.BytesIO(image_bytes)
            file_obj.name = "image.png"

            # Upload using v1.1 API
            media = self.api_v1.media_upload(filename="image.png", file=file_obj)
            media_id = str(media.media_id)
            logger.info(f"Uploaded media with ID {media_id}")
            return media_id
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            raise

    def get_me(self) -> dict[str, Any]:
        """
        Get authenticated user info.

        Returns:
            User data including id and username.
        """
        try:
            response = self.client.get_me()
            return {"id": response.data.id, "username": response.data.username}
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise

    def get_mentions(self, since_id: str | None = None) -> list[dict[str, Any]]:
        """
        Get recent mentions of authenticated user.

        Args:
            since_id: Only get mentions newer than this tweet ID.

        Returns:
            List of mention tweets with author info.
        """
        try:
            # Get authenticated user ID
            me = self.get_me()
            user_id = me["id"]

            # Fetch mentions
            response = self.client.get_users_mentions(
                id=user_id,
                since_id=since_id,
                max_results=10,
                expansions=["author_id"],
                tweet_fields=["created_at", "text", "author_id"],
                user_fields=["username"]
            )

            if not response.data:
                logger.info("No new mentions found")
                return []

            # Build user lookup from includes
            users = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    users[user.id] = user.username

            # Format mentions
            mentions = []
            for tweet in response.data:
                mentions.append({
                    "id_str": str(tweet.id),
                    "text": tweet.text,
                    "user": {
                        "screen_name": users.get(tweet.author_id, "unknown")
                    }
                })

            logger.info(f"Found {len(mentions)} new mentions")
            return mentions

        except Exception as e:
            logger.error(f"Error fetching mentions: {e}")
            raise

    def get_user_profile(self, username: str) -> dict[str, Any] | None:
        """
        Get Twitter user profile by username.

        Args:
            username: Twitter handle (without @).

        Returns:
            User profile data or None if not found.
        """
        try:
            response = self.client.get_user(
                username=username,
                user_fields=["description", "public_metrics", "created_at", "location"]
            )

            if not response.data:
                logger.info(f"User @{username} not found")
                return None

            user = response.data
            metrics = user.public_metrics or {}
            return {
                "username": user.username,
                "bio": user.description or "",
                "followers": metrics.get("followers_count", 0),
                "following": metrics.get("following_count", 0),
                "tweets": metrics.get("tweet_count", 0),
                "location": user.location or ""
            }

        except Exception as e:
            logger.error(f"Error getting profile @{username}: {e}")
            return None
