from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.app_context import AppContext
from core.actions import ActionResult
from core.i18n import t as tr
from core.logger import setup_logger
from core.router import CommandRouter
from core.safety import SafetyGate, Action
from llm.client import LLMClient, LLMError, LLMBusyError
from services.scheduler import Scheduler
from services.history import append_history
from services.text.num_normalize import normalize_numbers
from core.paths import data_dir
from core.text_norm import normalize_text


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
                data_dir=data_dir(),
                scheduler=Scheduler(notify=lambda _: None),
                volume=None,
                llm_client=config.llm_client,
            )
        else:
            self.app_context = config.app_context
        self.router = CommandRouter(self.app_context)
        self._pending_action: Action | None = None
        self._pending_lang: str | None = None

    def handle_text(
        self,
        text: str,
        language: str | None = None,
        allow_llm: bool = True,
    ) -> str | ActionResult:
        raw_text = (text or "").strip()
        if not raw_text:
            return ""

        append_history(self.app_context.data_dir, "user", raw_text)

        # 1) подтверждение SafetyGate
        lang = language or getattr(self.app_context, "language", None)
        self.log.info("Dialogue input: len=%s lang=%s", len(raw_text), lang)
        confirmed = self.safety.confirm(raw_text)
        if confirmed:
            if self._pending_action is not None:
                action = self._pending_action
                self._pending_action = None
                out = self.router.run(action.type, raw_text, action.payload)
                self.log.info("Dialogue confirmed action: %s", action.type)
                append_history(self.app_context.data_dir, "assistant", _as_text(out))
                return out
            return tr("safety_confirmed", lang or "ru")

        norm_text = normalize_text(raw_text)
        normalized_text = normalize_numbers(norm_text, lang or "auto")
        if normalized_text != raw_text:
            self.log.info("Text normalized: '%s' -> '%s'", raw_text, normalized_text)

        # 2) Router
        route = self.router.route(normalized_text, lang=lang)
        if route is not None:
            self.log.info("Dialogue route: %s source=%s", route.name, route.source)
        else:
            self.log.info("Dialogue route: unknown")

        # 3) если не поняли — LLM tool-calling, затем fallback
        if route is None:
            if allow_llm and self.config.llm_client is not None:
                self.log.info("Router unknown -> LLM tool-calling")
                tools = self.router.registry.as_tools()
                try:
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
                except LLMBusyError:
                    return tr("msg_ai_busy", lang or "ru")
                except LLMError as e:
                    return _llm_error_to_text(e, lang or "ru")

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
        self.log.info("Dialogue action: %s", route.name)
        out = self.router.run(route.name, normalized_text, route.slots)
        if isinstance(out, ActionResult):
            self.log.info("Dialogue result: action=%s status=%s", out.action, out.status)
        else:
            self.log.info("Dialogue result: text_len=%s", len(str(out)))

        # 6) exit как специальный маркер
        if out == "__EXIT__":
            return "__EXIT__"

        append_history(self.app_context.data_dir, "assistant", _as_text(out))
        return out


def _llm_error_to_text(err: LLMError, lang: str) -> str:
    if err.kind == "quota":
        return tr("msg_ai_quota", lang)
    if err.kind == "rate_limit":
        if err.retry_after:
            return tr("msg_ai_rate_limit_wait", lang).format(seconds=int(err.retry_after))
        return tr("msg_ai_rate_limit", lang)
    if err.kind == "unauthorized":
        return tr("msg_ai_check_401", lang)
    if err.kind == "forbidden":
        return tr("msg_ai_check_403", lang)
    if err.kind == "network":
        return tr("msg_ai_check_network", lang)
    return tr("msg_ai_check_error", lang)
