from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from model_provider import ProviderConfig, normalize_provider


@dataclass
class LabConfig:
    """Student TODO: define the shared configuration for the lab.

    Hints:
    - Keep paths for the repo root, dataset directory, and state directory.
    - Add compact-memory settings such as threshold and number of messages to keep.
    - Add provider settings for `openai`, `custom`, `gemini`, `anthropic`, `ollama`, and `openrouter`.
    """

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Student TODO: load environment variables and return a LabConfig.

    Pseudocode:
    1. Resolve the repo root or default to the current file parent.
    2. Optionally load values from `.env`.
    3. Create `state/` if it does not exist.
    4. Return a populated LabConfig instance.
    """

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()

    try:
        from dotenv import load_dotenv

        load_dotenv(root / ".env")
    except ImportError:
        pass

    provider = normalize_provider(os.getenv("LLM_PROVIDER", "custom"))
    model_name = os.getenv("LLM_MODEL")
    base_url = None
    api_key = None

    if provider == "openai":
        model_name = model_name or "gpt-4o-mini"
        api_key = os.getenv("OPENAI_API_KEY")
    elif provider == "gemini":
        model_name = model_name or "gemini-1.5-flash"
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    elif provider == "anthropic":
        model_name = model_name or "claude-3-5-haiku-latest"
        api_key = os.getenv("ANTHROPIC_API_KEY")
    elif provider == "ollama":
        model_name = model_name or "llama3.1"
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    elif provider == "openrouter":
        model_name = model_name or "openai/gpt-4o-mini"
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    else:
        provider = "custom"
        model_name = model_name or os.getenv("CUSTOM_MODEL", "deepseek-v4-flash")
        api_key = os.getenv("CUSTOM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("CUSTOM_BASE_URL", "https://api.deepseek.com")

    judge_provider = normalize_provider(os.getenv("JUDGE_PROVIDER", provider))
    judge_model_name = os.getenv("JUDGE_MODEL", model_name)
    judge_api_key = os.getenv("JUDGE_API_KEY", api_key or "")
    judge_base_url = os.getenv("JUDGE_BASE_URL", base_url or "")

    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    return LabConfig(
        base_dir=root,
        data_dir=root / "data",
        state_dir=state_dir,
        compact_threshold_tokens=int(os.getenv("COMPACT_THRESHOLD_TOKENS", "700")),
        compact_keep_messages=int(os.getenv("COMPACT_KEEP_MESSAGES", "6")),
        model=ProviderConfig(
            provider=provider,
            model_name=model_name,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
            api_key=api_key,
            base_url=base_url,
        ),
        judge_model=ProviderConfig(
            provider=judge_provider,
            model_name=judge_model_name,
            temperature=float(os.getenv("JUDGE_TEMPERATURE", "0")),
            api_key=judge_api_key or None,
            base_url=judge_base_url or None,
        ),
    )
