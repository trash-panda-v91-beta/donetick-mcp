"""Configuration management for Donetick MCP server."""

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Environment-driven configuration (reads .env and DONETICK_* vars)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    donetick_base_url: str | None = None
    donetick_api_token: str | None = None
    log_level: str = "INFO"
    rate_limit_per_second: float = 10.0
    rate_limit_burst: int = 10

    @model_validator(mode="after")
    def _validate(self) -> Config:
        base = self.donetick_base_url or ""
        errors: list[str] = []
        if not base:
            errors.append(
                "DONETICK_BASE_URL environment variable is required. Please set it to your Donetick instance URL."
            )
        elif not base.startswith("https://"):
            errors.append(f"DONETICK_BASE_URL must use HTTPS for security. Got: {base[:50]}")
        if not self.donetick_api_token:
            errors.append(
                "DONETICK_API_TOKEN environment variable is required. "
                "Generate one in Donetick settings (Access Tokens)."
            )

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        self.donetick_base_url = base.rstrip("/")
        return self

    def configure_logging(self) -> None:
        """Configure logging based on log level."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Global configuration instance
config = Config()
