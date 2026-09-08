"""Configuration settings for ACV-SE (CertifAI)."""

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class ACVConfig:
    """ACV-SE runtime configuration."""

    # Provider: 'auto', 'gemini', 'openai', 'anthropic', or 'offline'
    provider: str = os.getenv("ACV_PROVIDER", "auto")

    # Model name: default to gemini-2.5-flash (or user specified Gemini 3.5 Flash / etc.)
    model_name: str = os.getenv("ACV_MODEL", "gemini-2.5-flash")

    # Temperature: None keeps the provider default (as requested by user)
    temperature: Optional[float] = None

    # Timeout for API requests in seconds
    timeout_seconds: int = 60

    # API Keys
    gemini_api_key: Optional[str] = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    def resolve_provider(self) -> str:
        """Resolve the active provider based on configuration and available keys."""
        if self.provider != "auto":
            return self.provider.lower()

        if self.gemini_api_key:
            return "gemini"
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"

        # If no keys are provided, use deterministic offline engine
        return "offline"


# Default global instance
default_config = ACVConfig()
