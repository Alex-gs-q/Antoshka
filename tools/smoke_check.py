from __future__ import annotations

# ruff: noqa: E402

import json
import re
import sys
import threading
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.app_context import AppContext
from core.i18n import help_lines
from core.logger import setup_logger
from core.resources import resource_path
from core.router import CommandRouter
from services.scheduler import Scheduler
from alerts.audio_alerts import AudioAlerts


def _make_router() -> CommandRouter:
    ctx = AppContext(
        notify=lambda _: None,
        data_dir=Path("data"),
        scheduler=Scheduler(notify=lambda _: None),
        volume=None,
        llm_client=None,
    )
    return CommandRouter(ctx)


def _check_i18n() -> List[str]:
    issues: List[str] = []
    r = _make_router()
    cmds = [c.name for c in r.registry.all()]
    ru = "\n".join(help_lines("ru", cmds))
    en = "\n".join(help_lines("en", cmds))
    if re.search(r"[A-Za-z]", ru):
        issues.append("RU help contains Latin letters")
    if re.search(r"[А-Яа-яЁё]", en):
        issues.append("EN help contains Cyrillic")
    return issues


def _check_settings_utf8() -> List[str]:
    issues: List[str] = []
    path = Path("config/settings.json")
    try:
        text = path.read_bytes().decode("utf-8")
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        issues.append(f"settings.json invalid UTF-8 or JSON: {e}")
    return issues


def _check_phrases_utf8() -> List[str]:
    issues: List[str] = []
    ru_path = Path("config/phrases_ru.json")
    en_path = Path("config/phrases_en.json")
    try:
        text = ru_path.read_bytes().decode("utf-8")
        if re.search(r"[А-Яа-яЁё]", text) is None:
            issues.append("phrases_ru.json has no Cyrillic")
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        issues.append(f"phrases_ru.json invalid UTF-8 or JSON: {e}")
    try:
        text = en_path.read_bytes().decode("utf-8")
        if re.search(r"[А-Яа-яЁё]", text) is not None:
            issues.append("phrases_en.json contains Cyrillic")
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        issues.append(f"phrases_en.json invalid UTF-8 or JSON: {e}")
    return issues


def _router_cases() -> List[Tuple[str, str, str | None]]:
    return [
        ("privet", "greet", None),
        ("zdravstvuy", "greet", None),
        ("dobryy den", "greet", None),
        ("pomoshch", "help", None),
        ("spravka", "help", None),
        ("komandy", "help", None),
        ("pokazhi komandy", "help", None),
        ("skolko vremeni", "time", None),
        ("vremya", "time", None),
        ("kakaya data", "date", None),
        ("kakoe segodnya chislo", "date", None),
        ("otkroy youtube", "open_url", None),
        ("otkroy sait vk", "open_url", None),
        ("otkroy https://example.com", "open_url", None),
        ("naydi v internete kotikov", "search_web", None),
        ("poisk v internete novosti", "search_web", None),
        ("otkroy kartu", "open_map", None),
        ("pokazhi marshrut do doma", "open_map", None),
        (r"otkroy fail C:\Temp\note.txt", "open_path", None),
        ("otkroy papku zagruzki", "open_path", None),
        ("otkroy prilozhenie notepad", "open_app", None),
        ("sdelai zametku kupit moloko", "note_create", None),
        ("zametka: kupit hleb", "note_create", None),
        ("pokazhi zametki", "note_list", None),
        ("udali zametku 2", "note_delete", None),
        ("izmeni zametku 2 na kupit hleb", "note_update", None),
        ("zameni v zametke 2 moloko na hleb", "note_replace", None),
        ("postav timer na 5 minut", "timer_set", None),
        ("ustanovi timer na 10 minut", "timer_set", None),
        ("postav budilnik na 07:30", "alarm_set", None),
        ("napomni mne kupit hleb v 18:30", "reminder_set", None),
        ("napomni kupit hleb cherez 10 minut", "reminder_set", None),
        ("sdelai gromche", "volume_set", None),
        ("sdelai tishe", "volume_set", None),
        ("gromkost na 40", "volume_set", None),
        ("mut", "volume_set", None),
        ("proverka zvuka", "tts_test", None),
        ("skazhi test", "tts_test", None),
        ("ustanovi yazyk ru", "settings_language", None),
        ("ustanovi yazyk en", "settings_language", None),
        ("ustanovi temu dark", "settings_theme", None),
        ("ustanovi temu neon", "settings_theme", None),
        ("ustanovi accent #7dd3fc", "settings_accent", None),
        ("ustanovi fon 70", "settings_bg_intensity", None),
        ("ustanovi skorost 180", "settings_tts_rate", None),
        ("ustanovi gromkost golosa 70", "settings_tts_volume", None),
        ("vklyuchi proslushku", "settings_wake", None),
        ("vykluchi proslushku", "settings_wake", None),
        ("otkroy pochtu", "open_mail", None),
        ("open mail", "open_mail", "en"),
        ("open gmail", "open_mail", "en"),
        ("otkroy kalendar", "open_calendar", None),
        ("open calendar", "open_calendar", "en"),
        ("pogoda v moskve", "weather", None),
        ("pogoda", "weather", None),
        ("sozdai sobytie vstrecha na 10.02.2026 15:30", "event_add", None),
        ("dobav sobytie zvonok na 10.02.2026 14:00", "event_add", None),
        ("pokazhi sobytiya", "event_list", None),
        ("spisok sobytiy", "event_list", None),
        ("ochisti chat", "clear_chat", None),
        ("udali istoriyu chata", "clear_chat", None),
        ("vyhod", "exit", None),
        ("exit", "exit", "en"),
        ("hello", "greet", "en"),
        ("what time is it", "time", "en"),
        ("what date is it", "date", "en"),
        ("open youtube", "open_url", "en"),
        ("open site", "open_url", "en"),
        ("open folder", "open_path", "en"),
        ("open file", "open_path", "en"),
        ("help", "help", "en"),
        ("commands", "help", "en"),
        ("bye", "exit", "en"),
    ]


def _check_router() -> List[str]:
    issues: List[str] = []
    r = _make_router()
    for text, expected, lang in _router_cases():
        res = r.route(text, lang=lang) if lang else r.route(text)
        if res is None:
            issues.append(f"No match for: {text}")
            continue
        if res.name != expected:
            issues.append(f"{text} => {res.name}, expected {expected}")
    return issues


def _check_scheduler() -> List[str]:
    issues: List[str] = []
    fired = threading.Event()

    def _on_event(_event) -> None:
        fired.set()

    scheduler = Scheduler(notify=_on_event)
    scheduler.schedule_in(0, "test", meta={"type": "timer", "duration_sec": 1})
    if not fired.wait(1.0):
        issues.append("Scheduler did not fire within timeout")
    return issues


def run_self_test() -> int:
    logger = setup_logger()
    issues: List[str] = []

    issues.extend(_check_i18n())
    issues.extend(_check_settings_utf8())
    issues.extend(_check_phrases_utf8())
    issues.extend(_check_router())
    issues.extend(_check_scheduler())
    # audio alerts init + file check
    try:
        try:
            from PySide6.QtCore import QCoreApplication
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"PySide6 unavailable: {e}") from e
        if QCoreApplication.instance() is None:
            _ = QCoreApplication([])
        _ = AudioAlerts()
    except Exception as e:  # noqa: BLE001
        issues.append(f"AudioAlerts init failed: {e}")
    sound_path = resource_path("Music/Kioko - The Phantom Traveler.mp3")
    if not sound_path.exists():
        issues.append("Alert sound missing: Music/Kioko - The Phantom Traveler.mp3")

    if issues:
        logger.error("Self-test FAILED: %d issue(s)", len(issues))
        for item in issues:
            logger.error("Self-test issue: %s", item)
        print("SELF-TEST: FAIL")
        for item in issues:
            print(" -", item)
        return 1

    logger.info("Self-test PASSED")
    print("SELF-TEST: PASS")
    return 0


def main() -> int:
    return run_self_test()


if __name__ == "__main__":
    raise SystemExit(main())
