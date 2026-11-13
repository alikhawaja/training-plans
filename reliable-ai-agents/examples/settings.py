"""Workshop paths and explicit, local configuration."""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".state"
FIXTURES = ROOT / "fixtures"
load_dotenv(ROOT / ".env", override=False)


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Set {name} in the environment or {ROOT / '.env'}")
    return value


def local_url(name: str, default: str) -> str:
    value = os.environ.get(name, default).rstrip("/")
    parsed = urlparse(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{name} must be a loopback HTTP origin without credentials")
    return value


def model_config() -> tuple[str, str, str]:
    provider = required("AGENT_PROVIDER")
    if provider not in {"openai", "anthropic"}:
        raise ValueError("AGENT_PROVIDER must be openai or anthropic; no fallback is used")
    model = required("AGENT_MODEL")
    key = required("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY")
    return provider, model, key
