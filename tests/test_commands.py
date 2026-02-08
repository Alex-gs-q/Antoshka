from commands.builtins import create_registry


def _match_intent(text: str) -> str | None:
    reg = create_registry()
    res = reg.match(text)
    return res.command.name if res else None


def test_command_variations():
    cases = [
        ("pomoshch", "help"),
        ("chto ty umeesh", "help"),
        ("pokazhi komandy", "help"),
        ("privet", "greet"),
        ("dobryy vecher", "greet"),
        ("kotoryy chas", "time"),
        ("skolko vremeni", "time"),
        ("kakaya data", "date"),
        ("kakoy den nedeli", "date"),
        ("skazhi test", "tts_test"),
        ("prover zvuk", "tts_test"),
        ("otkroy youtube", "open_url"),
        ("otkroy sait vk", "open_url"),
        ("otkroy https://vk.com", "open_url"),
        ("zaydi na yandex", "open_url"),
        ("naydi pogodu v moskve", "search_web"),
        ("poisk v internete novosti", "search_web"),
        ("otkroy kartu", "open_map"),
        ("pokazhi marshrut do doma", "open_map"),
        ("otkroy papku zagruzki", "open_path"),
        ("otkroy dokumenty", "open_path"),
        ("otkroy fail otchet.pdf", "open_path"),
        ("zapusti kalkulyator", "open_app"),
        ("otkroy bloknot", "open_app"),
        ("sozdai zametku kupit moloko", "note_create"),
        ("zametka pozvonit mame", "note_create"),
        ("pokazhi zametki", "note_list"),
        ("spisok zametok", "note_list"),
        ("udali zametku 2", "note_delete"),
        ("postav timer na 5 minut", "timer_set"),
        ("timer na 30 sekund", "timer_set"),
        ("postav budilnik na 07:30", "alarm_set"),
        ("napomni mne kupit hleb v 18:30", "reminder_set"),
        ("napomni cherez 20 minut sdelat pereryv", "reminder_set"),
        ("sdelai gromche", "volume_set"),
        ("sdelai tishe", "volume_set"),
        ("gromkost na 30", "volume_set"),
        ("vykluchi zvuk", "volume_set"),
        ("pogovori so mnoi", "chat"),
        ("obyyasni chto takoe neyroseti", "chat"),
        ("perevedi tekst", "chat"),
        ("pridumai istoriyu", "chat"),
        ("vklyuchi golos", "settings_tts"),
        ("vykluchi golos", "settings_tts"),
        ("vklyuchi proslushku", "settings_wake"),
        ("vykluchi wake word", "settings_wake"),
        ("vykhod", "exit"),
        ("poka", "exit"),
    ]

    extra = [
        ("otkroy telegram", "open_url"),
        ("otkroy discord", "open_url"),
        ("otkroy yandex muzyka", "open_url"),
        ("otkroy google", "open_url"),
        ("naydi luchshie recepty", "search_web"),
        ("pogugli kak vklyuchit zvuk", "search_web"),
        ("otkroy rabochiy stol", "open_path"),
        ("otkroy papku dokumenty", "open_path"),
        ("otkroy prilozhenie discord", "open_app"),
        ("otkroy prilozhenie telegram", "open_app"),
    ]

    for text, intent in cases + extra:
        assert _match_intent(text) == intent
