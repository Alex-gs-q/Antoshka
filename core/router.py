from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Union

from commands.builtins import create_registry
from commands.registry import CommandContext, CommandRegistry
from core.actions import ActionResult
from core.logger import setup_logger
from core.nlu_rules import detect_intent
from core.text_norm import normalize_text

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

    def route(self, text: str) -> Optional[RouteResult]:
        if not text:
            return None
        cleaned = _WAKE_RE.sub("", text).strip()
        normalized = normalize_text(cleaned)

        match = self.registry.match(normalized)
        if match:
            self.log.info("Route matched: %s slots=%s", match.command.name, match.slots)
            return RouteResult(
                name=match.command.name, slots=match.slots, source="rules"
            )

        res = detect_intent(cleaned)
        if res.intent != "unknown":
            return RouteResult(name=res.intent, slots=res.slots, source="nlu")

        return None

    def run(self, name: str, raw_text: str, slots: Dict[str, str]) -> Union[str, ActionResult]:
        cmd = self.registry.get(name)
        if not cmd:
            return "Unknown command."
        ctx = CommandContext(text=raw_text, slots=slots, app_context=self.app_context)
        return cmd.handler(ctx)
