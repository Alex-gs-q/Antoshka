from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any, Dict, Optional

from core.logger import setup_logger


class SafetyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    NEED_CONFIRM = "need_confirm"


@dataclass
class SafetyResult:
    decision: SafetyDecision
    reason: str


@dataclass
class Action:
    """
    Единый формат "что мы собираемся сделать".
    type: тип действия (open_url/open_path/run_app/close_app/delete_file/...)
    payload: параметры (url/path/app_name/etc)
    """
    type: str
    payload: Dict[str, Any]


class SafetyGate:
    def __init__(
        self,
        dangerous_mode: bool = False,
        confirm_phrase: str = "подтверждаю",
        confirm_ttl_seconds: int = 10,
    ):
        self.logger = setup_logger()
        self.dangerous_mode = dangerous_mode
        self.confirm_phrase = confirm_phrase.strip().lower()
        self.confirm_ttl_seconds = int(confirm_ttl_seconds)
        self._confirm_until_ts: float = 0.0

        # Жёсткий запрет (никогда в MVP)
        self.deny_types = {
            "delete_file",
            "format_disk",
            "kill_process",
            "edit_registry",
            "download_and_run_exe",
        }

        # Требует подтверждение
        self.need_confirm_types = {
            "close_app",
            "open_system_folder",
        }

        # Белый список разрешённых действий в safe режиме
        self.allow_types = {
            "help",
            "time",
            "date",
            "greet",
            "exit",
            "open_url",
            "open_path",
            "run_app",
        }

    def confirm(self, phrase: str) -> bool:
        """Пользователь сказал фразу подтверждения."""
        p = (phrase or "").strip().lower()
        if p == self.confirm_phrase:
            self._confirm_until_ts = time() + self.confirm_ttl_seconds
            self.logger.info("Safety confirm accepted, ttl=%ss", self.confirm_ttl_seconds)
            return True
        self.logger.info("Safety confirm rejected, phrase=%s", p)
        return False

    def _has_valid_confirm(self) -> bool:
        return time() <= self._confirm_until_ts

    def check(self, action: Action) -> SafetyResult:
        """
        Вернёт решение безопасности.
        """
        a_type = action.type

        # 1) Жёсткий deny
        if a_type in self.deny_types:
            self.logger.warning("Safety DENY action=%s payload=%s", a_type, action.payload)
            return SafetyResult(SafetyDecision.DENY, "Запрещено политикой безопасности")

        # 2) Неизвестный тип — запрещаем (fail-closed)
        if a_type not in self.allow_types and a_type not in self.need_confirm_types:
            self.logger.warning("Safety DENY unknown action=%s payload=%s", a_type, action.payload)
            return SafetyResult(SafetyDecision.DENY, "Неизвестное действие")

        # 3) Если dangerous_mode включён — можно больше (в MVP пока просто логика)
        if self.dangerous_mode:
            self.logger.info("Safety ALLOW (dangerous_mode) action=%s payload=%s", a_type, action.payload)
            return SafetyResult(SafetyDecision.ALLOW, "dangerous_mode=true")

        # 4) Нужна явная конфирма
        if a_type in self.need_confirm_types:
            if self._has_valid_confirm():
                self.logger.info("Safety ALLOW (confirmed) action=%s payload=%s", a_type, action.payload)
                return SafetyResult(SafetyDecision.ALLOW, "Подтверждено пользователем")
            self.logger.info("Safety NEED_CONFIRM action=%s payload=%s", a_type, action.payload)
            return SafetyResult(SafetyDecision.NEED_CONFIRM, "Нужно подтверждение: скажи 'подтверждаю'")

        # 5) Обычные разрешённые действия
        self.logger.info("Safety ALLOW action=%s payload=%s", a_type, action.payload)
        return SafetyResult(SafetyDecision.ALLOW, "Разрешено")
