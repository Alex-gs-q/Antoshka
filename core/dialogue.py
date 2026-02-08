from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pathlib import Path

from core.app_context import AppContext
from core.logger import setup_logger
from core.router import CommandRouter
from core.safety import SafetyGate, Action
from llm.client import LLMClient
from services.scheduler import Scheduler
from services.history import append_history


@dataclass(frozen=True)
class DialogueConfig:
    dangerous_mode: bool = False
    llm_client: Optional[LLMClient] = None
    app_context: Optional[AppContext] = None


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

    def handle_text(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        append_history(self.app_context.data_dir, "user", text)

        # 1) подтверждение SafetyGate (если пользователь сказал "подтверждаю")
        self.safety.confirm(text)

        # 2) Router
        route = self.router.route(text)

        # 3) если не поняли — LLM tool-calling, затем fallback
        if route is None:
            if self.config.llm_client is not None:
                self.log.info("Router unknown -> LLM tool-calling")
                tools = self.router.registry.as_tools()
                tool_call = self.config.llm_client.call_with_tools(text, tools)
                if tool_call:
                    name, slots = tool_call
                    action = Action(name, slots)
                    decision = self.safety.check(action)
                    if decision.decision.value == "deny":
                        answer = f"Запрещено: {decision.reason}"
                    elif decision.decision.value == "need_confirm":
                        answer = decision.reason
                    else:
                        answer = self.router.run(name, text, slots)
                    append_history(self.app_context.data_dir, "assistant", answer)
                    return answer

                self.log.info("LLM tool-calling unavailable -> text fallback")
                answer = self.config.llm_client.ask(text)
                append_history(self.app_context.data_dir, "assistant", answer)
                return answer

            answer = "Не понял команду. Скажи 'помощь'."
            append_history(self.app_context.data_dir, "assistant", answer)
            return answer

        # 4) маппим intent -> действие (в SafetyGate)
        action = Action(route.name, route.slots)

        decision = self.safety.check(action)
        if decision.decision.value == "deny":
            return f"Запрещено: {decision.reason}"
        if decision.decision.value == "need_confirm":
            return decision.reason

        # 5) запускаем скилл
        out = self.router.run(route.name, text, route.slots)

        # 6) exit как специальный маркер
        if out == "__EXIT__":
            return "__EXIT__"

        append_history(self.app_context.data_dir, "assistant", out)
        return out
