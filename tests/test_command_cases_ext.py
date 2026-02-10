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


def test_command_cases_bulk() -> None:
    r = _make_router()
    cases = [
        ("privet", "greet"),
        ("zdravstvuy", "greet"),
        ("dobryy den", "greet"),
        ("pomoshch", "help"),
        ("spravka", "help"),
        ("komandy", "help"),
        ("pokazhi komandy", "help"),
        ("skolko vremeni", "time"),
        ("vremya", "time"),
        ("kakaya data", "date"),
        ("kakoe segodnya chislo", "date"),
        ("otkroy youtube", "open_url"),
        ("otkroy sait vk", "open_url"),
        ("otkroy https://example.com", "open_url"),
        ("naydi v internete kotikov", "search_web"),
        ("poisk v internete novosti", "search_web"),
        ("otkroy kartu", "open_map"),
        ("pokazhi marshrut do doma", "open_map"),
        (r"otkroy fail C:\Temp\note.txt", "open_path"),
        ("otkroy papku zagruzki", "open_path"),
        ("otkroy prilozhenie notepad", "open_app"),
        ("sdelai zametku kupit moloko", "note_create"),
        ("zametka: kupit hleb", "note_create"),
        ("pokazhi zametki", "note_list"),
        ("udali zametku 2", "note_delete"),
        ("izmeni zametku 2 na kupit hleb", "note_update"),
        ("zameni v zametke 2 moloko na hleb", "note_replace"),
        ("postav timer na 5 minut", "timer_set"),
        ("ustanovi timer na 10 minut", "timer_set"),
        ("postav budilnik na 07:30", "alarm_set"),
        ("napomni mne kupit hleb v 18:30", "reminder_set"),
        ("napomni kupit hleb cherez 10 minut", "reminder_set"),
        ("sdelai gromche", "volume_set"),
        ("sdelai tishe", "volume_set"),
        ("gromkost na 40", "volume_set"),
        ("mut", "volume_set"),
        ("proverka zvuka", "tts_test"),
        ("skazhi test", "tts_test"),
        ("ustanovi yazyk ru", "settings_language"),
        ("ustanovi yazyk en", "settings_language"),
        ("ustanovi temu dark", "settings_theme"),
        ("ustanovi temu neon", "settings_theme"),
        ("ustanovi accent #7dd3fc", "settings_accent"),
        ("ustanovi fon 70", "settings_bg_intensity"),
        ("ustanovi skorost 180", "settings_tts_rate"),
        ("ustanovi gromkost golosa 70", "settings_tts_volume"),
        ("vklyuchi proslushku", "settings_wake"),
        ("vykluchi proslushku", "settings_wake"),
        ("otkroy pochtu", "open_mail"),
        ("open mail", "open_mail"),
        ("open gmail", "open_mail"),
        ("otkroy kalendar", "open_calendar"),
        ("open calendar", "open_calendar"),
        ("pogoda v moskve", "weather"),
        ("pogoda", "weather"),
        ("sozdai sobytie vstrecha na 10.02.2026 15:30", "event_add"),
        ("dobav sobytie zvonok na 10.02.2026 14:00", "event_add"),
        ("pokazhi sobytiya", "event_list"),
        ("spisok sobytiy", "event_list"),
        ("ochisti chat", "clear_chat"),
        ("udali istoriyu chata", "clear_chat"),
        ("vyhod", "exit"),
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

    for entry in cases:
        if len(entry) == 3:
            text, expected, lang = entry
        else:
            text, expected = entry
            lang = None
        res = r.route(text, lang=lang) if lang else r.route(text)
        assert res is not None, f"No match for: {text}"
        assert res.name == expected, f"{text} => {res.name}, expected {expected}"
