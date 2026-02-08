from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Pattern


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    patterns: List[Pattern[str]]
    parameters_schema: Dict[str, str]
    handler: Callable[["CommandContext"], str]

    def json_schema(self) -> Dict[str, Any]:
        props = {k: {"type": "string"} for k in self.parameters_schema.keys()}
        required = [k for k, v in self.parameters_schema.items() if v != "optional"]
        return {"type": "object", "properties": props, "required": required}


@dataclass(frozen=True)
class MatchResult:
    command: Command
    slots: Dict[str, Any]
    confidence: float


@dataclass(frozen=True)
class CommandContext:
    text: str
    slots: Dict[str, Any]
    app_context: Any


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: List[Command] = []

    def register(self, command: Command) -> None:
        self._commands.append(command)

    def all(self) -> List[Command]:
        return list(self._commands)

    def get(self, name: str) -> Optional[Command]:
        for cmd in self._commands:
            if cmd.name == name:
                return cmd
        return None

    def as_tools(self) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = []
        for cmd in self._commands:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": cmd.name,
                        "description": cmd.description,
                        "parameters": cmd.json_schema(),
                    },
                }
            )
        return tools

    def match(self, text: str) -> Optional[MatchResult]:
        for cmd in self._commands:
            for pattern in cmd.patterns:
                m = pattern.search(text)
                if not m:
                    continue
                slots = {k: v for k, v in m.groupdict().items() if v is not None}
                return MatchResult(command=cmd, slots=slots, confidence=0.9)
        return None


def compile_patterns(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(p, flags=re.IGNORECASE | re.UNICODE) for p in patterns]
