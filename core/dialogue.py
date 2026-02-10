from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pathlib import Path

from core.app_context import AppContext
from core.actions import ActionResult
from core.i18n import t as tr
from core.logger import setup_logger
from core.router import CommandRouter
from core.safety import SafetyGate, Action
from llm.client import LLMClient
from services.scheduler import Scheduler
from services.history import append_history
from services.text.num_normalize import normalize_numbers


@dataclass(frozen=True)
class DialogueConfig:
    dangerous_mode: bool = False
    llm_client: Optional[LLMClient] = None
    app_context: Optional[AppContext] = None


def _as_text(answer: str | ActionResult) -> str:
    if isinstance(answer, ActionResult):
        return answer.to_text()
    return answer


class Dialogue:
    def __init__(self, config: DialogueConfig):
        self.log = setup_logger()
        self.config = config
        self.safety = SafetyGate(dangerous_mode=config.dangerous_mode)
        if config.app_context is None:
            self.app_context = AppContext(
                notify=lambda _: None,
                data_dir=Path("data"),
                scheduler=Scheduler(notify=lambda _: None),
                volume=None,
                llm_client=config.llm_client,
            )
        else:
            self.app_context = config.app_context
        self.router = CommandRouter(self.app_context)
        self._pending_action: Action | None = None
        self._pending_lang: str | None = None

    def handle_text(self, text: str, language: str | None = None) -> str | ActionResult:
        raw_text = (text or "").strip()
        if not raw_text:
            return ""

        append_history(self.app_context.data_dir, "user", raw_text)

        # 1) подтверждение SafetyGate
        lang = language or getattr(self.app_context, "language", None)
        confirmed = self.safety.confirm(raw_text)
        if confirmed:
            if self._pending_action is not None:
                action = self._pending_action
                self._pending_action = None
                out = self.router.run(action.type, raw_text, action.payload)
                append_history(self.app_context.data_dir, "assistant", _as_text(out))
                return out
            return tr("safety_confirmed", lang or "ru")

        normalized_text = normalize_numbers(raw_text, lang or "auto")
        if normalized_text != raw_text:
            self.log.info("Numbers normalized: '%s' -> '%s'", raw_text, normalized_text)

        # 2) Router
        route = self.router.route(normalized_text, lang=lang)

        # 3) если не поняли — LLM tool-calling, затем fallback
        if route is None:
            if self.config.llm_client is not None:
                self.log.info("Router unknown -> LLM tool-calling")
                tools = self.router.registry.as_tools()
                tool_call = self.config.llm_client.call_with_tools(raw_text, tools)
                if tool_call:
                    name, slots = tool_call
                    action = Action(name, slots)
                    decision = self.safety.check(action)
                    if decision.decision.value == "deny":
                        answer = tr("safety_denied", lang or "ru")
                    elif decision.decision.value == "need_confirm":
                        answer = tr("safety_need_confirm", lang or "ru")
                    else:
                        answer = self.router.run(name, normalized_text, slots)
                    append_history(self.app_context.data_dir, "assistant", _as_text(answer))
                    return answer

                self.log.info("LLM tool-calling unavailable -> text fallback")
                answer = self.config.llm_client.ask(raw_text)
                append_history(self.app_context.data_dir, "assistant", _as_text(answer))
                return answer

            lang = language or getattr(self.app_context, "language", "ru")
            answer = tr("msg_unknown_command", lang)
            append_history(self.app_context.data_dir, "assistant", _as_text(answer))
            return answer

        # 4) маппим intent -> действие (в SafetyGate)
        action = Action(route.name, route.slots)

        decision = self.safety.check(action)
        if decision.decision.value == "deny":
            return tr("safety_denied", lang or "ru")
        if decision.decision.value == "need_confirm":
            self._pending_action = action
            self._pending_lang = lang
            return tr("safety_need_confirm", lang or "ru")

        # 5) запускаем скилл
        out = self.router.run(route.name, normalized_text, route.slots)

        # 6) exit как специальный маркер
        if out == "__EXIT__":
            return "__EXIT__"

        append_history(self.app_context.data_dir, "assistant", out)
        return out
