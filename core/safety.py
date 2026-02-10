from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any, Dict

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

        self.deny_types = {
            "delete_file",
            "format_disk",
            "kill_process",
            "edit_registry",
            "download_and_run_exe",
        }

        self.need_confirm_types = {
            "close_app",
            "open_system_folder",
            "note_delete",
        }

        self.allow_types = {
            "help",
            "time",
            "date",
            "greet",
            "exit",
            "open_url",
            "open_path",
            "run_app",
            "open_app",
            "open_mail",
            "open_calendar",
            "search_web",
            "weather",
            "note_create",
            "timer_set",
            "reminder_set",
            "volume_set",
            "chat",
            "tts_test",
            "note_list",
            "note_delete",
            "note_update",
            "note_replace",
            "alarm_set",
            "open_map",
            "screenshot",
            "settings_wake",
            "settings_tts",
            "settings_language",
            "settings_theme",
            "settings_accent",
            "settings_bg_intensity",
            "settings_tts_rate",
            "settings_tts_volume",
            "clear_chat",
            "event_add",
            "event_list",
        }

    def confirm(self, phrase: str) -> bool:
        """Пользователь сказал фразу подтверждения."""
        p = (phrase or "").strip().lower()
        if p in {self.confirm_phrase, "подтверждаю", "confirm"}:
            self._confirm_until_ts = time() + self.confirm_ttl_seconds
            self.logger.info(
                "Safety confirm accepted, ttl=%ss", self.confirm_ttl_seconds
            )
            return True
        self.logger.info("Safety confirm rejected, phrase=%s", p)
        return False

    def _has_valid_confirm(self) -> bool:
        return time() <= self._confirm_until_ts

    def check(self, action: Action) -> SafetyResult:
        """Возвращает решение безопасности."""
        a_type = action.type

        if a_type in self.deny_types:
            self.logger.warning(
                "Safety DENY action=%s payload=%s", a_type, action.payload
            )
            return SafetyResult(SafetyDecision.DENY, "blocked")

        if a_type not in self.allow_types and a_type not in self.need_confirm_types:
            self.logger.warning(
                "Safety DENY unknown action=%s payload=%s", a_type, action.payload
            )
            return SafetyResult(SafetyDecision.DENY, "unknown")

        if self.dangerous_mode:
            self.logger.info(
                "Safety ALLOW (dangerous_mode) action=%s payload=%s",
                a_type,
                action.payload,
            )
            return SafetyResult(SafetyDecision.ALLOW, "dangerous_mode")

        if a_type in self.need_confirm_types:
            if self._has_valid_confirm():
                self.logger.info(
                    "Safety ALLOW (confirmed) action=%s payload=%s",
                    a_type,
                    action.payload,
                )
                return SafetyResult(SafetyDecision.ALLOW, "confirmed")
            self.logger.info(
                "Safety NEED_CONFIRM action=%s payload=%s", a_type, action.payload
            )
            return SafetyResult(SafetyDecision.NEED_CONFIRM, "need_confirm")

        self.logger.info("Safety ALLOW action=%s payload=%s", a_type, action.payload)
        return SafetyResult(SafetyDecision.ALLOW, "allowed")
