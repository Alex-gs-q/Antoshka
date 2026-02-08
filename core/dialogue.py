from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import setup_logger
from core.nlu_rules import detect_intent, NLUResult
from core.safety import Action, SafetyDecision, SafetyGate
from skills.registry import get_handler


@dataclass
class DialogueConfig:
    dangerous_mode: bool = False


class Dialogue:
    def __init__(self, cfg: DialogueConfig):
        self.logger = setup_logger()
        self.safety = SafetyGate(dangerous_mode=cfg.dangerous_mode)

    def _intent_to_action(self, nlu: NLUResult) -> Optional[Action]:
        """
        Превращаем intent+slots в Action для SafetyGate.
        Для "разговорных" интентов action тоже есть (ALLOW),
        чтобы всё было единообразно и логировалось.
        """
        if nlu.intent == "open_url":
            return Action("open_url", {"url": nlu.slots.get("url")})
        if nlu.intent == "open_path":
            return Action("open_path", {"path": nlu.slots.get("path")})
        if nlu.intent == "exit":
            return Action("exit", {})
        if nlu.intent in {"help", "greet", "time", "date"}:
            return Action(nlu.intent, {})
        return None

    def handle_text(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "Скажи команду или 'помощь'."

        # 1) Подтверждение опасных действий
        if self.safety.confirm(text):
            return "Ок, подтверждение принято. Повтори команду."

        # 2) NLU
        nlu = detect_intent(text)
        if not nlu:
            return "Не понял команду. Скажи 'помощь'."

        # 3) SafetyGate
        action = self._intent_to_action(nlu)
        if action:
            sr = self.safety.check(action)
            if sr.decision == SafetyDecision.DENY:
                return f"Запрещено: {sr.reason}"
            if sr.decision == SafetyDecision.NEED_CONFIRM:
                return sr.reason

        # 4) Skills
        handler = get_handler(nlu.intent)
        if not handler:
            return "Команда распознана, но пока не реализована."

        result = handler(nlu.slots)
        return result
