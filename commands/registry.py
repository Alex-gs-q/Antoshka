from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Pattern, Union

from core.actions import ActionResult
from core.text_norm import normalize_match_text
from core.config import load_settings
from services.site_catalog import resolve_site


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    patterns: List[Pattern[str]]
    triggers: List[str]
    examples: List[str]
    examples_ru: List[str]
    examples_en: List[str]
    group: str
    parameters_schema: Dict[str, str]
    handler: Callable[["CommandContext"], Union[str, ActionResult]]

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

    def examples_by_group(self, lang: str) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        lang = (lang or "ru").lower()
        for cmd in self._commands:
            if lang == "ru":
                examples = cmd.examples_ru or []
            else:
                examples = cmd.examples_en or []
            if not examples:
                continue
            group = cmd.group or "general"
            out.setdefault(group, [])
            out[group].extend(examples)
        return out

    def all_examples(self, lang: str) -> List[str]:
        out: List[str] = []
        for items in self.examples_by_group(lang).values():
            out.extend(items)
        return out

    def get_all_examples(self, lang: str) -> List[str]:
        return self.all_examples(lang)

    def as_tools(self) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = []
        for cmd in self._commands:
            tools.append(
                {
                    "type": "function",
                    "name": cmd.name,
                    "description": cmd.description,
                    "parameters": cmd.json_schema(),
                }
            )
        return tools

    def match(self, text: str) -> Optional[MatchResult]:
        raw = text or ""
        norm = normalize_match_text(text)
        for cmd in self._commands:
            # Prefer matching raw text to preserve original slots (Cyrillic, paths, URLs).
            for pattern in cmd.patterns:
                m = pattern.search(raw)
                if not m:
                    continue
                slots = {k: v for k, v in m.groupdict().items() if v is not None}
                if cmd.name == "open_url" and "site" in slots:
                    site_text = normalize_match_text(slots.get("site", ""))
                    if "prilozhenie" in site_text or "app" in site_text:
                        continue
                    if any(
                        token in site_text
                        for token in (
                            "gmail",
                            "yahoo",
                            "proton",
                            "outlook",
                            "icloud",
                            "mailru",
                            "mail ru",
                            "fastmail",
                            "tuta",
                            "zoho",
                            "pochta",
                        )
                    ):
                        # Prefer open_mail handler for mail providers.
                        continue
                    custom_sites = (load_settings().get("custom_sites") or {})
                    if not resolve_site(slots.get("site", ""), custom_sites) and site_text not in {
                        "site",
                        "website",
                        "web",
                    }:
                        continue
                return MatchResult(command=cmd, slots=slots, confidence=0.92)
            # Fallback to normalized text for transliterated or noisy input.
            for pattern in cmd.patterns:
                m = pattern.search(norm)
                if not m:
                    continue
                slots = {k: v for k, v in m.groupdict().items() if v is not None}
                if cmd.name == "open_url" and "site" in slots:
                    site_text = normalize_match_text(slots.get("site", ""))
                    if "prilozhenie" in site_text or "app" in site_text:
                        continue
                    if any(
                        token in site_text
                        for token in (
                            "gmail",
                            "yahoo",
                            "proton",
                            "outlook",
                            "icloud",
                            "mailru",
                            "mail ru",
                            "fastmail",
                            "tuta",
                            "zoho",
                            "pochta",
                        )
                    ):
                        continue
                    custom_sites = (load_settings().get("custom_sites") or {})
                    if not resolve_site(slots.get("site", ""), custom_sites) and site_text not in {
                        "site",
                        "website",
                        "web",
                    }:
                        continue
                return MatchResult(command=cmd, slots=slots, confidence=0.92)

        # Triggers are a fallback if no patterns matched across all commands.
        for cmd in self._commands:
            if cmd.triggers:
                for trig in cmd.triggers:
                    if _words_in_text(trig, norm):
                        return MatchResult(command=cmd, slots={}, confidence=0.75)
        return None


def compile_patterns(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(p, flags=re.IGNORECASE | re.UNICODE) for p in patterns]


def _words_in_text(phrase: str, text: str) -> bool:
    if not phrase or not text:
        return False
    pattern = r"(?:^|\s)" + re.escape(phrase) + r"(?:$|\s)"
    return re.search(pattern, text) is not None
