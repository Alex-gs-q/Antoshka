from __future__ import annotations

# ruff: noqa: E402

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.app_context import AppContext
from core.config import load_settings
from core.dialogue import Dialogue, DialogueConfig
from core.i18n import help_sections
from core.logger import setup_logger
from core.paths import data_dir
from core.router import CommandRouter
from core.suggestions import pick_suggestions
from services.scheduler import Scheduler
from services.time_parse import parse_duration_seconds


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def run_smoke() -> int:
    log = setup_logger()
    try:
        settings = load_settings()
        _ok("settings loaded")
    except Exception as e:  # noqa: BLE001
        _fail(f"settings load failed: {e}")
        return 1

    try:
        hs = help_sections(settings.get("app", {}).get("language", "ru"))
        _ok(f"help sections: {len(hs)}")
    except Exception as e:  # noqa: BLE001
        _fail(f"help sections failed: {e}")
        return 1

    try:
        app_ctx = AppContext(
            notify=lambda _: None,
            data_dir=data_dir(),
            scheduler=Scheduler(notify=lambda _: None),
            volume=None,
        )
        dlg = Dialogue(DialogueConfig(app_context=app_ctx))
        out = dlg.handle_text("помощь", language="ru", allow_llm=False)
        _ok(f"dialogue ok: {type(out).__name__}")
    except Exception as e:  # noqa: BLE001
        _fail(f"dialogue failed: {e}")
        return 1

    try:
        router = CommandRouter(app_ctx)
        cases = [
            ("привет", "greet", "ru"),
            ("помощь", "help", "ru"),
            ("команды", "help", "ru"),
            ("сколько времени", "time", "ru"),
            ("какая дата", "date", "ru"),
            ("открой сайт vk", "open_url", "ru"),
            ("открой карту", "open_map", "ru"),
            ("открой папку загрузки", "open_path", "ru"),
            ("открой приложение калькулятор", "open_app", "ru"),
            ("создай заметку купить молоко", "note_create", "ru"),
            ("покажи заметки", "note_list", "ru"),
            ("удали заметку 1", "note_delete", "ru"),
            ("поставь таймер на 5 минут", "timer_set", "ru"),
            ("поставь будильник на 07:30", "alarm_set", "ru"),
            ("напомни купить хлеб через 10 минут", "reminder_set", "ru"),
            ("погода в москве", "weather", "ru"),
            ("создай событие встреча на 10.02.2026 15:30", "event_add", "ru"),
            ("покажи события", "event_list", "ru"),
            ("очисти чат", "clear_chat", "ru"),
            ("выход", "exit", "ru"),
            ("hello", "greet", "en"),
            ("help", "help", "en"),
            ("what time is it", "time", "en"),
            ("what date is it", "date", "en"),
            ("open youtube", "open_url", "en"),
            ("open site", "open_url", "en"),
            ("open folder", "open_path", "en"),
            ("open file", "open_path", "en"),
            ("open calendar", "open_calendar", "en"),
            ("open mail", "open_mail", "en"),
            ("set a timer for 10 minutes", "timer_set", "en"),
            ("remind me in 20 minutes", "reminder_set", "en"),
            ("pogoda v london", "weather", "en"),
            ("exit", "exit", "en"),
        ]
        for text, expected, lang in cases:
            res = router.route(text, lang=lang)
            if not res or res.name != expected:
                _fail(
                    f"route mismatch: {text} -> {getattr(res, 'name', None)} expected {expected}"
                )
                return 1
        _ok(f"router cases: {len(cases)}")
    except Exception as e:  # noqa: BLE001
        _fail(f"router failed: {e}")
        return 1

    try:
        durations = [
            ("таймер на 5 сек", 5),
            ("таймер на 10с", 10),
            ("через 2 мин", 120),
            ("через 1ч 20мин", 4800),
            ("set a timer for 10 sec", 10),
            ("in 2 mins", 120),
            ("in 1 hr 20 min", 4800),
            ("set a timer for 10s", 10),
        ]
        for text, expected in durations:
            got = parse_duration_seconds(text)
            if got != expected:
                _fail(f"time parse mismatch: {text} -> {got} expected {expected}")
                return 1
        _ok(f"time parse cases: {len(durations)}")
    except Exception as e:  # noqa: BLE001
        _fail(f"time parse failed: {e}")
        return 1

    try:
        registry = router.registry
        for lang in ("ru", "en"):
            picked = pick_suggestions(registry, lang, "default", k=5)
            if len(picked) != 5:
                _fail(f"suggestions count: {len(picked)} for {lang}")
                return 1
            all_examples = set(registry.get_all_examples(lang))
            if not all(p in all_examples for p in picked):
                _fail(f"suggestions not from registry for {lang}")
                return 1
        _ok("suggestions ok")
    except Exception as e:  # noqa: BLE001
        _fail(f"suggestions failed: {e}")
        return 1

    stt = settings.get("stt", {}) or {}
    vosk_path = stt.get("vosk_model_path") or "models/vosk"
    if Path(vosk_path).exists() or (Path(data_dir()) / vosk_path).exists():
        _ok("vosk model path exists")
    else:
        log.warning("Vosk model not found at %s (expected for text-mode demos).", vosk_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(run_smoke())
