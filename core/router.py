from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Union

from commands.builtins import create_registry
from commands.registry import CommandContext, CommandRegistry
from core.actions import ActionResult
from core.logger import setup_logger
from core.nlu_rules import detect_intent

_WAKE_RE = re.compile(r"^\s*antoshka[\s,]*", flags=re.IGNORECASE | re.UNICODE)


@dataclass(frozen=True)
class RouteResult:
    name: str
    slots: Dict[str, str]
    source: str


class CommandRouter:
    def __init__(self, app_context):
        self.log = setup_logger()
        self.registry: CommandRegistry = create_registry()
        self.app_context = app_context
        self.app_context.registry = self.registry

    def route(self, text: str, lang: str | None = None) -> Optional[RouteResult]:
        if not text:
            return None
        cleaned = _WAKE_RE.sub("", text).strip()
        match = self.registry.match(cleaned)
        if match:
            self.log.info("Route matched: %s slots=%s", match.command.name, match.slots)
            return RouteResult(
                name=match.command.name, slots=match.slots, source="rules"
            )

        lang = lang or getattr(self.app_context, "language", "ru")
        res = detect_intent(cleaned, lang=lang)
        if res.intent != "unknown":
            return RouteResult(name=res.intent, slots=res.slots, source="nlu")

        return None

    def run(self, name: str, raw_text: str, slots: Dict[str, str]) -> Union[str, ActionResult]:
        cmd = self.registry.get(name)
        if not cmd:
            return "Unknown command."
        ctx = CommandContext(text=raw_text, slots=slots, app_context=self.app_context)
        self.log.info("Handler start: %s slots=%s", name, slots)
        out = cmd.handler(ctx)
        self.log.info("Handler done: %s", name)
        return out
