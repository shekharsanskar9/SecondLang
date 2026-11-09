"""Application settings, read from environment variables / a .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    # Which engine refines your text: "ollama" (local, free), "anthropic", "openai" or "offline".
    provider: str = "ollama"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Your first language - the coach uses it to explain mistakes and translate mixed-in words.
    native_language: str = "Hindi"

    db_path: str = "data/secondlang.db"
    request_timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        env = os.getenv
        return cls(
            provider=env("LLM_PROVIDER", cls.provider).strip().lower(),
            ollama_url=env("OLLAMA_URL", cls.ollama_url).rstrip("/"),
            ollama_model=env("OLLAMA_MODEL", cls.ollama_model),
            anthropic_api_key=env("ANTHROPIC_API_KEY", ""),
            anthropic_model=env("ANTHROPIC_MODEL", cls.anthropic_model),
            openai_api_key=env("OPENAI_API_KEY", ""),
            openai_model=env("OPENAI_MODEL", cls.openai_model),
            native_language=env("NATIVE_LANGUAGE", cls.native_language),
            db_path=env("DB_PATH", cls.db_path),
            request_timeout=float(env("REQUEST_TIMEOUT", str(cls.request_timeout))),
        )
