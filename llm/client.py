"""Thin wrapper for OpenAI chat API used by eval scripts.

Environment: ``OPENAI_API_KEY`` with optional ``.env`` at repo root.
Override temperature and max output tokens with ``LLM_TEMPERATURE`` and
``LLM_MAX_OUTPUT_TOKENS``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover

    # load dotenv
    def load_dotenv(*_a, **_k):
        return False


Provider = Literal["openai"]


@dataclass
class LLMConfig:
    provider: Provider
    model: str


# env provider
def _env_provider() -> Provider:
    return "openai"


# load llm config
def load_llm_config(path: Path | None) -> LLMConfig:
    """Load ``llm.provider`` and ``llm.model`` from YAML, or fall back to env."""
    # missing yaml → env-only (handy for quick runs with just OPENAI_API_KEY)
    if path is None or not path.exists():
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        return LLMConfig(provider=_env_provider(), model=model)
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    llm = data.get("llm", {})
    return LLMConfig(provider="openai", model=llm.get("model", "gpt-4o-mini"))


# chat text
def chat_text(system: str, user: str, cfg: LLMConfig) -> str:
    """Single-turn chat completion; returns assistant text (stripped)."""
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")
    from openai import OpenAI

    client = OpenAI()
    max_tokens = int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "4096"))
    # GPT-5 family rejects legacy max_tokens; use max_completion_tokens instead.
    cap_kw = (
        {"max_completion_tokens": max_tokens}
        if cfg.model.startswith("gpt-5")
        else {"max_tokens": max_tokens}
    )
    r = client.chat.completions.create(
        model=cfg.model,
        temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **cap_kw,
    )
    return (r.choices[0].message.content or "").strip()
