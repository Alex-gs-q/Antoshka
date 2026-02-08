from __future__ import annotations

import os
from dataclasses import dataclass
import json
from typing import Optional, List, Dict, Any, Tuple

import httpx
from dotenv import load_dotenv

from core.logger import setup_logger
from llm.prompts import SYSTEM_PROMPT_RU


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "dummy"  # "dummy" | "openai"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 30.0
    history_max_messages: int = 10


class LLMClient:
    """
    MVP LLM client:
    - dummy provider (заглушка)
    - openai provider через Responses API
    - хранит историю (короткую), чтобы потом было легче расширять
    """

    def __init__(self, config: LLMConfig):
        self.log = setup_logger()
        self.config = config

        load_dotenv()

        self.history: List[Dict[str, Any]] = []

        if self.config.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY", "")
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is missing in .env")

            if not self.api_key.isascii():
                raise RuntimeError("OPENAI_API_KEY contains non-ASCII characters")

            self.base_url = os.getenv("OPENAI_BASE_URL", self.config.base_url).rstrip("/")
            if not self.base_url.isascii():
                raise RuntimeError("OPENAI_BASE_URL contains non-ASCII characters")

            self.log.info("LLM initialized (openai), model=%s", self.config.model)
        else:
            self.api_key = ""
            self.base_url = self.config.base_url
            self.log.info("LLM initialized (dummy)")

    def reset_history(self) -> None:
        self.history = []

    def ask(self, user_text: str) -> str:
        user_text = (user_text or "").strip()
        if not user_text:
            return ""

        if self.config.provider == "dummy":
            return (
                "Сейчас ИИ отключен (provider=dummy). "
                "Чтобы включить — задай OPENAI_API_KEY в .env и поставь llm.provider=openai."
            )

        if self.config.provider != "openai":
            return f"Неизвестный LLM provider: {self.config.provider}"

        self.history.append({"role": "user", "content": user_text})
        self._trim_history()

        try:
            answer = self._ask_openai_responses(user_text)
        except Exception as e:
            self.log.error("LLM request failed: %s", e)
            return "Извини, сейчас не могу ответить (LLM недоступен)."

        self.history.append({"role": "assistant", "content": answer})
        self._trim_history()

        return answer

    def call_with_tools(self, user_text: str, tools: List[Dict[str, Any]]) -> Optional[Tuple[str, Dict[str, Any]]]:
        user_text = (user_text or "").strip()
        if not user_text:
            return None

        if self.config.provider == "dummy":
            return None
        if self.config.provider != "openai":
            return None

        try:
            return self._ask_openai_tool_call(user_text, tools)
        except Exception as e:
            self.log.error("LLM tool call failed: %s", e)
            return None

    def _trim_history(self) -> None:
        max_n = max(0, int(self.config.history_max_messages))
        if max_n and len(self.history) > max_n:
            self.history = self.history[-max_n:]

    def _ask_openai_responses(self, user_text: str) -> str:
        """
        POST /v1/responses
        Вытаскиваем текст из output[].content[].text
        """
        url = f"{self.base_url}/responses"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for k, v in headers.items():
            if not v.isascii():
                raise RuntimeError(f"Header {k} contains non-ASCII characters")

        payload = {
            "model": self.config.model,
            "instructions": SYSTEM_PROMPT_RU,
            "input": user_text,
        }

        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        output = data.get("output", [])
        for item in output:
            if item.get("type") == "message" and item.get("role") == "assistant":
                content = item.get("content", [])
                for part in content:
                    if part.get("type") == "output_text":
                        return part.get("text", "").strip()

        return ""

    def _ask_openai_tool_call(
        self, user_text: str, tools: List[Dict[str, Any]]
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        url = f"{self.base_url}/responses"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for k, v in headers.items():
            if not v.isascii():
                raise RuntimeError(f"Header {k} contains non-ASCII characters")

        payload = {
            "model": self.config.model,
            "instructions": SYSTEM_PROMPT_RU,
            "input": user_text,
            "tools": tools,
            "tool_choice": "auto",
        }

        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        output = data.get("output", [])
        for item in output:
            if item.get("type") in {"function_call", "tool_call"}:
                name = item.get("name") or item.get("function", {}).get("name")
                arguments = item.get("arguments") or item.get("function", {}).get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                if name:
                    return name, arguments

        return None
