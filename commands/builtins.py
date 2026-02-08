from __future__ import annotations

import sys
from datetime import datetime, timedelta
from typing import Dict
from urllib.parse import quote_plus

from adapters.windows import open_path, open_url, run_app
from commands.registry import Command, CommandContext, CommandRegistry, compile_patterns
from core.text_norm import normalize_text
from services.notes import add_note
from services.reminders import add_reminder
from services.time_parse import parse_duration_seconds, parse_time_of_day


_SITE_ALIASES: Dict[str, str] = {
    "ютуб": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",
    "гугл": "https://www.google.com",
    "google": "https://www.google.com",
}


def _resolve_site_to_url(text: str) -> str | None:
    key = normalize_text(text)
    return _SITE_ALIASES.get(key)


def create_registry() -> CommandRegistry:
    registry = CommandRegistry()

    registry.register(
        Command(
            name="help",
            description="Список команд",
            patterns=compile_patterns([r"\b(помощь|справка|что ты умеешь|команды|покажи команды)\b"]),
            parameters_schema={},
            handler=_handle_help,
        )
    )

    registry.register(
        Command(
            name="greet",
            description="Приветствие",
            patterns=compile_patterns([r"\b(привет|здравствуй|добрый день|добрый вечер|доброе утро)\b"]),
            parameters_schema={},
            handler=_handle_greet,
        )
    )

    registry.register(
        Command(
            name="time",
            description="Текущее время",
            patterns=compile_patterns([r"\b(который час|сколько времени|какое сейчас время|время)\b"]),
            parameters_schema={},
            handler=_handle_time,
        )
    )

    registry.register(
        Command(
            name="date",
            description="Текущая дата",
            patterns=compile_patterns([r"\b(какая дата|какое сегодня число|сегодня какое число|дата)\b"]),
            parameters_schema={},
            handler=_handle_date,
        )
    )

    registry.register(
        Command(
            name="open_url",
            description="Открыть сайт",
            patterns=compile_patterns(
                [
                    r"\bоткрой\s+(?P<url>https?://\S+)\b",
                    r"\bоткрой\s+(?P<site>ютуб|youtube|гугл|google)\b",
                ]
            ),
            parameters_schema={"url": "optional", "site": "optional"},
            handler=_handle_open_url,
        )
    )

    registry.register(
        Command(
            name="search_web",
            description="Поиск в интернете",
            patterns=compile_patterns([r"\bнайди( в интернете)?\s+(?P<query>.+)\b"]),
            parameters_schema={"query": "string"},
            handler=_handle_search_web,
        )
    )

    registry.register(
        Command(
            name="open_path",
            description="Открыть файл или папку",
            patterns=compile_patterns(
                [
                    r"\bоткрой\s+(файл|папку)\s+(?P<path>.+)\b",
                    r"\bоткрой\s+(?P<path>[a-zA-Z]:\\[^\\].+)\b",
                    r"\bоткрой\s+(?P<path>.+\.(txt|md|pdf|docx|xlsx|pptx|exe|lnk))\b",
                ]
            ),
            parameters_schema={"path": "string"},
            handler=_handle_open_path,
        )
    )

    registry.register(
        Command(
            name="open_app",
            description="Открыть приложение",
            patterns=compile_patterns([r"\bоткрой( приложение)?\s+(?P<app>[^/:\\]+)\b"]),
            parameters_schema={"app": "string"},
            handler=_handle_open_app,
        )
    )

    registry.register(
        Command(
            name="note_create",
            description="Создать заметку",
            patterns=compile_patterns(
                [
                    r"\b(сделай|создай|запиши)\s+заметк[ау]\s+(?P<note>.+)\b",
                    r"\bзаметк[ау]\s+(?P<note>.+)\b",
                ]
            ),
            parameters_schema={"note": "string"},
            handler=_handle_note_create,
        )
    )

    registry.register(
        Command(
            name="timer_set",
            description="Поставить таймер",
            patterns=compile_patterns([r"\b(поставь|установи)\s+таймер\s+на\s+(?P<duration>.+)\b"]),
            parameters_schema={"duration": "string"},
            handler=_handle_timer_set,
        )
    )

    registry.register(
        Command(
            name="reminder_set",
            description="Создать напоминание",
            patterns=compile_patterns(
                [
                    r"\bнапомни( мне)?\s+(?P<what>.+)\s+в\s+(?P<time>\d{1,2}:\d{2})\b",
                    r"\bнапомни( мне)?\s+(?P<what>.+)\s+через\s+(?P<duration>.+)\b",
                ]
            ),
            parameters_schema={"what": "string", "time": "optional", "duration": "optional"},
            handler=_handle_reminder_set,
        )
    )

    registry.register(
        Command(
            name="volume_set",
            description="Управление громкостью",
            patterns=compile_patterns(
                [
                    r"\b(громче|сделай громче|прибавь громкость)\b",
                    r"\b(тише|сделай тише|убавь громкость)\b",
                    r"\b(выключи звук|без звука|мут)\b",
                ]
            ),
            parameters_schema={},
            handler=_handle_volume_set,
        )
    )

    registry.register(
        Command(
            name="chat",
            description="Диалог с ИИ",
            patterns=compile_patterns([r"\bпоговори со мной\b(?P<topic>.*)"]),
            parameters_schema={"topic": "optional"},
            handler=_handle_chat,
        )
    )

    registry.register(
        Command(
            name="exit",
            description="Выход",
            patterns=compile_patterns([r"\b(выход|стоп|пока|завершить)\b"]),
            parameters_schema={},
            handler=_handle_exit,
        )
    )

    return registry


def _handle_help(ctx: CommandContext) -> str:
    registry = ctx.app_context.registry
    lines = ["Я Антошка. Вот что я умею:"]
    for cmd in registry.all():
        lines.append(f"- {cmd.description}")
    return "\n".join(lines)


def _handle_greet(_: CommandContext) -> str:
    return "Привет! Я Антошка. Скажи 'помощь', чтобы увидеть команды."


def _handle_time(_: CommandContext) -> str:
    now = datetime.now()
    return f"Сейчас {now:%H:%M}."


def _handle_date(_: CommandContext) -> str:
    now = datetime.now()
    return f"Сегодня {now:%d.%m.%Y}."


def _handle_open_url(ctx: CommandContext) -> str:
    url = ctx.slots.get("url")
    if not url:
        site = ctx.slots.get("site")
        if site:
            url = _resolve_site_to_url(site)
    if not url:
        return "Не понял, какой сайт открыть."
    ok = open_url(url)
    return "Открываю сайт." if ok else "Не смог открыть сайт."


def _handle_search_web(ctx: CommandContext) -> str:
    query = (ctx.slots.get("query") or "").strip()
    if not query:
        return "Не понял, что искать."
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    ok = open_url(url)
    return "Открываю результаты поиска." if ok else "Не смог открыть поиск."


def _handle_open_path(ctx: CommandContext) -> str:
    path = ctx.slots.get("path")
    if not path:
        return "Не понял, какой путь открыть."
    ok = open_path(path)
    return "Открываю." if ok else "Не смог открыть путь."


def _handle_open_app(ctx: CommandContext) -> str:
    app = (ctx.slots.get("app") or "").strip()
    if not app:
        return "Не понял, какое приложение открыть."
    if sys.platform != "win32":
        return "Открытие приложений доступно только на Windows."
    ok = run_app(app)
    return "Открываю приложение." if ok else "Не смог открыть приложение."


def _handle_note_create(ctx: CommandContext) -> str:
    note = (ctx.slots.get("note") or "").strip()
    if not note:
        return "Не понял, что записать."
    add_note(ctx.app_context.data_dir, note)
    return "Записал заметку."


def _handle_timer_set(ctx: CommandContext) -> str:
    duration_text = (ctx.slots.get("duration") or "").strip()
    seconds = parse_duration_seconds(duration_text)
    if not seconds:
        return "Не понял длительность таймера."
    ctx.app_context.scheduler.schedule_in(seconds, "Таймер сработал.")
    return "Таймер установлен."


def _handle_reminder_set(ctx: CommandContext) -> str:
    what = (ctx.slots.get("what") or "").strip()
    if not what:
        return "Не понял, о чем напомнить."

    delay_seconds = None
    when = None

    if "duration" in ctx.slots:
        delay_seconds = parse_duration_seconds(ctx.slots.get("duration"))
        if delay_seconds:
            when = datetime.now() + timedelta(seconds=delay_seconds)
    elif "time" in ctx.slots:
        when = parse_time_of_day(ctx.slots.get("time"))
        if when:
            delay_seconds = max(0, int((when - datetime.now()).total_seconds()))

    if not delay_seconds:
        return "Не понял время напоминания."

    add_reminder(ctx.app_context.data_dir, what, when)
    ctx.app_context.scheduler.schedule_in(delay_seconds, f"Напоминание: {what}")
    return "Напоминание создано."


def _handle_volume_set(ctx: CommandContext) -> str:
    text = normalize_text(ctx.text)
    controller = ctx.app_context.volume
    if controller is None:
        return "Не могу изменить громкость на этом устройстве."

    if "громче" in text or "прибавь" in text:
        ok = controller.change_relative(0.1)
        return "Сделал громче." if ok else "Не смог изменить громкость."
    if "тише" in text or "убавь" in text:
        ok = controller.change_relative(-0.1)
        return "Сделал тише." if ok else "Не смог изменить громкость."
    if "выключи звук" in text or "мут" in text or "без звука" in text:
        ok = controller.set_mute(True)
        return "Звук выключен." if ok else "Не смог выключить звук."

    return "Не понял команду для громкости."


def _handle_chat(ctx: CommandContext) -> str:
    llm_client = ctx.app_context.llm_client
    if llm_client is None:
        return "ИИ недоступен. Проверь ключ и настройки."
    topic = (ctx.slots.get("topic") or "").strip()
    if not topic:
        return "Слушаю, спрашивай."
    return llm_client.ask(topic)


def _handle_exit(_: CommandContext) -> str:
    return "__EXIT__"
