from __future__ import annotations

import sys
from pathlib import Path

# чтобы работало и так:
# python tools/llm_smoke_test.py
# и так:
# python -m tools.llm_smoke_test
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_settings
from core.logger import setup_logger
from llm.client import LLMClient, LLMConfig


def main() -> None:
    log = setup_logger()
    settings = load_settings()

    llm_raw = settings.get("llm", {}) or {}
    provider = llm_raw.get("provider", "dummy")
    model = llm_raw.get("model", "gpt-4o-mini")

    # можно также переключать через .env:
    # ANTOSHKA_LLM_PROVIDER=openai
    # но тут берём из settings.json, чтобы было явно
    cfg = LLMConfig(
        provider=str(provider),
        model=str(model),
        history_max_messages=int(llm_raw.get("history_max_messages", 10)),
    )

    client = LLMClient(cfg)

    print(">>> Asking LLM...")
    answer = client.ask("Привет! Скажи одним предложением кто ты.")
    print("<<< Answer:")
    print(answer)


if __name__ == "__main__":
    main()
