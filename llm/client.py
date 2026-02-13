from __future__ import annotations

import os
import json
import time
import random
import threading
from dataclasses import dataclass
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
        self.api_key = ""
        self._in_flight = threading.Lock()
        self._tools_enabled = True
        provider_env = os.getenv("ANTOSHKA_LLM_PROVIDER", "").strip().lower()
        model_env = os.getenv("ANTOSHKA_LLM_MODEL", "").strip()
        base_provider = (self.config.provider or "dummy").strip().lower()
        if provider_env and base_provider != "dummy":
            self.provider = provider_env
        else:
            self.provider = base_provider
        self.model = model_env or self.config.model
        self.base_url = self.config.base_url

        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is missing in .env")

            if not self.api_key.isascii():
                raise RuntimeError("OPENAI_API_KEY contains non-ASCII characters")
            if "..." in self.api_key or "твой" in self.api_key.lower():
                raise RuntimeError("OPENAI_API_KEY looks like a placeholder")

            self.base_url = (
                os.getenv("OPENAI_BASE_URL", self.config.base_url).strip().rstrip("/")
            )
            if not self.base_url:
                raise RuntimeError("OPENAI_BASE_URL is empty")
            if not self.base_url.isascii():
                raise RuntimeError("OPENAI_BASE_URL contains non-ASCII characters")

            self.log.info("OpenAI enabled")
            self.log.info("LLM initialized (openai), model=%s", self.model)
        else:
            self.log.info("LLM initialized (dummy)")

    def status(self) -> Dict[str, Any]:
        provider = self.provider
        ok = provider == "openai" and bool(self.api_key)
        reason = ""
        if provider == "dummy":
            reason = "provider=dummy"
        if provider != "dummy" and not self.api_key:
            reason = "missing_api_key"
        return {
            "provider": provider,
            "model": self.model,
            "base_url": self.base_url,
            "ok": ok,
            "reason": reason,
        }

    def test_connection(self) -> Tuple[bool, str]:
        if self.provider != "openai":
            return False, "provider_dummy"
        if not self.api_key:
            return False, "missing_api_key"

        url = f"{self.base_url}/responses"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT_RU,
            "input": _build_input_messages("ping"),
            "max_output_tokens": 16,
        }

        try:
            data = self._post_with_retry(url, headers, payload)
            if data:
                return True, "ok"
            return False, "error"
        except LLMError as e:
            if e.kind == "rate_limit":
                if e.retry_after:
                    return False, f"rate_limit:{e.retry_after}"
                return False, "rate_limit"
            if e.kind == "quota":
                return False, "quota"
            if e.status:
                return False, f"http_{e.status}"
            if e.kind == "network":
                return False, "network"
            return False, "error"

    def reset_history(self) -> None:
        self.history = []

    def ask(self, user_text: str) -> str:
        user_text = (user_text or "").strip()
        if not user_text:
            return ""

        if self.provider == "dummy":
            return (
                "Сейчас ИИ отключен (provider=dummy). "
                "Чтобы включить — задай OPENAI_API_KEY в .env и поставь llm.provider=openai."
            )

        if self.provider != "openai":
            return f"Неизвестный LLM provider: {self.provider}"

        if not self._in_flight.acquire(blocking=False):
            raise LLMBusyError("llm_busy")
        try:
            self.history.append({"role": "user", "content": user_text})
            self._trim_history()
            answer = self._ask_openai_responses(user_text)
            self.history.append({"role": "assistant", "content": answer})
            self._trim_history()
            return answer
        finally:
            self._in_flight.release()

    def is_busy(self) -> bool:
        return self._in_flight.locked()

    def call_with_tools(
        self, user_text: str, tools: List[Dict[str, Any]]
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        user_text = (user_text or "").strip()
        if not user_text:
            return None

        if self.provider == "dummy":
            return None
        if self.provider != "openai":
            return None
        if not self._tools_enabled:
            return None

        if not self._in_flight.acquire(blocking=False):
            raise LLMBusyError("llm_busy")
        try:
            return self._ask_openai_tool_call(user_text, tools)
        except LLMError as e:
            if e.status == 400:
                self._tools_enabled = False
                self.log.warning("Tool-calling disabled for this session due to 400 Bad Request")
                return None
            raise
        finally:
            self._in_flight.release()

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

        payload = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT_RU,
            "input": _build_input_messages(user_text),
        }

        data = self._post_with_retry(url, headers, payload)

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

        payload = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT_RU,
            "input": _build_input_messages(user_text),
            "tools": tools,
            "tool_choice": "auto",
        }

        data = self._post_with_retry(url, headers, payload)

        output = data.get("output", [])
        for item in output:
            if item.get("type") in {"function_call", "tool_call"}:
                name = item.get("name") or item.get("function", {}).get("name")
                arguments = (
                    item.get("arguments")
                    or item.get("function", {}).get("arguments")
                    or {}
                )
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                if name:
                    return name, arguments

        return None

    def _post_with_retry(self, url: str, headers: dict, payload: dict) -> dict:
        max_attempts = 3
        backoff_base = 1.0
        max_wait_seconds = 8.0
        start_ts = time.monotonic()
        last_err: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds) as client:
                    r = client.post(url, headers=headers, json=payload)
                    r.raise_for_status()
                    return r.json()
            except httpx.HTTPStatusError as e:
                last_err = e
                info = _extract_error_info(e)
                self._log_http_error(info)
                status = info.status or e.response.status_code
                retry_after = info.retry_after
                if status == 429:
                    if info.kind == "quota":
                        raise info.to_error()
                    elapsed = time.monotonic() - start_ts
                    if elapsed >= max_wait_seconds:
                        raise info.to_error()
                    if attempt < max_attempts:
                        base = backoff_base * (2 ** (attempt - 1))
                        jitter = random.uniform(0.0, 0.5)
                        delay = min(max_wait_seconds - elapsed, base + jitter)
                        wait_hint = retry_after or delay
                        self.log.warning(
                            "LLM retry %s/%s after %ss (status=429)",
                            attempt,
                            max_attempts,
                            round(wait_hint, 2),
                        )
                        time.sleep(delay)
                        continue
                    raise info.to_error()
                if status in {500, 502, 503, 504} and attempt < max_attempts:
                    delay = backoff_base * (2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
                    self.log.warning(
                        "LLM retry %s/%s after %ss (status=%s)",
                        attempt,
                        max_attempts,
                        round(delay, 2),
                        status,
                    )
                    time.sleep(delay)
                    continue
                raise info.to_error()
            except Exception as e:  # noqa: BLE001
                last_err = e
                raise LLMError(kind="network", message=str(e))
        if last_err:
            raise LLMError(kind="error", message=str(last_err))
        raise RuntimeError("LLM request failed")

    def _log_http_error(self, info: "_ErrorInfo") -> None:
        self.log.warning(
            "OpenAI error status=%s request_id=%s type=%s code=%s param=%s message=%s",
            info.status,
            info.request_id,
            info.error_type,
            info.error_code,
            info.error_param,
            info.error_message,
        )


class LLMBusyError(Exception):
    pass


@dataclass(frozen=True)
class LLMError(Exception):
    kind: str
    message: str = ""
    status: int | None = None
    error_type: str | None = None
    error_code: str | None = None
    error_param: str | None = None
    request_id: str | None = None
    retry_after: float | None = None


@dataclass(frozen=True)
class _ErrorInfo:
    kind: str
    status: int | None
    error_type: str | None
    error_code: str | None
    error_param: str | None
    error_message: str | None
    request_id: str | None
    retry_after: float | None

    def to_error(self) -> LLMError:
        return LLMError(
            kind=self.kind,
            message=self.error_message or "",
            status=self.status,
            error_type=self.error_type,
            error_code=self.error_code,
            error_param=self.error_param,
            request_id=self.request_id,
            retry_after=self.retry_after,
        )


def _build_input_messages(text: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        }
    ]


def _classify_error(kind_hint: str | None, code: str | None, status: int | None) -> str:
    if status == 429:
        if code in {"insufficient_quota", "quota_exceeded", "billing_hard_limit_reached"}:
            return "quota"
        if kind_hint in {"insufficient_quota"}:
            return "quota"
        return "rate_limit"
    if status == 400:
        return "bad_request"
    if status == 401:
        return "unauthorized"
    if status == 403:
        return "forbidden"
    if status == 402:
        return "quota"
    return "http_error"


def _extract_error_info(err: httpx.HTTPStatusError) -> _ErrorInfo:
    status = err.response.status_code
    request_id = err.response.headers.get("x-request-id") or err.response.headers.get("X-Request-Id")
    retry_after = None
    ra = err.response.headers.get("retry-after")
    if ra:
        try:
            retry_after = float(ra)
        except ValueError:
            retry_after = None
    error_type = None
    error_code = None
    error_param = None
    error_message = None
    try:
        payload = err.response.json()
        if isinstance(payload, dict):
            err_obj = payload.get("error") or {}
            if isinstance(err_obj, dict):
                error_message = err_obj.get("message")
                error_type = err_obj.get("type")
                error_code = err_obj.get("code")
                error_param = err_obj.get("param")
    except Exception:
        pass
    kind = _classify_error(error_type, error_code, status)
    return _ErrorInfo(
        kind=kind,
        status=status,
        error_type=error_type,
        error_code=error_code,
        error_param=error_param,
        error_message=error_message,
        request_id=request_id,
        retry_after=retry_after,
    )
