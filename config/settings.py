"""
Application settings using Pydantic Settings.

Loads configuration from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # OpenRouter API (used for both LLM and image generation)
    openrouter_api_key: str

    # Twitter API credentials
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_secret: str
    twitter_bearer_token: str

    # PostgreSQL database
    database_url: str

    # Bot configuration
    post_interval_minutes: int = 30
    mentions_interval_minutes: int = 20
    enable_image_generation: bool = True

    # Unified Agent (new architecture)
    use_unified_agent: bool = True
    agent_interval_minutes: int = 30

    # Feature toggles
    allow_mentions: bool = True  # Set to false to disable mentions even if tier allows


# Global settings instance
settings = Settings()
