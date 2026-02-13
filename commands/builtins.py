from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote_plus

from adapters.windows import open_path, open_url, run_app
from commands.registry import Command, CommandContext, CommandRegistry, compile_patterns
from core.actions import ActionResult
from core.config import load_settings, save_settings
from core.i18n import t as tr
from core.text_norm import normalize_match_text
from services.app_catalog import resolve_app
from services.notes import add_note, list_notes, delete_note, update_note, replace_in_note, find_note_index
from services.calendar_events import add_event, list_events
from services.path_catalog import resolve_known_path
from services.reminders import add_reminder
from services.site_catalog import resolve_site
from services.time_parse import parse_duration_seconds, parse_time_of_day, parse_date, parse_date_time


def _cmd(
    name: str,
    description: str,
    patterns: List[str],
    handler,
    parameters_schema: Dict[str, str] | None = None,
    triggers: List[str] | None = None,
    examples: List[str] | None = None,
    examples_ru: List[str] | None = None,
    examples_en: List[str] | None = None,
    group: str | None = None,
) -> Command:
    return Command(
        name=name,
        description=description,
        patterns=compile_patterns(patterns),
        triggers=triggers or [],
        examples=examples or [],
        examples_ru=examples_ru or [],
        examples_en=examples_en or [],
        group=group or "general",
        parameters_schema=parameters_schema or {},
        handler=handler,
    )


def _lang(ctx: CommandContext) -> str:
    return getattr(ctx.app_context, "language", "ru")


def _t(ctx: CommandContext, key: str, **kwargs) -> str:
    text = tr(key, _lang(ctx))
    if kwargs:
        return text.format(**kwargs)
    return text


def create_registry() -> CommandRegistry:
    registry = CommandRegistry()

    registry.register(
        _cmd(
            name="help",
            description="Commands list",
            patterns=[
                r"\b(pomoshch|pomosch|spravka|chto ty umeesh|komandy|pokazhi komandy)\b",
                r"\b(help|show commands|what can you do|commands|help me|list commands|show help)\b",
            ],
            triggers=[
                "pomoshch",
                "pomosch",
                "chto ty umeesh",
                "spravka",
                "komandy",
                "pokazhi komandy",
                "podskazhi komandy",
                "spisok komand",
                "chto umesh",
                "chto mozhesh",
                "kak polzovatsya",
                "help",
            ],
            examples=["help", "show commands"],
            examples_ru=[
                "помощь",
                "покажи команды",
                "что ты умеешь",
                "справка",
                "команды",
                "список команд",
                "подскажи команды",
                "как пользоваться",
            ],
            examples_en=[
                "help",
                "show commands",
                "what can you do",
                "commands",
                "list commands",
                "show help",
                "help me",
                "commands list",
            ],
            group="help",
            handler=_handle_help,
        )
    )

    registry.register(
        _cmd(
            name="greet",
            description="Greeting",
            patterns=[
                r"\b(privet|zdravstvuy|dobryy (den|vecher|utro))\b",
                r"\b(hello|hi|hey|good (morning|afternoon|evening))\b",
            ],
            triggers=[
                "privet",
                "zdravstvuy",
                "privetik",
                "privet antoshka",
                "dobryy den",
                "dobroe utro",
                "dobryy vecher",
                "hello",
                "hi",
            ],
            examples=["hello", "hi"],
            examples_ru=["привет", "привет антошка", "добрый день", "добрый вечер"],
            examples_en=["hello", "hi", "good morning", "good evening"],
            group="general",
            handler=_handle_greet,
        )
    )

    registry.register(
        _cmd(
            name="time",
            description="Current time",
            patterns=[
                r"\b(kotoryy chas|skolko vremeni|vremya)\b",
                r"\b(what time is it|current time|time)\b",
            ],
            triggers=[
                "kotoryy chas",
                "skolko vremeni",
                "vremya",
                "kakoe seychas vremya",
                "skazhi vremya",
                "vremya seychas",
                "time",
            ],
            examples=["what time is it", "current time"],
            examples_ru=["который час", "сколько времени"],
            examples_en=["what time is it", "current time"],
            group="general",
            handler=_handle_time,
        )
    )

    registry.register(
        _cmd(
            name="date",
            description="Current date",
            patterns=[
                r"\b(kakaya data|kakoe segodnya chislo|segodnya kakoe chislo|data|den nedeli)\b",
                r"\b(what date is it|what day is it|today's date|date)\b",
            ],
            triggers=[
                "kakaya data",
                "kakoe segodnya chislo",
                "segodnya kakoe chislo",
                "data",
                "kakoy den nedeli",
                "den nedeli",
            ],
            examples=["what date is it", "today's date"],
            examples_ru=["какая дата", "какое сегодня число"],
            examples_en=["what date is it", "today's date"],
            group="general",
            handler=_handle_date,
        )
    )

    registry.register(
        _cmd(
            name="tts_test",
            description="Sound test",
            patterns=[
                r"\b(skazhi test|test zvuka|prover zvuk|proverka zvuka)\b",
                r"\b(sound test|test sound|sound check)\b",
            ],
            triggers=["skazhi test", "test zvuka", "prover zvuk", "proverka zvuka"],
            examples=["sound test", "sound check"],
            examples_ru=["тест звука", "проверка звука"],
            examples_en=["sound test", "sound check"],
            group="system",
            handler=_handle_tts_test,
        )
    )

    registry.register(
        _cmd(
            name="open_map",
            description="Open map",
            patterns=[
                r"\b(otkroy kartu|karta|pokazhi kartu)(\s+(?P<query>.+))?\b",
                r"\b(pokazhi marshrut|marshrut)\s+(?P<query>.+)\b",
                r"\b(open|show)\s+map(\s+of)?(\s+(?P<query>.+))?\b",
            ],
            triggers=["otkroy kartu", "pokazhi kartu", "karta", "pokazhi marshrut"],
            examples=["open map", "show map of london"],
            examples_ru=["открой карту", "покажи маршрут до дома"],
            examples_en=["open map", "show map of london"],
            group="open_web",
            parameters_schema={"query": "optional"},
            handler=_handle_open_map,
        )
    )

    registry.register(
        _cmd(
            name="search_web",
            description="Web search",
            patterns=[
                r"\b(найди|поиск|ищи|погугли|загугли)\s+(?P<query>.+)\b",
                r"\b(найди в интернете|поиск в интернете)\s+(?P<query>.+)\b",
                r"\b(naydi|poisk|ishi|pogugli|zagugli)\s+(?P<query>.+)\b",
                r"\b(naydi v internete|poisk v internete)\s+(?P<query>.+)\b",
                r"\b(search( the web)?( for)?|google|find)\s+(?P<query>.+)\b",
            ],
            triggers=["naydi", "poisk", "pogugli", "zagugli", "naydi v internete"],
            examples=["search the web for news", "google best movies 2025"],
            examples_ru=["найди в интернете новости", "поиск в интернете погода"],
            examples_en=["search the web for news", "google best movies 2025", "find weather in london", "search for python tutorial"],
            group="open_web",
            parameters_schema={"query": "string"},
            handler=_handle_search_web,
        )
    )

    registry.register(
        _cmd(
            name="open_path",
            description="Open file or folder",
            patterns=[
                r"\b(открой|открыть)\s+(файл|папку)\s+(?P<path>.+)\b",
                r"\b(открой|открыть)\s+(?P<path>[a-zA-Z]:\\[^\s].+)\b",
                r"\b(открой|открыть)\s+(?P<path>.+\.(txt|md|pdf|docx|xlsx|pptx|exe|lnk))\b",
                r"\b(открой|открыть)\s+(?P<path>загрузки|документы|рабочий стол)\b",
                r"\b(otkroy|otkryt)\s+(fail|papku)\s+(?P<path>.+)\b",
                r"\b(otkroy|otkryt)\s+(?P<path>[a-zA-Z]:\\[^\s].+)\b",
                r"\b(otkroy|otkryt)\s+(?P<path>.+\.(txt|md|pdf|docx|xlsx|pptx|exe|lnk))\b",
                r"\b(otkroy|otkryt)\s+(?P<path>zagruzki|dokumenty|rabochiy stol|downloads|documents|desktop)\b",
                r"\b(open)\s+(file|folder)\s+(?P<path>.+)\b",
                r"\b(open)\s+file\b",
                r"\b(open)\s+folder\b",
                r"\b(open)\s+(?P<path>[a-zA-Z]:\\[^\s].+)\b",
                r"\b(open)\s+(?P<path>.+\.(txt|md|pdf|docx|xlsx|pptx|exe|lnk))\b",
                r"\b(open)\s+(?P<path>downloads|documents|desktop)\b",
            ],
            triggers=["otkroy papku", "otkroy fail", "otkroy zagruzki", "otkroy dokumenty"],
            examples=["open documents", "open file report.pdf"],
            examples_ru=[
                "открой папку документы",
                "открой загрузки",
                "открой рабочий стол",
                "открой файл отчет.pdf",
            ],
            examples_en=["open documents", "open file report.pdf", "open downloads", "open desktop"],
            group="open_apps",
            parameters_schema={"path": "string"},
            handler=_handle_open_path,
        )
    )

    registry.register(
        _cmd(
            name="screenshot",
            description="Screenshot",
            patterns=[
                r"\b((sdelai|sdelay)\s+skrinshot|(sdelai|sdelay)\s+snimok ekrana|screenshot)\b",
                r"\b(take a screenshot|screenshot)\b",
            ],
            triggers=["sdelai skrinshot", "sdelay skrinshot", "sdelai snimok ekrana", "sdelay snimok ekrana", "screenshot"],
            examples=["take a screenshot", "screenshot"],
            examples_ru=["сделай скриншот"],
            examples_en=["take a screenshot", "screenshot"],
            group="system",
            handler=_handle_screenshot,
        )
    )

    registry.register(
        _cmd(
            name="open_url",
            description="Open website",
            patterns=[
                r"\b(открой|открыть|зайди|запусти)\s+(на\s+)?(?P<url>https?://\S+)\b",
                r"\b(открой|открыть|зайди|запусти)\s+(на\s+)?(сайт\s+)?(?P<site>[\w\s]+)\b",
                r"\b(otkroy|otkryt|zaydi|zapusti)\s+(na\s+)?(?P<url>https?://\S+)\b",
                r"\b(otkroy|otkryt|zaydi|zapusti)\s+(na\s+)?(sait\s+)?(?P<site>[\w\s]+)\b",
                r"\b(open|go to|visit)\s+(?P<url>https?://\S+)\b",
                r"\b(open|go to|visit)\s+(site\s+)?(?P<site>[\w\s]+)\b",
            ],
            triggers=[
                "otkroy sait",
                "otkroy vk",
                "otkroy youtube",
                "otkroy telegram",
                "otkroy discord",
                "otkroy yandex",
                "otkroy google",
                "otkroy gmail",
                "otkroy maps",
            ],
            examples=["open youtube", "open google"],
            examples_ru=["открой ютуб", "открой гугл"],
            examples_en=["open youtube", "open google", "open telegram", "visit wikipedia"],
            group="open_web",
            parameters_schema={"url": "optional", "site": "optional"},
            handler=_handle_open_url,
        )
    )

    registry.register(
        _cmd(
            name="open_mail",
            description="Open mail",
            patterns=[
                r"\b(otkroy|otkryt|zaydi)\s+(pochtu|gmail|pochta|outlook|icloud|yahoo|proton|mail\.ru|zoho|fastmail|tuta)\b",
                r"\b(открой|открыть|зайди)\s+(почту|джимейл|gmail|аутлук|icloud|айклауд|яху|протон|mail\.ru|зохо|фастмейл|тута)\b",
                r"\b(open)\s+(mail|gmail|outlook|icloud|yahoo|proton|zoho|fastmail|tuta)\b",
            ],
            triggers=[
                "otkroy pochta",
                "otkroy gmail",
                "открой почту",
                "open mail",
                "открой яндекс почту",
                "открой outlook",
                "открой icloud",
                "открой yahoo mail",
                "открой proton mail",
                "открой mail.ru",
                "открой zoho mail",
                "открой fastmail",
                "открой tuta",
            ],
            examples=["open mail", "open gmail"],
            examples_ru=["открой почту", "открой gmail"],
            examples_en=["open mail", "open gmail"],
            group="open_web",
            parameters_schema={"provider": "optional"},
            handler=_handle_open_mail,
        )
    )

    registry.register(
        _cmd(
            name="open_calendar",
            description="Open calendar",
            patterns=[
                r"\b(otkroy|otkryt|zaydi)\s+kalendar\b",
                r"\b(open)\s+calendar\b",
                r"\bcalendar\b",
            ],
            triggers=["otkroy kalendar", "открой календарь", "open calendar"],
            examples=["open calendar", "calendar"],
            examples_ru=["открой календарь"],
            examples_en=["open calendar", "calendar"],
            group="open_web",
            handler=_handle_open_calendar,
        )
    )

    registry.register(
        _cmd(
            name="open_app",
            description="Open app",
            patterns=[
                r"\b(otkroy|otkryt|zapusti|zapusk)\s+(prilozhenie\s+)?(?P<app>[\w\s\-\.]+)\b",
                r"\b(open|launch|start)\s+(app\s+)?(?P<app>[\w\s\-\.]+)\b",
            ],
            triggers=["otkroy prilozhenie", "zapusti", "otkroy kalkulyator", "otkroy bloknot"],
            examples=["open calculator", "open notepad"],
            examples_ru=["открой калькулятор", "открой блокнот", "запусти калькулятор", "запусти discord"],
            examples_en=["open calculator", "open notepad", "launch discord", "start calculator"],
            group="open_apps",
            parameters_schema={"app": "string"},
            handler=_handle_open_app,
        )
    )

    registry.register(
        _cmd(
            name="note_delete",
            description="Delete a note",
            patterns=[
                r"\b(udali|udalit)\s+zametk[au]\s+(?P<index>\d+)\b",
                r"\b(delete)\s+note\s+(?P<index>\d+)\b",
            ],
            triggers=["udali zametku"],
            examples=["delete note 1", "delete note 2"],
            examples_ru=["удали заметку 1"],
            examples_en=["delete note 1", "delete note 2"],
            group="notes",
            parameters_schema={"index": "string"},
            handler=_handle_note_delete,
        )
    )

    registry.register(
        _cmd(
            name="note_create",
            description="Create a note",
            patterns=[
                r"\b(создай|сделай|запиши)\s+заметк[ау]\s+(?P<note>.+)\b",
                r"\bзаметк[ау]\s*[:\-]\s*(?P<note>.+)\b",
                r"\b(sozdai|sozday|sdelai|sdelay|zapishi|zapishe)\s+zametk[au]\s+(?P<note>.+)\b",
                r"\bzametk[au]\s*[:\-]\s*(?P<note>.+)\b",
                r"\b(create|make|add)\s+(a\s+)?note\s+(?P<note>.+)\b",
                r"\bnote\s*[:\-]\s*(?P<note>.+)\b",
            ],
            triggers=["sozdai zametku", "sdelai zametku", "zametka"],
            examples=["create a note: buy bread", "add note call mom"],
            examples_ru=[
                "создай заметку: купить хлеб",
                "заметка: купить молоко",
                "создай заметку позвонить маме",
                "сделай заметку купить молоко",
            ],
            examples_en=["create a note: buy bread", "add note call mom", "note: buy milk", "make a note to pay bills"],
            group="notes",
            parameters_schema={"note": "string"},
            handler=_handle_note_create,
        )
    )

    registry.register(
        _cmd(
            name="note_list",
            description="List notes",
            patterns=[
                r"\b(pokazhi zametki|moi zametki|spisok zametok)\b",
                r"\b(list notes|show notes|my notes)\b",
            ],
            triggers=["pokazhi zametki", "moi zametki", "spisok zametok"],
            examples=["list notes", "show notes"],
            examples_ru=["покажи заметки"],
            examples_en=["list notes", "show notes"],
            group="notes",
            handler=_handle_note_list,
        )
    )

    registry.register(
        _cmd(
            name="note_update",
            description="Update a note",
            patterns=[
                r"\b(izmeni|izmenit|obnovi|obnovit)\s+zametk[au]\s+(?P<index>\d+)\s+na\s+(?P<note>.+)\b",
                r"\b(update|edit)\s+note\s+(?P<index>\d+)\s+(to|with)\s+(?P<note>.+)\b",
            ],
            triggers=["izmeni zametku", "obnovi zametku", "изменить заметку"],
            examples=["update note 1 to buy milk", "edit note 2 with buy bread"],
            examples_ru=["измени заметку 1 на купить молоко"],
            examples_en=["update note 1 to buy milk", "edit note 2 with buy bread"],
            group="notes",
            parameters_schema={"index": "string", "note": "string"},
            handler=_handle_note_update,
        )
    )

    registry.register(
        _cmd(
            name="note_replace",
            description="Replace in note",
            patterns=[
                r"\b(zameni)\s+v\s+zametke\s+(?P<index>\d+)\s+(?P<old>.+)\s+na\s+(?P<new>.+)\b",
                r"\b(replace)\s+in\s+note\s+(?P<index>\d+)\s+(?P<old>.+)\s+with\s+(?P<new>.+)\b",
                r"\b(replace)\s+note\s+(?P<index>\d+)\s+(?P<old>.+)\s+with\s+(?P<new>.+)\b",
            ],
            triggers=["zameni v zametke", "замени в заметке", "замени заметку"],
            examples=["replace in note 1 milk with bread", "replace note 2 coffee with tea"],
            examples_ru=["замени в заметке 1 молоко на хлеб"],
            examples_en=["replace in note 1 milk with bread", "replace note 2 coffee with tea"],
            group="notes",
            parameters_schema={"index": "optional", "old": "string", "new": "string"},
            handler=_handle_note_replace,
        )
    )

    registry.register(
        _cmd(
            name="timer_set",
            description="Set a timer",
            patterns=[
                r"\b(поставь|установи)\s+таймер\s+на\s+(?P<duration>.+)\b",
                r"\bтаймер\s+на\s+(?P<duration>.+)\b",
                r"\b(postav|ustanovi)\s+(timer|taymer)\s+na\s+(?P<duration>.+)\b",
                r"\b(set|start)\s+(a\s+)?timer\s+(for|in)\s+(?P<duration>.+)\b",
                r"\b(timer|taymer)\s+(for|in)\s+(?P<duration>.+)\b",
                r"\b(timer|taymer)\s+na\s+(?P<duration>.+)\b",
            ],
            triggers=["postav timer", "ustanovi timer", "postav taymer", "ustanovi taymer", "timer na", "taymer na"],
            examples=["set a timer for 10 seconds", "set a timer for 5 minutes"],
            examples_ru=[
                "поставь таймер на 10 секунд",
                "поставь таймер на 5 минут",
                "поставь таймер на 1 минуту",
                "поставь таймер на 3 минуты",
                "поставь таймер на 30 секунд",
                "таймер на 45 секунд",
                "таймер на 2 минуты",
                "поставь таймер на 7 минут",
            ],
            examples_en=["set a timer for 10 seconds", "set a timer for 5 minutes", "timer for 30 sec", "timer in 1 min", "set timer for 2 minutes", "start a timer for 15 sec", "timer for 45 seconds", "set a timer in 3 minutes"],
            group="timers",
            parameters_schema={"duration": "string"},
            handler=_handle_timer_set,
        )
    )

    registry.register(
        _cmd(
            name="alarm_set",
            description="Set alarm",
            patterns=[
                r"\b(postav|ustanovi)\s+budilnik\s+na\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\b(set|create)\s+(an?\s+)?alarm\s+(for|at)\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\balarm\s+(for|at)\s+(?P<time>\d{1,2}:\d{2})\b",
            ],
            triggers=["postav budilnik", "budilnik na"],
            examples=["set an alarm for 07:30", "alarm at 08:00"],
            examples_ru=[
                "поставь будильник на 07:30",
                "поставь будильник на 08:00",
                "поставь будильник на 06:45",
                "поставь будильник на 21:00",
                "поставь будильник на 06:30",
                "поставь будильник на 07:00",
                "поставь будильник на 09:15",
                "поставь будильник на 08:10",
            ],
            examples_en=["set an alarm for 07:30", "alarm at 08:00", "set alarm for 06:45", "alarm at 21:00", "set an alarm at 09:15", "alarm at 06:30", "set an alarm for 07:00", "alarm at 22:10"],
            group="alarms",
            parameters_schema={"time": "string"},
            handler=_handle_alarm_set,
        )
    )

    registry.register(
        _cmd(
            name="reminder_set",
            description="Create reminder",
            patterns=[
                r"\bнапомни( мне)?\s+(?P<what>.+)\s+в\s+(?P<time>\d{1,2}[:\s]\d{2})\b",
                r"\bнапомни( мне)?\s+(?P<what>.+)\s+через\s+(?P<duration>.+)\b",
                r"\bnapomni( mne)?\s+(?P<what>.+)\s+v\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\bnapomni( mne)?\s+(?P<what>.+)\s+cherez\s+(?P<duration>.+)\b",
                r"\b(remind me)\s+to\s+(?P<what>.+)\s+at\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\b(remind me)\s+in\s+(?P<duration>.+)\b",
            ],
            triggers=["napomni", "napominanie"],
            examples=["remind me to buy bread at 18:30", "remind me in 5 minutes"],
            examples_ru=[
                "напомни мне купить хлеб в 18:30",
                "напомни мне позвонить в 19:00",
                "напомни мне отправить отчет в 09:00",
                "напомни мне про встречу в 15:30",
                "напомни мне сделать перерыв через 10 минут",
                "напомни мне выпить воду через 30 минут",
                "напомни мне позвонить через 1 час",
                "напомни мне проверить почту через 2 часа",
            ],
            examples_en=["remind me to buy bread at 18:30", "remind me in 5 minutes", "remind me to call mom at 19:00", "remind me in 1 hour", "remind me in 30 minutes", "remind me to send report at 09:00", "remind me in 10 minutes", "remind me in 2 hours"],
            group="reminders",
            parameters_schema={"what": "string", "time": "optional", "duration": "optional"},
            handler=_handle_reminder_set,
        )
    )

    registry.register(
        _cmd(
            name="volume_set",
            description="Volume control",
            patterns=[
                r"\b(sdelai gromche|pribav gromkost|gromche)\b",
                r"\b(sdelai tishe|ubav gromkost|tishe)\b",
                r"\b(vykluchi zvuk|mut|bez zvuka)\b",
                r"\b(make it louder|turn it up|volume up)\b",
                r"\b(make it quieter|turn it down|volume down)\b",
                r"\bgromkost\s+na\s+(?P<level>\d{1,3})\b",
                r"\bgromkost\s+(?P<level>\d{1,3})\b",
                r"\b(set|change)\s+volume\s+(to\s+)?(?P<level>\d+)\b",
                r"\bvolume\s+(?P<level>\d+)\b",
            ],
            triggers=["gromche", "tishe", "gromkost", "vykluchi zvuk"],
            examples=["set volume to 40", "volume 70"],
            examples_ru=["сделай громкость 40", "сделай тише"],
            examples_en=["set volume to 40", "volume 70", "make it louder", "make it quieter"],
            group="system",
            parameters_schema={"level": "optional"},
            handler=_handle_volume_set,
        )
    )

    registry.register(
        _cmd(
            name="chat",
            description="Chat",
            patterns=[
                r"\b(pogovori so mnoy|pogovori so mnoi|davai pogovorim|davay pogovorim)\b(?P<topic>.*)",
                r"\b(obyasni|obyyasni)\s+(?P<topic>.+)\b",
                r"\b(perevedi)\s+(?P<topic>.+)\b",
                r"\b(pridumai|pridumay)\s+(?P<topic>.+)\b",
                r"\b(talk to me|let's talk)\b(?P<topic>.*)",
                r"\b(explain|translate|write|create)\s+(?P<topic>.+)\b",
            ],
            triggers=["pogovori so mnoi", "pogovori so mnoy", "davai pogovorim", "davay pogovorim", "obyasni", "obyyasni", "perevedi", "pridumai", "pridumay"],
            examples=["talk to me", "explain neural networks"],
            examples_ru=[
                "поговори со мной",
                "давай поговорим",
                "объясни что такое нейросети",
                "объясни как работает интернет",
                "переведи этот текст",
                "переведи фразу",
                "придумай историю",
                "поговори со мной о фильмах",
            ],
            examples_en=[
                "talk to me",
                "let's talk",
                "explain neural networks",
                "explain how it works",
                "translate this text",
                "write a short story",
                "create a poem",
                "translate this",
            ],
            group="chat",
            parameters_schema={"topic": "optional"},
            handler=_handle_chat,
        )
    )

    registry.register(
        _cmd(
            name="settings_tts",
            description="Toggle voice",
            patterns=[
                r"\b(vklyuchi|vyklyuchi|vykluchi)\s+golos\b",
                r"\b(enable|disable|turn on|turn off)\s+voice\b",
            ],
            triggers=["vklyuchi golos", "vyklyuchi golos", "vykluchi golos", "vklyuchi zvuk", "vyklyuchi zvuk", "vykluchi zvuk"],
            examples=["enable voice", "disable voice"],
            examples_ru=["включи голос", "выключи голос", "включи звук", "выключи звук"],
            examples_en=["enable voice", "disable voice", "turn on voice", "turn off voice"],
            group="voice",
            parameters_schema={},
            handler=_handle_toggle_tts,
        )
    )

    registry.register(
        _cmd(
            name="settings_language",
            description="Set language",
            patterns=[
                r"\b(ustanovi|postav|sdelay)\s+ya(?:zyk|zik)\s+(?P<lang>ru|en|auto)\b",
                r"\b(set)\s+language\s+(to\s+)?(?P<lang>ru|en|auto|russian|english)\b",
            ],
            triggers=["ustanovi yazyk", "установи язык"],
            examples=["set language to english", "set language to russian"],
            examples_ru=["установи язык русский", "установи язык английский"],
            examples_en=["set language to english", "set language to russian", "set language auto"],
            group="settings",
            parameters_schema={"lang": "string"},
            handler=_handle_set_language,
        )
    )

    registry.register(
        _cmd(
            name="settings_theme",
            description="Set theme",
            patterns=[
                r"\b(ustanovi|postav|sdelay)\s+temu\s+(?P<preset>temnaya|dark|midnight|neon)\b",
                r"\b(set)\s+theme\s+(?P<preset>dark|midnight|neon)\b",
            ],
            triggers=["ustanovi temu", "установи тему"],
            examples=["set theme neon", "set theme dark"],
            examples_ru=["установи тему неон", "поставь тему темная"],
            examples_en=["set theme neon", "set theme dark"],
            group="settings",
            parameters_schema={"preset": "string"},
            handler=_handle_set_theme,
        )
    )

    registry.register(
        _cmd(
            name="settings_accent",
            description="Set accent color",
            patterns=[
                r"\b(ustanovi|postav|sdelay)\s+(accent|aktsent)\s+(?P<color>#?[0-9a-fA-F]{6})\b",
                r"\b(set)\s+accent\s+(?P<color>#?[0-9a-fA-F]{6})\b",
            ],
            triggers=["ustanovi accent", "ustanovi aktsent", "установи акцент"],
            examples=["set accent #7dd3fc", "set accent #ff6b6b"],
            examples_ru=["установи акцент #7dd3fc"],
            examples_en=["set accent #7dd3fc", "set accent #ff6b6b"],
            group="settings",
            parameters_schema={"color": "string"},
            handler=_handle_set_accent,
        )
    )

    registry.register(
        _cmd(
            name="settings_bg_intensity",
            description="Set background intensity",
            patterns=[
                r"\b(ustanovi|postav|sdelay)\s+fon\s+(?P<value>\d{1,3})\b",
                r"\b(set)\s+background\s+(?P<value>\d{1,3})\b",
            ],
            triggers=["ustanovi fon", "установи фон"],
            examples=["set background 70", "set background 40"],
            examples_ru=["установи фон 70"],
            examples_en=["set background 70", "set background 40"],
            group="settings",
            parameters_schema={"value": "string"},
            handler=_handle_set_bg_intensity,
        )
    )

    registry.register(
        _cmd(
            name="settings_tts_rate",
            description="Set TTS rate",
            patterns=[
                r"\b(ustanovi|postav)\s+skorost\s+(?P<value>\d{2,3})\b",
                r"\b(set)\s+voice\s+rate\s+(?P<value>\d{2,3})\b",
            ],
            triggers=["ustanovi skorost", "установи скорость"],
            examples=["set voice rate 180", "set voice rate 200"],
            examples_ru=["установи скорость 180"],
            examples_en=["set voice rate 180", "set voice rate 200"],
            group="settings",
            parameters_schema={"value": "string"},
            handler=_handle_set_tts_rate,
        )
    )

    registry.register(
        _cmd(
            name="settings_tts_volume",
            description="Set TTS volume",
            patterns=[
                r"\b(ustanovi|postav)\s+gromkost\s+golosa\s+(?P<value>\d{1,3})\b",
                r"\b(set)\s+voice\s+volume\s+(?P<value>\d{1,3})\b",
            ],
            triggers=["ustanovi gromkost golosa", "установи громкость голоса"],
            examples=["set voice volume 70", "set voice volume 40"],
            examples_ru=["установи громкость голоса 70"],
            examples_en=["set voice volume 70", "set voice volume 40"],
            group="settings",
            parameters_schema={"value": "string"},
            handler=_handle_set_tts_volume,
        )
    )

    registry.register(
        _cmd(
            name="weather",
            description="Weather",
            patterns=[
                r"\b(pogoda)(\s+v\s+(?P<query>.+))?\b",
                r"\b(погода)(\s+в\s+(?P<query>.+))?\b",
            ],
            triggers=["pogoda", "погода"],
            examples=["погода в москве", "pogoda v spb"],
            parameters_schema={"query": "optional"},
            handler=_handle_weather,
        )
    )

    registry.register(
        _cmd(
            name="event_add",
            description="Add calendar event",
            patterns=[
                r"\b(sozdai|sdelai|dobav)\s+sobyti[e|ya]\s+(?P<title>.+)\s+na\s+(?P<date>\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}[-./]\d{1,2}[-./]\d{1,2})\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\b(создай|сделай|добавь)\s+событи[е|я]\s+(?P<title>.+)\s+на\s+(?P<date>\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}[-./]\d{1,2}[-./]\d{1,2})\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\b(создай|сделай|добавь)\s+событи[е|я]\s+(?P<title>.+)\s+на\s+(?P<time>\d{1,2}:\d{2})\b",
            ],
            triggers=["создай событие", "сделай событие", "add event"],
            examples=["создай событие встреча на 15:30", "создай событие звонок на 10.02.2026 14:00"],
            parameters_schema={"title": "string", "date": "optional", "time": "optional"},
            handler=_handle_event_add,
        )
    )

    registry.register(
        _cmd(
            name="event_list",
            description="List calendar events",
            patterns=[r"\b(pokazhi sobytiya|spisok sobytiy|kalendar)\b", r"\b(покажи события|список событий|календарь)\b"],
            triggers=["pokazhi sobytiya", "покажи события", "календарь"],
            examples=["покажи события", "календарь"],
            handler=_handle_event_list,
        )
    )

    registry.register(
        _cmd(
            name="settings_wake",
            description="Toggle wake word",
            patterns=[
                r"\b(vklyuchi|vyklyuchi|vykluchi)\s+proslushku\b",
                r"\b(vklyuchi|vyklyuchi|vykluchi)\s+(wake word|hotword)\b",
                r"\b(enable|disable|turn on|turn off)\s+(wake word|hotword)\b",
            ],
            triggers=[
                "vklyuchi proslushku",
                "vyklyuchi proslushku",
                "vykluchi proslushku",
                "vklyuchi wake word",
                "vyklyuchi wake word",
                "vykluchi wake word",
            ],
            examples=["enable wake word", "disable wake word"],
            examples_ru=["включи прослушку", "выключи прослушку", "включи wake word", "выключи wake word"],
            examples_en=["enable wake word", "disable wake word", "turn on wake word", "turn off wake word"],
            group="voice",
            handler=_handle_toggle_wake,
        )
    )

    registry.register(
        _cmd(
            name="clear_chat",
            description="Clear chat",
            patterns=[
                r"\b(очисти|очистить)\s+чат\b",
                r"\bудали\s+историю\s+чата\b",
                r"\b(ochisti|ochistit|sbroc|sbros)\s+chat\b",
                r"\b(clear|reset)\s+chat\b",
            ],
            triggers=[
                "ochisti chat",
                "udali istoriyu chata",
                "udalit istoriyu chata",
                "sbros dialog",
                "sbros chat",
                "clear chat",
                "clear conversation",
                "reset dialog",
            ],
            examples=["clear chat", "reset chat"],
            examples_ru=["очисти чат", "сбрось чат"],
            examples_en=["clear chat", "reset chat"],
            group="system",
            handler=_handle_clear_chat,
        )
    )

    registry.register(
        _cmd(
            name="exit",
            description="Exit",
            patterns=[
                r"\b(vykhod|vyhod|poka|zavershit)\b",
                r"\b(exit|quit|bye)\b",
            ],
            triggers=["vykhod", "vyhod", "stop", "poka", "zakroy"],
            examples=["exit", "bye"],
            examples_ru=["выход", "пока"],
            examples_en=["exit", "bye"],
            group="system",
            handler=_handle_exit,
        )
    )

    return registry


def _handle_help(ctx: CommandContext) -> ActionResult:
    return ActionResult(
        text=_t(ctx, "msg_help_opened"),
        action="help",
        title=_t(ctx, "action_help_title"),
        details="",
    )


def _handle_greet(ctx: CommandContext) -> str:
    return _t(ctx, "msg_greet")


def _handle_time(ctx: CommandContext) -> str:
    now = datetime.now()
    return _t(ctx, "msg_time", time=f"{now:%H:%M}")


def _handle_date(ctx: CommandContext) -> str:
    now = datetime.now()
    weekday = now.strftime("%A")
    return _t(ctx, "msg_date", date=f"{now:%d.%m.%Y}", weekday=weekday)


def _handle_tts_test(ctx: CommandContext) -> ActionResult:
    return ActionResult(
        text=_t(ctx, "msg_tts_test"),
        action="tts_test",
        title=_t(ctx, "action_tts_test_title"),
        details=_t(ctx, "msg_tts_test"),
    )


def _handle_open_url(ctx: CommandContext) -> ActionResult | str:
    url = ctx.slots.get("url")
    if not url:
        site = ctx.slots.get("site")
        if site:
            custom_sites = (load_settings().get("custom_sites") or {})
            url = resolve_site(site, custom_sites)
    if not url:
        return _t(ctx, "msg_site_unknown")
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_open_site_ok" if ok else "msg_open_site_fail"),
        action="open_url",
        title=_t(ctx, "action_open_site_title"),
        details=url,
        status=status,
        url=url,
    )


def _handle_open_mail(ctx: CommandContext) -> ActionResult:
    text = normalize_match_text(ctx.text)
    provider = "gmail"
    if "yandex" in text or "yandeks" in text or "яндекс" in ctx.text.lower():
        provider = "yandex"
    elif "yahoo" in text or "яху" in ctx.text.lower():
        provider = "yahoo"
    elif "proton" in text or "протон" in ctx.text.lower():
        provider = "proton"
    elif "zoho" in text or "зохо" in ctx.text.lower():
        provider = "zoho"
    elif "fastmail" in text or "фастмейл" in ctx.text.lower():
        provider = "fastmail"
    elif "tuta" in text or "тута" in ctx.text.lower():
        provider = "tuta"
    elif "mail ru" in text or "mail.ru" in text:
        provider = "mailru"
    elif "outlook" in text or "аутлук" in ctx.text.lower():
        provider = "outlook"
    elif "icloud" in text or "айклауд" in ctx.text.lower():
        provider = "icloud"

    url_map = {
        "gmail": "https://mail.google.com/",
        "yandex": "https://mail.yandex.ru/",
        "yahoo": "https://mail.yahoo.com/",
        "proton": "https://mail.proton.me/",
        "zoho": "https://mail.zoho.com/",
        "fastmail": "https://www.fastmail.com/",
        "tuta": "https://mail.tutanota.com/",
        "mailru": "https://e.mail.ru/",
        "outlook": "https://outlook.live.com/mail/",
        "icloud": "https://www.icloud.com/mail",
    }
    label_map = {
        "gmail": "Gmail",
        "yandex": "Yandex Mail",
        "yahoo": "Yahoo Mail",
        "proton": "Proton Mail",
        "zoho": "Zoho Mail",
        "fastmail": "Fastmail",
        "tuta": "Tuta Mail",
        "mailru": "Mail.ru",
        "outlook": "Outlook",
        "icloud": "iCloud Mail",
    }
    url = url_map.get(provider, "https://mail.google.com/")
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_mail_ok" if ok else "msg_mail_fail"),
        action="open_mail",
        title=_t(ctx, "action_mail_title"),
        details=label_map.get(provider, "Mail"),
        status=status,
        url=url,
    )


def _handle_open_calendar(ctx: CommandContext) -> ActionResult:
    url = "https://calendar.google.com/"
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_calendar_ok" if ok else "msg_calendar_fail"),
        action="open_calendar",
        title=_t(ctx, "action_calendar_title"),
        details="Google Calendar",
        status=status,
        url=url,
    )

def _handle_search_web(ctx: CommandContext) -> ActionResult | str:
    query = (ctx.slots.get("query") or "").strip()
    if not query:
        return _t(ctx, "msg_search_empty")
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_search_ok" if ok else "msg_search_fail"),
        action="search_web",
        title=_t(ctx, "action_search_title"),
        details=query,
        status=status,
        url=url,
    )


def _handle_open_map(ctx: CommandContext) -> ActionResult:
    query = (ctx.slots.get("query") or "").strip()
    if query:
        url = f"https://yandex.ru/maps/?text={quote_plus(query)}"
    else:
        url = "https://yandex.ru/maps"
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_map_ok" if ok else "msg_map_fail"),
        action="open_map",
        title=_t(ctx, "action_map_title"),
        details=query or _t(ctx, "map_default_name"),
        status=status,
        url=url,
    )


def _handle_open_path(ctx: CommandContext) -> ActionResult | str:
    path = ctx.slots.get("path")
    if not path:
        return _t(ctx, "msg_path_unknown")
    known = resolve_known_path(path)
    if known:
        path = known
    ok = open_path(path)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_open_path_ok" if ok else "msg_open_path_fail"),
        action="open_path",
        title=_t(ctx, "action_open_path_title"),
        details=path,
        status=status,
    )


def _handle_open_app(ctx: CommandContext) -> ActionResult | str:
    app = (ctx.slots.get("app") or "").strip()
    if not app:
        return _t(ctx, "msg_app_unknown")
    if sys.platform != "win32":
        return _t(ctx, "msg_windows_only")
    custom_apps = (load_settings().get("custom_apps") or {})
    resolved = resolve_app(app, custom_apps) or app
    ok = run_app(resolved)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_open_app_ok" if ok else "msg_open_app_fail"),
        action="open_app",
        title=_t(ctx, "action_open_app_title"),
        details=resolved,
        status=status,
    )


def _handle_note_create(ctx: CommandContext) -> ActionResult | str:
    note = (ctx.slots.get("note") or "").strip()
    if not note:
        return _t(ctx, "msg_note_empty")
    add_note(ctx.app_context.data_dir, note)
    return ActionResult(
        text=_t(ctx, "msg_note_saved"),
        action="note_create",
        title=_t(ctx, "action_note_title"),
        details=note,
        status="ok",
    )


def _handle_note_list(ctx: CommandContext) -> ActionResult:
    notes = list_notes(ctx.app_context.data_dir)
    if not notes:
        return ActionResult(
            text=_t(ctx, "msg_notes_empty"),
            action="note_list",
            title=_t(ctx, "action_notes_title"),
            details=_t(ctx, "msg_notes_empty"),
            status="ok",
        )
    lines = [f"{idx+1}. {n.get('text','')}" for idx, n in enumerate(notes[-10:])]
    return ActionResult(
        text=_t(ctx, "msg_notes_list"),
        action="note_list",
        title=_t(ctx, "action_notes_title"),
        details="\n".join(lines),
        status="ok",
    )


def _handle_note_delete(ctx: CommandContext) -> ActionResult | str:
    raw = (ctx.slots.get("index") or "").strip()
    if not raw.isdigit():
        return _t(ctx, "msg_note_index")
    idx = int(raw)
    ok = delete_note(ctx.app_context.data_dir, idx)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_note_deleted" if ok else "msg_note_delete_fail"),
        action="note_delete",
        title=_t(ctx, "action_note_delete_title"),
        details=f"#{idx}",
        status=status,
    )


def _handle_note_update(ctx: CommandContext) -> ActionResult | str:
    raw = (ctx.slots.get("index") or "").strip()
    note = (ctx.slots.get("note") or "").strip()
    if not raw.isdigit() or not note:
        return _t(ctx, "msg_note_update_fail")
    idx = int(raw)
    ok = update_note(ctx.app_context.data_dir, idx, note)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_note_updated" if ok else "msg_note_not_found"),
        action="note_update",
        title=_t(ctx, "action_note_update_title"),
        details=f"#{idx}: {note}" if ok else f"#{idx}",
        status=status,
    )


def _handle_note_replace(ctx: CommandContext) -> ActionResult | str:
    old = (ctx.slots.get("old") or "").strip()
    new = (ctx.slots.get("new") or "").strip()
    if not old or not new:
        return _t(ctx, "msg_note_replace_fail")

    idx_raw = (ctx.slots.get("index") or "").strip()
    idx = int(idx_raw) if idx_raw.isdigit() else None
    if idx is None:
        idx = find_note_index(ctx.app_context.data_dir, old)
        if idx is None:
            return _t(ctx, "msg_note_not_found")

    ok = replace_in_note(ctx.app_context.data_dir, idx, old, new)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_note_replaced" if ok else "msg_note_replace_fail"),
        action="note_replace",
        title=_t(ctx, "action_note_replace_title"),
        details=f"#{idx}: {old} -> {new}",
        status=status,
    )


def _handle_timer_set(ctx: CommandContext) -> ActionResult | str:
    duration_text = (ctx.slots.get("duration") or "").strip()
    seconds = parse_duration_seconds(duration_text)
    if not seconds:
        return _t(ctx, "msg_timer_duration")
    ctx.app_context.scheduler.schedule_in(
        seconds,
        _t(ctx, "msg_timer_fired"),
        meta={"type": "timer", "duration_sec": seconds, "duration_text": duration_text},
    )
    end_time = datetime.now() + timedelta(seconds=seconds)
    return ActionResult(
        text=_t(ctx, "msg_timer_set"),
        action="timer_set",
        title=_t(ctx, "action_timer_title"),
        details=f"{end_time:%H:%M}",
        status="ok",
    )


def _handle_alarm_set(ctx: CommandContext) -> ActionResult | str:
    time_text = (ctx.slots.get("time") or "").strip()
    when = parse_time_of_day(time_text)
    if not when:
        return _t(ctx, "msg_alarm_time")
    seconds = max(0, int((when - datetime.now()).total_seconds()))
    ctx.app_context.scheduler.schedule_in(
        seconds,
        _t(ctx, "msg_alarm_fired"),
        meta={"type": "alarm", "time": time_text},
    )
    return ActionResult(
        text=_t(ctx, "msg_alarm_set"),
        action="alarm_set",
        title=_t(ctx, "action_alarm_title"),
        details=f"{when:%H:%M}",
        status="ok",
    )


def _handle_reminder_set(ctx: CommandContext) -> ActionResult | str:
    what = (ctx.slots.get("what") or "").strip()
    if not what:
        return _t(ctx, "msg_reminder_text")

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
        return _t(ctx, "msg_reminder_time")

    add_reminder(ctx.app_context.data_dir, what, when)
    ctx.app_context.scheduler.schedule_in(
        delay_seconds,
        _t(ctx, "msg_reminder_prefix", text=what),
        meta={"type": "reminder", "text": what, "delay_sec": delay_seconds},
    )
    return ActionResult(
        text=_t(ctx, "msg_reminder_set"),
        action="reminder_set",
        title=_t(ctx, "action_reminder_title"),
        details=f"{what} ({when:%H:%M})" if when else what,
        status="ok",
    )


def _handle_volume_set(ctx: CommandContext) -> ActionResult | str:
    text = normalize_match_text(ctx.text)
    controller = ctx.app_context.volume
    if controller is None:
        return _t(ctx, "msg_volume_fail")

    level = ctx.slots.get("level")
    if level and level.isdigit():
        target = max(0, min(100, int(level))) / 100.0
        ok = controller.set_absolute(target)
        status = "ok" if ok else "error"
        return ActionResult(
            text=_t(ctx, "msg_volume_changed" if ok else "msg_volume_fail"),
            action="volume_set",
            title=_t(ctx, "action_volume_title"),
            details=f"{int(target*100)}%",
            status=status,
        )

    if "gromche" in text or "pribav" in text:
        ok = controller.change_relative(0.1)
        status = "ok" if ok else "error"
        return ActionResult(
            text=_t(ctx, "msg_louder" if ok else "msg_volume_fail"),
            action="volume_set",
            title=_t(ctx, "action_volume_title"),
            details="+10%",
            status=status,
        )
    if "tishe" in text or "ubav" in text:
        ok = controller.change_relative(-0.1)
        status = "ok" if ok else "error"
        return ActionResult(
            text=_t(ctx, "msg_quieter" if ok else "msg_volume_fail"),
            action="volume_set",
            title=_t(ctx, "action_volume_title"),
            details="-10%",
            status=status,
        )
    if "vykluchi zvuk" in text or "mut" in text or "bez zvuka" in text:
        ok = controller.set_mute(True)
        status = "ok" if ok else "error"
        return ActionResult(
            text=_t(ctx, "msg_mute" if ok else "msg_volume_fail"),
            action="volume_set",
            title=_t(ctx, "action_volume_title"),
            details="mute",
            status=status,
        )

    return _t(ctx, "msg_volume_cmd")


def _handle_chat(ctx: CommandContext) -> str:
    llm_client = ctx.app_context.llm_client
    if llm_client is None:
        return _t(ctx, "msg_ai_unavailable_cmd")
    topic = (ctx.slots.get("topic") or "").strip()
    if not topic:
        return _t(ctx, "msg_chat_prompt")
    return llm_client.ask(topic)


def _handle_toggle_tts(ctx: CommandContext) -> ActionResult:
    t = normalize_match_text(ctx.text)
    settings = load_settings()
    enable = "vklyuchi" in t
    settings.setdefault("tts", {})["enabled"] = bool(enable)
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_tts_on" if enable else "msg_tts_off"),
        action="settings_tts",
        title=_t(ctx, "action_voice_title"),
        details=_t(ctx, "state_on" if enable else "state_off"),
        status="ok",
    )


def _handle_toggle_wake(ctx: CommandContext) -> ActionResult:
    t = normalize_match_text(ctx.text)
    settings = load_settings()
    enable = "vklyuchi" in t
    settings.setdefault("ui", {})["wake_word"] = bool(enable)
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_wake_on" if enable else "msg_wake_off"),
        action="settings_wake",
        title=_t(ctx, "action_wake_title"),
        details=_t(ctx, "state_on" if enable else "state_off"),
        status="ok",
    )


def _handle_set_language(ctx: CommandContext) -> ActionResult | str:
    raw = normalize_match_text(ctx.slots.get("lang") or "")
    mapping = {
        "ru": "ru",
        "rus": "ru",
        "russkiy": "ru",
        "russkii": "ru",
        "russki": "ru",
        "en": "en",
        "english": "en",
        "angliyskiy": "en",
        "auto": "auto",
    }
    lang = mapping.get(raw)
    if lang is None:
        return _t(ctx, "msg_lang_unknown")
    settings = load_settings()
    settings.setdefault("app", {})["language"] = lang
    settings.setdefault("stt", {})["language"] = lang
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_settings_updated"),
        action="settings_language",
        title=_t(ctx, "action_settings_title"),
        details=f"{lang.upper()}",
        status="ok",
    )


def _handle_set_theme(ctx: CommandContext) -> ActionResult | str:
    raw = normalize_match_text(ctx.slots.get("preset") or "")
    mapping = {
        "dark": "dark",
        "temnaya": "dark",
        "nochnaya": "midnight",
        "midnight": "midnight",
        "neon": "neon",
        "neonovaya": "neon",
    }
    preset = mapping.get(raw)
    if preset is None:
        return _t(ctx, "msg_theme_unknown")
    settings = load_settings()
    settings.setdefault("ui", {})["theme_preset"] = preset
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_settings_updated"),
        action="settings_theme",
        title=_t(ctx, "action_settings_title"),
        details=preset.title(),
        status="ok",
    )


def _handle_set_accent(ctx: CommandContext) -> ActionResult | str:
    color = (ctx.slots.get("color") or "").strip()
    if not color:
        return _t(ctx, "msg_accent_invalid")
    if not color.startswith("#"):
        color = f"#{color}"
    if len(color) != 7:
        return _t(ctx, "msg_accent_invalid")
    settings = load_settings()
    settings.setdefault("ui", {})["accent_color"] = color
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_settings_updated"),
        action="settings_accent",
        title=_t(ctx, "action_settings_title"),
        details=color,
        status="ok",
    )


def _handle_set_bg_intensity(ctx: CommandContext) -> ActionResult | str:
    raw = (ctx.slots.get("value") or "").strip()
    if not raw.isdigit():
        return _t(ctx, "msg_value_invalid")
    value = max(0, min(100, int(raw)))
    settings = load_settings()
    settings.setdefault("ui", {})["background_intensity"] = float(value) / 100.0
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_settings_updated"),
        action="settings_bg_intensity",
        title=_t(ctx, "action_settings_title"),
        details=f"{value}%",
        status="ok",
    )


def _handle_set_tts_rate(ctx: CommandContext) -> ActionResult | str:
    raw = (ctx.slots.get("value") or "").strip()
    if not raw.isdigit():
        return _t(ctx, "msg_value_invalid")
    value = max(100, min(240, int(raw)))
    settings = load_settings()
    settings.setdefault("tts", {})["rate"] = value
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_settings_updated"),
        action="settings_tts_rate",
        title=_t(ctx, "action_settings_title"),
        details=str(value),
        status="ok",
    )


def _handle_set_tts_volume(ctx: CommandContext) -> ActionResult | str:
    raw = (ctx.slots.get("value") or "").strip()
    if not raw.isdigit():
        return _t(ctx, "msg_value_invalid")
    value = max(0, min(100, int(raw)))
    settings = load_settings()
    settings.setdefault("tts", {})["volume"] = float(value) / 100.0
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=_t(ctx, "msg_settings_updated"),
        action="settings_tts_volume",
        title=_t(ctx, "action_settings_title"),
        details=f"{value}%",
        status="ok",
    )


def _handle_weather(ctx: CommandContext) -> ActionResult | str:
    query = (ctx.slots.get("query") or "").strip()
    if query:
        search = f"{_t(ctx, 'msg_weather_query')}: {query}"
        url = f"https://www.google.com/search?q={quote_plus('weather ' + query)}"
    else:
        search = _t(ctx, "msg_weather_query_default")
        url = "https://www.google.com/search?q=weather"
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=_t(ctx, "msg_weather_ok" if ok else "msg_weather_fail"),
        action="weather",
        title=_t(ctx, "action_weather_title"),
        details=search,
        status=status,
        url=url,
    )


def _handle_event_add(ctx: CommandContext) -> ActionResult | str:
    title = (ctx.slots.get("title") or "").strip()
    if not title:
        return _t(ctx, "msg_event_title")
    date_raw = (ctx.slots.get("date") or "").strip()
    time_raw = (ctx.slots.get("time") or "").strip()
    when = None
    if date_raw and time_raw:
        when = parse_date_time(date_raw, time_raw)
    elif time_raw:
        when = parse_time_of_day(time_raw)
    elif date_raw:
        date = parse_date(date_raw)
        if date is not None:
            when = date.replace(hour=9, minute=0, second=0, microsecond=0)
    add_event(ctx.app_context.data_dir, title, when)
    return ActionResult(
        text=_t(ctx, "msg_event_added"),
        action="event_add",
        title=_t(ctx, "action_event_title"),
        details=f"{title} ({when:%Y-%m-%d %H:%M})" if when else title,
        status="ok",
    )


def _handle_event_list(ctx: CommandContext) -> ActionResult:
    events = list_events(ctx.app_context.data_dir)
    if not events:
        return ActionResult(
            text=_t(ctx, "msg_events_empty"),
            action="event_list",
            title=_t(ctx, "action_event_title"),
            details=_t(ctx, "msg_events_empty"),
            status="ok",
        )
    lines = []
    for idx, ev in enumerate(events[-10:], start=1):
        title = ev.get("title", "")
        when = ev.get("when", "")
        lines.append(f"{idx}. {title} {when}".strip())
    return ActionResult(
        text=_t(ctx, "msg_events_list"),
        action="event_list",
        title=_t(ctx, "action_event_title"),
        details="\n".join(lines),
        status="ok",
    )


def _handle_clear_chat(ctx: CommandContext) -> ActionResult:
    return ActionResult(
        text=_t(ctx, "msg_chat_cleared"),
        action="clear_chat",
        title=_t(ctx, "msg_chat_cleared"),
        details="",
        status="ok",
    )


def _handle_exit(_: CommandContext) -> str:
    return "__EXIT__"


def _handle_screenshot(ctx: CommandContext) -> ActionResult:
    try:
        from PIL import ImageGrab  # type: ignore
    except Exception:
        return ActionResult(
            text=_t(ctx, "msg_screenshot_unavailable"),
            action="screenshot",
            title="Screenshot",
            details="Install pillow to enable screenshots.",
            status="error",
        )

    out_dir = Path("data") / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        img = ImageGrab.grab()
        img.save(path)
        return ActionResult(
            text=_t(ctx, "msg_screenshot_saved"),
            action="screenshot",
            title="Screenshot",
            details=str(path),
            status="ok",
        )
    except Exception as e:  # noqa: BLE001
        return ActionResult(
            text=_t(ctx, "msg_screenshot_failed"),
            action="screenshot",
            title="Screenshot",
            details=str(e),
            status="error",
        )
