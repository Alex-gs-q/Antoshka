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
from core.text_norm import normalize_text
from services.app_catalog import resolve_app
from services.notes import add_note, list_notes, delete_note
from services.path_catalog import resolve_known_path
from services.reminders import add_reminder
from services.site_catalog import resolve_site
from services.time_parse import parse_duration_seconds, parse_time_of_day


def _cmd(
    name: str,
    description: str,
    patterns: List[str],
    handler,
    parameters_schema: Dict[str, str] | None = None,
    triggers: List[str] | None = None,
    examples: List[str] | None = None,
) -> Command:
    return Command(
        name=name,
        description=description,
        patterns=compile_patterns(patterns),
        triggers=triggers or [],
        examples=examples or [],
        parameters_schema=parameters_schema or {},
        handler=handler,
    )


def create_registry() -> CommandRegistry:
    registry = CommandRegistry()

    registry.register(
        _cmd(
            name="help",
            description="Spisok komand",
            patterns=[r"\b(pomoshch|spravka|chto ty umeesh|komandy|pokazhi komandy)\b"],
            triggers=[
                "pomoshch",
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
            examples=[
                "antoshka pomoshch",
                "pomoshch",
                "chto ty umeesh",
                "pokazhi komandy",
                "spravka",
                "komandy",
                "help",
            ],
            handler=_handle_help,
        )
    )

    registry.register(
        _cmd(
            name="greet",
            description="Privetstvie",
            patterns=[r"\b(privet|zdravstvuy|dobryy (den|vecher|utro))\b"],
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
            examples=[
                "privet",
                "privet antoshka",
                "dobryy den",
                "dobryy vecher",
                "zdravstvuy",
            ],
            handler=_handle_greet,
        )
    )

    registry.register(
        _cmd(
            name="time",
            description="Tekuschee vremya",
            patterns=[r"\b(kotoryy chas|skolko vremeni|vremya)\b"],
            triggers=[
                "kotoryy chas",
                "skolko vremeni",
                "vremya",
                "kakoe seychas vremya",
                "skazhi vremya",
                "vremya seychas",
                "time",
            ],
            examples=[
                "skolko vremeni",
                "kotoryy chas",
                "skazhi vremya",
            ],
            handler=_handle_time,
        )
    )

    registry.register(
        _cmd(
            name="date",
            description="Tekushchaya data",
            patterns=[r"\b(kakaya data|kakoe segodnya chislo|segodnya kakoe chislo|data|den nedeli)\b"],
            triggers=[
                "kakaya data",
                "kakoe segodnya chislo",
                "segodnya kakoe chislo",
                "data",
                "kakoy den nedeli",
                "den nedeli",
            ],
            examples=[
                "kakaya data",
                "kakoy den nedeli",
                "skazhi datu",
            ],
            handler=_handle_date,
        )
    )

    registry.register(
        _cmd(
            name="tts_test",
            description="Proverka zvuka",
            patterns=[r"\b(skazhi test|test zvuka|prover zvuk|proverka zvuka)\b"],
            triggers=["skazhi test", "test zvuka", "prover zvuk", "proverka zvuka"],
            examples=["antoshka skazhi test", "test zvuka"],
            handler=_handle_tts_test,
        )
    )

    registry.register(
        _cmd(
            name="open_map",
            description="Otkryt kartu",
            patterns=[
                r"\b(otkroy kartu|karta|pokazhi kartu)(\s+(?P<query>.+))?\b",
                r"\b(pokazhi marshrut|marshrut)\s+(?P<query>.+)\b",
            ],
            triggers=["otkroy kartu", "pokazhi kartu", "karta", "pokazhi marshrut"],
            examples=["otkroy kartu", "pokazhi marshrut do doma"],
            parameters_schema={"query": "optional"},
            handler=_handle_open_map,
        )
    )

    registry.register(
        _cmd(
            name="search_web",
            description="Poisk v internete",
            patterns=[
                r"\b(naydi|poisk|ishi|pogugli|zagugli)\s+(?P<query>.+)\b",
                r"\b(naydi v internete|poisk v internete)\s+(?P<query>.+)\b",
            ],
            triggers=["naydi", "poisk", "pogugli", "zagugli", "naydi v internete"],
            examples=["naydi pogodu v moskve", "poisk v internete novosti"],
            parameters_schema={"query": "string"},
            handler=_handle_search_web,
        )
    )

    registry.register(
        _cmd(
            name="open_path",
            description="Otkryt fail ili papku",
            patterns=[
                r"\b(otkroy|otkryt)\s+(fail|papku)\s+(?P<path>.+)\b",
                r"\b(otkroy|otkryt)\s+(?P<path>[a-zA-Z]:\\[^\s].+)\b",
                r"\b(otkroy|otkryt)\s+(?P<path>.+\.(txt|md|pdf|docx|xlsx|pptx|exe|lnk))\b",
                r"\b(otkroy|otkryt)\s+(?P<path>zagruzki|dokumenty|rabochiy stol|downloads|documents|desktop)\b",
            ],
            triggers=["otkroy papku", "otkroy fail", "otkroy zagruzki", "otkroy dokumenty"],
            examples=["otkroy papku zagruzki", "otkroy dokumenty"],
            parameters_schema={"path": "string"},
            handler=_handle_open_path,
        )
    )

    registry.register(
        _cmd(
            name="screenshot",
            description="Sdelat skrinshot",
            patterns=[r"(sdelai skrinshot|sdelai snimok ekrana|screenshot)"],
            triggers=["sdelai skrinshot", "sdelai snimok ekrana", "screenshot"],
            examples=["sdelai skrinshot"],
            handler=_handle_screenshot,
        )
    )

    registry.register(
        _cmd(
            name="open_url",
            description="Otkryt sayt",
            patterns=[
                r"\b(otkroy|otkryt|zaydi|zapusti)\s+(?P<url>https?://\S+)\b",
                r"\b(otkroy|otkryt|zaydi|zapusti)\s+(sait\s+)?(?P<site>[\w\s]+)\b",
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
            examples=[
                "otkroy sait vk",
                "otkroy youtube",
                "otkroy https://vk.com",
                "zaydi na yandex",
                "otkroy telegram",
            ],
            parameters_schema={"url": "optional", "site": "optional"},
            handler=_handle_open_url,
        )
    )

    registry.register(
        _cmd(
            name="open_app",
            description="Otkryt prilozhenie",
            patterns=[r"\b(otkroy|otkryt|zapusti|zapusk)\s+(prilozhenie\s+)?(?P<app>[\w\s\-\.]+)\b"],
            triggers=["otkroy prilozhenie", "zapusti", "otkroy kalkulyator", "otkroy bloknot"],
            examples=["zapusti kalkulyator", "otkroy bloknot"],
            parameters_schema={"app": "string"},
            handler=_handle_open_app,
        )
    )

    registry.register(
        _cmd(
            name="note_delete",
            description="Udalit zametku",
            patterns=[r"\b(udali|udalit)\s+zametk[au]\s+(?P<index>\d+)\b"],
            triggers=["udali zametku"],
            examples=["udali zametku 2"],
            parameters_schema={"index": "string"},
            handler=_handle_note_delete,
        )
    )

    registry.register(
        _cmd(
            name="note_create",
            description="Sozdat zametku",
            patterns=[
                r"\b(sozdai|sdelai|zapishe)\s+zametk[au]\s+(?P<note>.+)\b",
                r"\bzametk[au]\s+(?P<note>.+)\b",
            ],
            triggers=["sozdai zametku", "sdelai zametku", "zametka"],
            examples=["sozdai zametku kupit moloko"],
            parameters_schema={"note": "string"},
            handler=_handle_note_create,
        )
    )

    registry.register(
        _cmd(
            name="note_list",
            description="Pokazat zametki",
            patterns=[r"\b(pokazhi zametki|moi zametki|spisok zametok)\b"],
            triggers=["pokazhi zametki", "moi zametki", "spisok zametok"],
            examples=["pokazhi zametki", "spisok zametok"],
            handler=_handle_note_list,
        )
    )

    registry.register(
        _cmd(
            name="timer_set",
            description="Postavit timer",
            patterns=[r"\b(postav|ustanovi)\s+timer\s+na\s+(?P<duration>.+)\b"],
            triggers=["postav timer", "ustanovi timer", "timer na"],
            examples=["postav timer na 5 minut"],
            parameters_schema={"duration": "string"},
            handler=_handle_timer_set,
        )
    )

    registry.register(
        _cmd(
            name="alarm_set",
            description="Postavit budilnik",
            patterns=[r"\b(postav|ustanovi)\s+budilnik\s+na\s+(?P<time>\d{1,2}:\d{2})\b"],
            triggers=["postav budilnik", "budilnik na"],
            examples=["postav budilnik na 07:30"],
            parameters_schema={"time": "string"},
            handler=_handle_alarm_set,
        )
    )

    registry.register(
        _cmd(
            name="reminder_set",
            description="Sozdat napominanie",
            patterns=[
                r"\bnapomni( mne)?\s+(?P<what>.+)\s+v\s+(?P<time>\d{1,2}:\d{2})\b",
                r"\bnapomni( mne)?\s+(?P<what>.+)\s+cherez\s+(?P<duration>.+)\b",
            ],
            triggers=["napomni", "napominanie"],
            examples=["napomni mne kupit hleb v 18:30"],
            parameters_schema={"what": "string", "time": "optional", "duration": "optional"},
            handler=_handle_reminder_set,
        )
    )

    registry.register(
        _cmd(
            name="volume_set",
            description="Upravlenie gromkostyu",
            patterns=[
                r"\b(sdelai gromche|pribav gromkost|gromche)\b",
                r"\b(sdelai tishe|ubav gromkost|tishe)\b",
                r"\b(vykluchi zvuk|mut|bez zvuka)\b",
                r"\bgromkost\s+na\s+(?P<level>\d{1,3})\b",
                r"\bgromkost\s+(?P<level>\d{1,3})\b",
            ],
            triggers=["gromche", "tishe", "gromkost", "vykluchi zvuk"],
            examples=["sdelai gromche", "gromkost na 30"],
            parameters_schema={"level": "optional"},
            handler=_handle_volume_set,
        )
    )

    registry.register(
        _cmd(
            name="chat",
            description="Dialog s II",
            patterns=[
                r"\b(pogovori so mnoi|davai pogovorim)\b(?P<topic>.*)",
                r"\bobyyasni\s+(?P<topic>.+)\b",
                r"\bperevedi\s+(?P<topic>.+)\b",
                r"\bpridumai\s+(?P<topic>.+)\b",
            ],
            triggers=["pogovori so mnoi", "obyyasni", "perevedi", "pridumai"],
            examples=["pogovori so mnoi", "obyyasni chto takoe neyroseti"],
            parameters_schema={"topic": "optional"},
            handler=_handle_chat,
        )
    )

    registry.register(
        _cmd(
            name="settings_tts",
            description="Vklyuchit/vykluchit golos",
            patterns=[r"\b(vklyuchi|vykluchi)\s+golos\b", r"\b(vklyuchi|vykluchi)\s+zvuk\b"],
            triggers=["vklyuchi golos", "vykluchi golos", "vklyuchi zvuk", "vykluchi zvuk"],
            examples=["vykluchi golos", "vklyuchi golos"],
            parameters_schema={},
            handler=_handle_toggle_tts,
        )
    )

    registry.register(
        _cmd(
            name="settings_wake",
            description="Vklyuchit/vykluchit wake word",
            patterns=[r"\b(vklyuchi|vykluchi)\s+proslushku\b", r"\b(vklyuchi|vykluchi)\s+wake\s*word\b"],
            triggers=["vklyuchi proslushku", "vykluchi proslushku", "vklyuchi wake word", "vykluchi wake word"],
            examples=["vykluchi proslushku", "vklyuchi wake word"],
            handler=_handle_toggle_wake,
        )
    )

    registry.register(
        _cmd(
            name="exit",
            description="Vykhod",
            patterns=[r"\b(vykhod|stop|poka|zavershi|zakroy)\b"],
            triggers=["vykhod", "stop", "poka", "zakroy"],
            examples=["vykhod", "poka"],
            handler=_handle_exit,
        )
    )

    return registry


def _handle_help(ctx: CommandContext) -> str:
    registry = ctx.app_context.registry
    lines = ["Ya Antoshka. Vot chto ya umeyu:"]
    for cmd in registry.all():
        lines.append(f"- {cmd.description}")
    return "\n".join(lines)


def _handle_greet(_: CommandContext) -> str:
    return "Privet! Ya Antoshka. Skazhi 'pomoshch', chtoby uvidet komandy."


def _handle_time(_: CommandContext) -> str:
    now = datetime.now()
    return f"Seichas {now:%H:%M}."


def _handle_date(_: CommandContext) -> str:
    now = datetime.now()
    weekday = now.strftime("%A")
    return f"Segodnya {now:%d.%m.%Y} ({weekday})."


def _handle_tts_test(_: CommandContext) -> ActionResult:
    return ActionResult(
        text="Proverka zvuka.",
        action="tts_test",
        title="Test zvuka",
        details="Proiznesu testovuyu frazu.",
    )


def _handle_open_url(ctx: CommandContext) -> ActionResult | str:
    url = ctx.slots.get("url")
    if not url:
        site = ctx.slots.get("site")
        if site:
            custom_sites = (load_settings().get("custom_sites") or {})
            url = resolve_site(site, custom_sites)
    if not url:
        return "Ne ponyal, kakoy sait otkryt."
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=("Otkry??? sait." if ok else "Ne smog otkryt sait."),
        action="open_url",
        title="Otkry??? sait",
        details=url,
        status=status,
        url=url,
    )


def _handle_search_web(ctx: CommandContext) -> ActionResult | str:
    query = (ctx.slots.get("query") or "").strip()
    if not query:
        return "Ne ponyal, chto iskat."
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    ok = open_url(url)
    status = "ok" if ok else "error"
    return ActionResult(
        text=("Otkry??? rezultaty poiska." if ok else "Ne smog otkryt poisk."),
        action="search_web",
        title="Poisk v internete",
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
        text=("Otkry??? kartu." if ok else "Ne smog otkryt kartu."),
        action="open_map",
        title="Karta",
        details=query or "Yandex Maps",
        status=status,
        url=url,
    )


def _handle_open_path(ctx: CommandContext) -> ActionResult | str:
    path = ctx.slots.get("path")
    if not path:
        return "Ne ponyal, kakoy put otkryt."
    known = resolve_known_path(path)
    if known:
        path = known
    ok = open_path(path)
    status = "ok" if ok else "error"
    return ActionResult(
        text=("Otkry???." if ok else "Ne smog otkryt put."),
        action="open_path",
        title="Otkry??? put",
        details=path,
        status=status,
    )


def _handle_open_app(ctx: CommandContext) -> ActionResult | str:
    app = (ctx.slots.get("app") or "").strip()
    if not app:
        return "Ne ponyal, kakoe prilozhenie otkryt."
    if sys.platform != "win32":
        return "Otkrytie prilozheniy dostupno tolko na Windows."
    custom_apps = (load_settings().get("custom_apps") or {})
    resolved = resolve_app(app, custom_apps) or app
    ok = run_app(resolved)
    status = "ok" if ok else "error"
    return ActionResult(
        text=("Otkry??? prilozhenie." if ok else "Ne smog otkryt prilozhenie."),
        action="open_app",
        title="Zapusk prilozheniya",
        details=resolved,
        status=status,
    )


def _handle_note_create(ctx: CommandContext) -> ActionResult | str:
    note = (ctx.slots.get("note") or "").strip()
    if not note:
        return "Ne ponyal, chto zapisat."
    add_note(ctx.app_context.data_dir, note)
    return ActionResult(
        text="Zametka sohranena.",
        action="note_create",
        title="Zametka",
        details=note,
        status="ok",
    )


def _handle_note_list(ctx: CommandContext) -> ActionResult:
    notes = list_notes(ctx.app_context.data_dir)
    if not notes:
        return ActionResult(
            text="Zametok poka net.",
            action="note_list",
            title="Zametki",
            details="Pusto",
            status="ok",
        )
    lines = [f"{idx+1}. {n.get('text','')}" for idx, n in enumerate(notes[-10:])]
    return ActionResult(
        text="Vot poslednie zametki:",
        action="note_list",
        title="Zametki",
        details="\n".join(lines),
        status="ok",
    )


def _handle_note_delete(ctx: CommandContext) -> ActionResult | str:
    raw = (ctx.slots.get("index") or "").strip()
    if not raw.isdigit():
        return "Ne ponyal nomer zametki."
    idx = int(raw)
    ok = delete_note(ctx.app_context.data_dir, idx)
    status = "ok" if ok else "error"
    return ActionResult(
        text=("Zametka udalena." if ok else "Ne smog udalit zametku."),
        action="note_delete",
        title="Udaleniye zametki",
        details=f"Nomer: {idx}",
        status=status,
    )


def _handle_timer_set(ctx: CommandContext) -> ActionResult | str:
    duration_text = (ctx.slots.get("duration") or "").strip()
    seconds = parse_duration_seconds(duration_text)
    if not seconds:
        return "Ne ponyal dlitelnost taimera."
    ctx.app_context.scheduler.schedule_in(seconds, "Timer srabotal.")
    end_time = datetime.now() + timedelta(seconds=seconds)
    return ActionResult(
        text="Timer ustanovlen.",
        action="timer_set",
        title="Timer",
        details=f"Srabotaet v {end_time:%H:%M}",
        status="ok",
    )


def _handle_alarm_set(ctx: CommandContext) -> ActionResult | str:
    time_text = (ctx.slots.get("time") or "").strip()
    when = parse_time_of_day(time_text)
    if not when:
        return "Ne ponyal vremya budilnika."
    seconds = max(0, int((when - datetime.now()).total_seconds()))
    ctx.app_context.scheduler.schedule_in(seconds, "Budilnik. Pora vstav???.")
    return ActionResult(
        text="Budilnik ustanovlen.",
        action="alarm_set",
        title="Budilnik",
        details=f"Srabotaet v {when:%H:%M}",
        status="ok",
    )


def _handle_reminder_set(ctx: CommandContext) -> ActionResult | str:
    what = (ctx.slots.get("what") or "").strip()
    if not what:
        return "Ne ponyal, o chem napomnit."

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
        return "Ne ponyal vremya napominaniya."

    add_reminder(ctx.app_context.data_dir, what, when)
    ctx.app_context.scheduler.schedule_in(delay_seconds, f"Napominanie: {what}")
    return ActionResult(
        text="Napominanie sozdano.",
        action="reminder_set",
        title="Napominanie",
        details=f"{what} (v {when:%H:%M})" if when else what,
        status="ok",
    )


def _handle_volume_set(ctx: CommandContext) -> ActionResult | str:
    text = normalize_text(ctx.text)
    controller = ctx.app_context.volume
    if controller is None:
        return "Ne mogu izmenit gromkost na etom ustroystve."

    level = ctx.slots.get("level")
    if level and level.isdigit():
        target = max(0, min(100, int(level))) / 100.0
        ok = controller.set_absolute(target)
        status = "ok" if ok else "error"
        return ActionResult(
            text=("Gromkost izmenena." if ok else "Ne smog izmenit gromkost."),
            action="volume_set",
            title="Gromkost",
            details=f"{int(target*100)}%",
            status=status,
        )

    if "gromche" in text or "pribav" in text:
        ok = controller.change_relative(0.1)
        status = "ok" if ok else "error"
        return ActionResult(
            text=("Sdelal gromche." if ok else "Ne smog izmenit gromkost."),
            action="volume_set",
            title="Gromkost",
            details="+10%",
            status=status,
        )
    if "tishe" in text or "ubav" in text:
        ok = controller.change_relative(-0.1)
        status = "ok" if ok else "error"
        return ActionResult(
            text=("Sdelal tishe." if ok else "Ne smog izmenit gromkost."),
            action="volume_set",
            title="Gromkost",
            details="-10%",
            status=status,
        )
    if "vykluchi zvuk" in text or "mut" in text or "bez zvuka" in text:
        ok = controller.set_mute(True)
        status = "ok" if ok else "error"
        return ActionResult(
            text=("Zvuk vykluchen." if ok else "Ne smog vykluchit zvuk."),
            action="volume_set",
            title="Gromkost",
            details="mute",
            status=status,
        )

    return "Ne ponyal komandu dlya gromkosti."


def _handle_chat(ctx: CommandContext) -> str:
    llm_client = ctx.app_context.llm_client
    if llm_client is None:
        return "II nedostupen. Prover klyuch i nastroyki."
    topic = (ctx.slots.get("topic") or "").strip()
    if not topic:
        return "Slushayu, sprashivai."
    return llm_client.ask(topic)


def _handle_toggle_tts(ctx: CommandContext) -> ActionResult:
    t = normalize_text(ctx.text)
    settings = load_settings()
    enable = "vklyuchi" in t
    settings.setdefault("tts", {})["enabled"] = bool(enable)
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=("Golos vklyuchen." if enable else "Golos vykluchen."),
        action="settings_tts",
        title="Golos",
        details="on" if enable else "off",
        status="ok",
    )


def _handle_toggle_wake(ctx: CommandContext) -> ActionResult:
    t = normalize_text(ctx.text)
    settings = load_settings()
    enable = "vklyuchi" in t
    settings.setdefault("ui", {})["wake_word"] = bool(enable)
    save_settings(settings)
    if ctx.app_context.on_settings_changed:
        ctx.app_context.on_settings_changed(settings)
    return ActionResult(
        text=("Proslushka vklyuchena." if enable else "Proslushka vykluchena."),
        action="settings_wake",
        title="Wake word",
        details="on" if enable else "off",
        status="ok",
    )


def _handle_exit(_: CommandContext) -> str:
    return "__EXIT__"


def _handle_screenshot(_: CommandContext) -> ActionResult:
    try:
        from PIL import ImageGrab  # type: ignore
    except Exception:
        return ActionResult(
            text="Skrinshot nedostupen (nuzhen pillow).",
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
            text="Screenshot saved.",
            action="screenshot",
            title="Screenshot",
            details=str(path),
            status="ok",
        )
    except Exception as e:  # noqa: BLE001
        return ActionResult(
            text="Screenshot failed.",
            action="screenshot",
            title="Screenshot",
            details=str(e),
            status="error",
        )
