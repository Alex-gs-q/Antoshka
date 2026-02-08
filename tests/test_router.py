from pathlib import Path

from core.app_context import AppContext
from core.router import CommandRouter
from services.scheduler import Scheduler


def _make_router() -> CommandRouter:
    ctx = AppContext(
        notify=lambda _: None,
        data_dir=Path("data"),
        scheduler=Scheduler(notify=lambda _: None),
        volume=None,
        llm_client=None,
    )
    return CommandRouter(ctx)


def test_greet():
    r = _make_router()
    res = r.route("привет")
    assert res is not None
    assert res.name == "greet"


def test_time():
    r = _make_router()
    res = r.route("антошка, который час")
    assert res is not None
    assert res.name == "time"


def test_open_url_alias():
    r = _make_router()
    res = r.route("открой ютуб")
    assert res is not None
    assert res.name == "open_url"
    assert res.slots.get("site") == "ютуб"


def test_open_url_direct():
    r = _make_router()
    res = r.route("открой https://example.com")
    assert res is not None
    assert res.name == "open_url"
    assert res.slots.get("url") == "https://example.com"


def test_search_web():
    r = _make_router()
    res = r.route("найди в интернете котиков")
    assert res is not None
    assert res.name == "search_web"
    assert "котиков" in res.slots.get("query", "")


def test_open_path():
    r = _make_router()
    res = r.route("открой файл C:\\Temp\\note.txt")
    assert res is not None
    assert res.name == "open_path"
    assert "C:\\Temp\\note.txt" in res.slots.get("path", "")


def test_open_app():
    r = _make_router()
    res = r.route("открой приложение notepad")
    assert res is not None
    assert res.name == "open_app"
    assert res.slots.get("app") == "notepad"


def test_note_create():
    r = _make_router()
    res = r.route("сделай заметку купить молоко")
    assert res is not None
    assert res.name == "note_create"
    assert "купить молоко" in res.slots.get("note", "")


def test_timer_set():
    r = _make_router()
    res = r.route("поставь таймер на 5 минут")
    assert res is not None
    assert res.name == "timer_set"
    assert "5 минут" in res.slots.get("duration", "")


def test_reminder_set():
    r = _make_router()
    res = r.route("напомни мне позвонить в 18:30")
    assert res is not None
    assert res.name == "reminder_set"
    assert res.slots.get("time") == "18:30"
