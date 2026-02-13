import re
from pathlib import Path

from commands.builtins import create_registry
from commands.registry import CommandContext
from core.app_context import AppContext
from services.scheduler import Scheduler


def _get_help(lang: str) -> str:
    app_context = AppContext(
        notify=lambda _: None,
        data_dir=Path("data"),
        scheduler=Scheduler(notify=lambda _: None),
        volume=None,
        llm_client=None,
        language_mode=lang,
        language=lang,
    )
    registry = create_registry()
    app_context.registry = registry
    cmd = registry.get("help")
    ctx = CommandContext(text="help", slots={}, app_context=app_context)
    res = cmd.handler(ctx)
    return res.text if hasattr(res, "text") else str(res)


def test_help_ru_no_latin() -> None:
    text = _get_help("ru")
    assert re.search(r"[A-Za-z]", text) is None


def test_help_en_no_cyrillic() -> None:
    text = _get_help("en")
    assert re.search(r"[А-Яа-яЁё]", text) is None
