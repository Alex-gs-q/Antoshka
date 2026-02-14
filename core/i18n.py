from __future__ import annotations

from pathlib import Path
from typing import Dict, List


_UI: Dict[str, Dict[str, str]] = {
    "app_name": {"ru": "Антошка", "en": "Antoshka"},
    "start_title": {"ru": "Привет, я Антошка", "en": "Hi, I'm Antoshka"},
    "start_subtitle": {"ru": "Голосовой помощник", "en": "Voice assistant"},
    "start_button": {"ru": "Начать", "en": "Start"},
    "examples_title": {"ru": "Примеры", "en": "Examples"},
    "placeholder": {"ru": "Введите сообщение...", "en": "Type a message..."},
    "status_ready": {"ru": "готов", "en": "ready"},
    "status_speaking": {"ru": "говорю", "en": "speaking"},
    "status_thinking": {"ru": "думаю", "en": "thinking"},
    "status_listening": {"ru": "слушаю", "en": "listening"},
    "status_stopped": {"ru": "остановлено", "en": "stopped"},
    "status_text_mode": {"ru": "текстовый режим", "en": "text mode"},
    "status_prefix": {"ru": "Статус", "en": "Status"},
    "btn_listen": {"ru": "Слушать", "en": "Listen"},
    "btn_stop": {"ru": "Стоп", "en": "Stop"},
    "btn_history": {"ru": "История", "en": "History"},
    "btn_volume": {"ru": "Громкость", "en": "Volume"},
    "btn_ai": {"ru": "ИИ", "en": "AI"},
    "btn_settings": {"ru": "Настройки", "en": "Settings"},
    "btn_clear_chat": {"ru": "Очистить чат", "en": "Clear chat"},
    "msg_speech_empty": {
        "ru": "Речь не распознана. Попробуй говорить громче.",
        "en": "No speech detected. Try speaking louder.",
    },
    "msg_voice_timeout": {
        "ru": "Не получил ответ за {seconds} секунд. Попробуй ещё раз.",
        "en": "No response within {seconds} seconds. Try again.",
    },
    "msg_ai_unavailable": {
        "ru": "ИИ недоступен. Проверь ключ АПИ в настройках.",
        "en": "AI is unavailable. Check OPENAI_API_KEY.",
    },
    "msg_ai_enabled": {"ru": "ИИ включён.", "en": "AI enabled."},
    "msg_ai_disabled": {"ru": "ИИ выключен.", "en": "AI disabled."},
    "msg_ai_missing_key": {
        "ru": "Не найден ключ OpenAI. Добавь OPENAI_API_KEY.",
        "en": "OPENAI_API_KEY is missing.",
    },
    "msg_ai_inflight": {"ru": "ИИ отвечает…", "en": "AI is responding…"},
    "msg_ai_busy": {"ru": "ИИ занят. Подожди.", "en": "AI is busy. Please wait."},
    "msg_ai_queued": {"ru": "Запрос в очереди: {position}.", "en": "Queued request: {position}."},
    "msg_ai_quota": {"ru": "Лимит ИИ исчерпан.", "en": "AI quota exceeded."},
    "msg_ai_rate_limit": {"ru": "ИИ ограничил запросы. Попробуй позже.", "en": "AI rate limit reached. Try later."},
    "msg_ai_rate_limit_wait": {
        "ru": "Слишком много запросов. Подожди {seconds} сек.",
        "en": "Too many requests. Wait {seconds} seconds.",
    },
    "msg_ai_check_ok": {"ru": "ИИ доступен.", "en": "AI check OK."},
    "msg_ai_check_401": {"ru": "ИИ: 401 (неверный ключ).", "en": "AI: 401 unauthorized."},
    "msg_ai_check_403": {"ru": "ИИ: 403 (доступ запрещён).", "en": "AI: 403 forbidden."},
    "msg_ai_check_429": {"ru": "ИИ: 429 (лимит запросов).", "en": "AI: 429 rate limit."},
    "msg_ai_check_no_credits": {"ru": "ИИ: нет кредитов.", "en": "AI: no credits."},
    "msg_ai_check_network": {"ru": "ИИ: ошибка сети.", "en": "AI: network error."},
    "msg_ai_check_error": {"ru": "ИИ: ошибка проверки.", "en": "AI: check failed."},
    "msg_tts_disabled": {
        "ru": "Озвучка выключена в настройках.",
        "en": "TTS is disabled in settings.",
    },
    "msg_tts_unavailable": {
        "ru": "Озвучка недоступна. Проверь провайдер озвучки.",
        "en": "TTS is unavailable. Install a provider (pyttsx3 or edge-tts).",
    },
    "msg_wake_unavailable": {
        "ru": "Ключевая фраза недоступна: проверь микрофон и модель распознавания.",
        "en": "Wake word unavailable: check microphone and Vosk model.",
    },
    "msg_chat_cleared": {"ru": "Чат очищен", "en": "Chat cleared"},
    "msg_volume_unavailable": {
        "ru": "Управление громкостью недоступно на этом устройстве.",
        "en": "Volume control is not available on this device.",
    },
    "confirm_clear_title": {"ru": "Очистить историю", "en": "Clear history"},
    "confirm_clear_text": {"ru": "Точно очистить историю?", "en": "Clear saved history?"},
    "confirm_yes": {"ru": "Да", "en": "Yes"},
    "confirm_no": {"ru": "Нет", "en": "No"},
    "safety_confirmed": {"ru": "Подтверждение получено.", "en": "Confirmation received."},
    "settings_title": {"ru": "Настройки", "en": "Settings"},
    "title_history": {"ru": "История", "en": "History"},
    "title_volume": {"ru": "Громкость", "en": "Volume"},
    "settings_saved": {"ru": "Сохранено", "en": "Saved"},
    "section_language": {"ru": "Язык и распознавание", "en": "Language & STT"},
    "section_mic": {"ru": "Микрофон", "en": "Microphone"},
    "section_theme": {"ru": "Тема", "en": "Theme"},
    "section_tts": {"ru": "Голос", "en": "Voice (TTS)"},
    "section_ai": {"ru": "ИИ", "en": "AI"},
    "section_wake": {"ru": "Ключевая фраза", "en": "Wake word"},
    "label_language": {"ru": "Язык", "en": "Language"},
    "opt_auto": {"ru": "Авто", "en": "Auto"},
    "opt_ru": {"ru": "Русский", "en": "RU"},
    "opt_en": {"ru": "Английский", "en": "EN"},
    "label_stt_mode": {"ru": "Режим распознавания", "en": "STT mode"},
    "opt_text": {"ru": "Текст", "en": "Text"},
    "opt_vosk": {"ru": "Воск", "en": "Vosk"},
    "label_default_device": {"ru": "По умолчанию", "en": "Default"},
    "label_mic_device": {"ru": "Устройство ввода", "en": "Input device"},
    "label_mic_level": {"ru": "Уровень входа", "en": "Input level"},
    "label_theme_preset": {"ru": "Пресет", "en": "Preset"},
    "label_accent": {"ru": "Цвет акцента", "en": "Accent color"},
    "label_bg_intensity": {"ru": "Интенсивность фона", "en": "Background intensity"},
    "label_voice_timeout": {"ru": "Ожидание ответа (голос)", "en": "Voice response timeout"},
    "label_vosk_model_path": {"ru": "Путь к Vosk модели", "en": "Vosk model path"},
    "label_stt_section": {"ru": "Распознавание речи (Vosk)", "en": "Speech recognition (Vosk)"},
    "label_status": {"ru": "Статус", "en": "Status"},
    "label_actions": {"ru": "Действия", "en": "Actions"},
    "unit_seconds": {"ru": "сек", "en": "s"},
    "label_tts_provider": {"ru": "Провайдер озвучки", "en": "TTS provider"},
    "label_tts_enabled": {"ru": "Включить голос", "en": "Enable voice"},
    "label_tts_rate": {"ru": "Скорость", "en": "Rate"},
    "label_tts_volume": {"ru": "Громкость", "en": "Volume"},
    "label_tts_pitch": {"ru": "Тон", "en": "Pitch"},
    "label_voice_ru": {"ru": "Голос РУ", "en": "Voice RU"},
    "label_voice_en": {"ru": "Голос ЕН", "en": "Voice EN"},
    "label_wake_word": {"ru": "Ключевая фраза: Антошка", "en": "Wake word: Antoshka"},
    "btn_test_mic": {"ru": "Тест микрофона", "en": "Test microphone"},
    "btn_test_tts": {"ru": "Тест звука", "en": "Test sound"},
    "btn_ai_check": {"ru": "Проверить ИИ", "en": "Check AI"},
    "btn_open_settings": {"ru": "Открыть настройки", "en": "Open settings"},
    "btn_choose_vosk_model": {"ru": "Выбрать папку", "en": "Choose folder"},
    "btn_check_vosk_model": {"ru": "Проверить модель", "en": "Check model"},
    "btn_choose_vosk_path": {"ru": "Указать папку модели...", "en": "Choose model folder..."},
    "btn_vosk_install_help": {"ru": "Скачать модель (инструкция)", "en": "Download model (help)"},
    "btn_open_vosk_page": {"ru": "Открыть страницу модели", "en": "Open model page"},
    "btn_add_sound": {"ru": "Добавить звук", "en": "Add sound"},
    "btn_delete_sound": {"ru": "Удалить звук", "en": "Delete sound"},
    "btn_save": {"ru": "Сохранить", "en": "Save"},
    "label_show_start": {"ru": "Показывать стартовый экран", "en": "Show start screen"},
    "helper_language": {"ru": "Авто определяет язык по вводу или речи.", "en": "Auto detects language from input or speech."},
    "helper_mic": {"ru": "Выбери устройство и проверь уровень сигнала.", "en": "Choose device and check input level."},
    "helper_theme": {"ru": "Изменения применяются сразу.", "en": "Changes apply instantly."},
    "helper_tts": {"ru": "Выбор голоса влияет на озвучку.", "en": "Voice selection affects speech output."},
    "helper_wake": {"ru": "Ключевая фраза включает голосовое пробуждение.", "en": "Wake word enables voice activation."},
    "role_user": {"ru": "пользователь", "en": "user"},
    "role_assistant": {"ru": "ассистент", "en": "assistant"},
    "msg_mic_ok": {"ru": "Микрофон в порядке", "en": "Mic ok"},
    "msg_mic_error": {"ru": "Ошибка микрофона", "en": "Mic error"},
    "msg_mic_unavailable": {"ru": "Микрофон не найден или нет доступа.", "en": "Microphone not found or no access."},
    "msg_mic_signal_low": {"ru": "Сигнал слишком слабый", "en": "Signal too low"},
    "msg_mic_testing": {"ru": "Тест микрофона...", "en": "Testing microphone..."},
    "msg_greet": {
        "ru": "Привет! Я Антошка. Скажи «помощь», чтобы увидеть команды.",
        "en": "Hi! I'm Antoshka. Say \"help\" to see commands.",
    },
    "msg_time": {"ru": "Сейчас {time}.", "en": "It's {time}."},
    "msg_date": {"ru": "Сегодня {date} ({weekday}).", "en": "Today is {date} ({weekday})."},
    "msg_tts_test": {"ru": "Проверка звука.", "en": "Sound test."},
    "msg_tts_test_phrase": {"ru": "Антошка, проверка звука.", "en": "Antoshka, sound check."},
    "msg_startup": {"ru": "Антошка запущен", "en": "Antoshka started"},
    "msg_listening": {"ru": "Слушаю", "en": "Listening"},
    "msg_console_hello": {
        "ru": "текстовый режим. Напиши команду (или «помощь»). Для выхода: «выход».",
        "en": "text mode. Type a command (or \"help\"). To exit: \"exit\".",
    },
    "msg_bye": {"ru": "Пока!", "en": "Bye!"},
    "msg_open_site_ok": {"ru": "Открыл сайт.", "en": "Opened the website."},
    "msg_open_site_fail": {"ru": "Не смог открыть сайт.", "en": "Couldn't open the website."},
    "msg_search_ok": {"ru": "Открыл результаты поиска.", "en": "Opened search results."},
    "msg_search_fail": {"ru": "Не смог открыть поиск.", "en": "Couldn't open search."},
    "msg_mail_ok": {"ru": "Открыл почту.", "en": "Opened mail."},
    "msg_mail_fail": {"ru": "Не смог открыть почту.", "en": "Couldn't open mail."},
    "msg_calendar_ok": {"ru": "Открыл календарь.", "en": "Opened calendar."},
    "msg_calendar_fail": {"ru": "Не смог открыть календарь.", "en": "Couldn't open calendar."},
    "msg_map_ok": {"ru": "Открыл карту.", "en": "Opened the map."},
    "msg_map_fail": {"ru": "Не смог открыть карту.", "en": "Couldn't open the map."},
    "msg_open_path_ok": {"ru": "Открыл.", "en": "Opened."},
    "msg_open_path_fail": {"ru": "Не смог открыть путь.", "en": "Couldn't open the path."},
    "msg_open_app_ok": {"ru": "Открыл приложение.", "en": "Opened the app."},
    "msg_open_app_fail": {"ru": "Не смог открыть приложение.", "en": "Couldn't open the app."},
    "msg_note_saved": {"ru": "Заметка сохранена.", "en": "Note saved."},
    "msg_notes_empty": {"ru": "Заметок пока нет.", "en": "No notes yet."},
    "msg_notes_list": {"ru": "Вот последние заметки:", "en": "Here are the latest notes:"},
    "msg_note_deleted": {"ru": "Заметка удалена.", "en": "Note deleted."},
    "msg_note_delete_fail": {"ru": "Не смог удалить заметку.", "en": "Couldn't delete the note."},
    "msg_note_updated": {"ru": "Заметка обновлена.", "en": "Note updated."},
    "msg_note_not_found": {"ru": "Не нашел заметку.", "en": "Note not found."},
    "msg_note_replace_fail": {"ru": "Не смог заменить текст в заметке.", "en": "Couldn't replace text in note."},
    "msg_note_update_fail": {"ru": "Не понял, какую заметку изменить.", "en": "I didn't understand which note to update."},
    "msg_note_replaced": {"ru": "Текст в заметке заменен.", "en": "Text in note replaced."},
    "msg_timer_set": {"ru": "Таймер установлен.", "en": "Timer set."},
    "msg_timer_fired": {"ru": "Таймер сработал.", "en": "Timer finished."},
    "msg_timer_cancelled": {"ru": "Таймеры отменены.", "en": "Timers cancelled."},
    "msg_timer_not_found": {"ru": "Активных таймеров нет.", "en": "No active timers."},
    "msg_timer_done": {"ru": "Таймер завершён: {duration}", "en": "Timer finished: {duration}"},
    "msg_snoozed": {"ru": "Отложено на {minutes} мин.", "en": "Snoozed for {minutes} min."},
    "msg_timer_restarted": {"ru": "Таймер перезапущен.", "en": "Timer restarted."},
    "msg_alert_stopped": {"ru": "Отключено.", "en": "Stopped."},
    "msg_alert_hidden": {"ru": "Событие сработало.", "en": "Event fired."},
    "msg_alarm_set": {"ru": "Будильник установлен.", "en": "Alarm set."},
    "msg_alarm_fired": {"ru": "Будильник. Пора вставать.", "en": "Alarm. Time to wake up."},
    "msg_alarm_cancelled": {"ru": "Будильники отменены.", "en": "Alarms cancelled."},
    "msg_alarm_not_found": {"ru": "Активных будильников нет.", "en": "No active alarms."},
    "msg_reminder_set": {"ru": "Напоминание создано.", "en": "Reminder created."},
    "msg_reminder_prefix": {"ru": "Напоминание: {text}", "en": "Reminder: {text}"},
    "msg_volume_changed": {"ru": "Громкость изменена.", "en": "Volume changed."},
    "msg_volume_fail": {"ru": "Не смог изменить громкость.", "en": "Couldn't change volume."},
    "msg_louder": {"ru": "Сделал громче.", "en": "Made it louder."},
    "msg_quieter": {"ru": "Сделал тише.", "en": "Made it quieter."},
    "msg_mute": {"ru": "Звук выключен.", "en": "Sound muted."},
    "msg_ai_unavailable_cmd": {
        "ru": "ИИ недоступен. Проверь ключ АПИ и настройки.",
        "en": "AI is unavailable. Check key and settings.",
    },
    "msg_chat_prompt": {"ru": "Слушаю, спрашивай.", "en": "I'm listening. Ask me anything."},
    "msg_tts_on": {"ru": "Голос включен.", "en": "Voice enabled."},
    "msg_tts_off": {"ru": "Голос выключен.", "en": "Voice disabled."},
    "msg_wake_on": {"ru": "Прослушка включена.", "en": "Wake word enabled."},
    "msg_wake_off": {"ru": "Прослушка выключена.", "en": "Wake word disabled."},
    "msg_screenshot_unavailable": {
        "ru": "Скриншот недоступен (нужен пакет для скриншотов).",
        "en": "Screenshot unavailable (pillow required).",
    },
    "msg_screenshot_saved": {"ru": "Скриншот сохранен.", "en": "Screenshot saved."},
    "msg_screenshot_failed": {"ru": "Скриншот не удалось сделать.", "en": "Screenshot failed."},
    "msg_unknown_command": {"ru": "Не понял команду. Скажи «помощь».", "en": "I didn't understand. Say \"help\"."},
    "msg_help_short": {"ru": "Вот основные команды и примеры.", "en": "Here are the main commands and examples."},
    "msg_help_opened": {
        "ru": "Открыл помощь. Выбери команду или начни вводить.",
        "en": "Help is open. Pick a command or start typing.",
    },
    "help_search": {"ru": "Поиск команд…", "en": "Search commands…"},
    "help_execute": {"ru": "Выполнить", "en": "Run"},
    "help_insert": {"ru": "Вставить", "en": "Insert"},
    "help_category_all": {"ru": "Все", "en": "All"},
    "help_category_time": {"ru": "Время", "en": "Time"},
    "help_category_timer": {"ru": "Таймер", "en": "Timer"},
    "help_category_alarm": {"ru": "Будильник", "en": "Alarm"},
    "help_category_reminder": {"ru": "Напоминания", "en": "Reminders"},
    "help_category_notes": {"ru": "Заметки", "en": "Notes"},
    "help_category_sites": {"ru": "Сайты", "en": "Sites"},
    "help_category_system": {"ru": "Система", "en": "System"},
    "help_category_ai": {"ru": "ИИ", "en": "AI"},
    "suggestion_refresh": {"ru": "Обновить подсказки", "en": "Refresh suggestions"},
    "msg_error_generic": {"ru": "Произошла ошибка. Проверь логи.", "en": "An error occurred. Check logs."},
    "msg_site_unknown": {"ru": "Не понял, какой сайт открыть.", "en": "I didn't understand which site to open."},
    "msg_search_empty": {"ru": "Не понял, что искать.", "en": "I didn't understand what to search."},
    "msg_path_unknown": {"ru": "Не понял, какой путь открыть.", "en": "I didn't understand which path to open."},
    "msg_app_unknown": {"ru": "Не понял, какое приложение открыть.", "en": "I didn't understand which app to open."},
    "msg_windows_only": {"ru": "Открытие приложений доступно только на Виндовс.", "en": "App launching is available only on Windows."},
    "msg_note_empty": {"ru": "Не понял, что записать.", "en": "I didn't understand what to save."},
    "msg_note_index": {"ru": "Не понял номер заметки.", "en": "I didn't understand the note number."},
    "msg_timer_duration": {"ru": "Не понял длительность таймера.", "en": "I didn't understand the timer duration."},
    "msg_alarm_time": {"ru": "Не понял время будильника.", "en": "I didn't understand the alarm time."},
    "msg_reminder_text": {"ru": "Не понял, о чем напомнить.", "en": "I didn't understand what to remind."},
    "msg_reminder_time": {"ru": "Не понял время напоминания.", "en": "I didn't understand the reminder time."},
    "msg_event_title": {"ru": "Не понял название события.", "en": "I didn't understand the event title."},
    "msg_event_added": {"ru": "Событие добавлено.", "en": "Event added."},
    "msg_events_empty": {"ru": "Событий пока нет.", "en": "No events yet."},
    "msg_events_list": {"ru": "Вот ближайшие события:", "en": "Here are upcoming events:"},
    "msg_lang_unknown": {"ru": "Не понял язык. Скажи: русский, английский или авто.", "en": "Unknown language. Say ru, en, or auto."},
    "msg_theme_unknown": {"ru": "Не понял тему. Варианты: Dark, Midnight, Neon.", "en": "Unknown theme. Options: Dark, Midnight, Neon."},
    "msg_accent_invalid": {"ru": "Неверный цвет. Пример: #7dd3fc", "en": "Invalid color. Example: #7dd3fc"},
    "msg_value_invalid": {"ru": "Не понял значение.", "en": "Invalid value."},
    "msg_settings_updated": {"ru": "Настройки обновлены.", "en": "Settings updated."},
    "msg_weather_ok": {"ru": "Открыл прогноз погоды.", "en": "Opened weather forecast."},
    "msg_weather_fail": {"ru": "Не смог открыть погоду.", "en": "Couldn't open weather."},
    "msg_weather_query": {"ru": "Погода", "en": "Weather"},
    "msg_weather_query_default": {"ru": "Погода", "en": "Weather"},
    "msg_volume_cmd": {"ru": "Не понял команду для громкости.", "en": "I didn't understand the volume command."},
    "safety_denied": {"ru": "Запрещено политикой безопасности.", "en": "Blocked by safety policy."},
    "safety_unknown_action": {"ru": "Неизвестное действие.", "en": "Unknown action."},
    "safety_need_confirm": {"ru": "Нужно подтверждение: скажи «подтверждаю».", "en": "Confirmation required: say \"confirm\"."},
    "action_open_site_title": {"ru": "Открыть сайт", "en": "Open website"},
    "action_search_title": {"ru": "Поиск в интернете", "en": "Web search"},
    "action_mail_title": {"ru": "Почта", "en": "Mail"},
    "action_calendar_title": {"ru": "Календарь", "en": "Calendar"},
    "action_map_title": {"ru": "Карта", "en": "Map"},
    "action_open_path_title": {"ru": "Открыть путь", "en": "Open path"},
    "action_open_app_title": {"ru": "Запуск приложения", "en": "Launch app"},
    "action_note_title": {"ru": "Заметка", "en": "Note"},
    "action_notes_title": {"ru": "Заметки", "en": "Notes"},
    "action_note_delete_title": {"ru": "Удаление заметки", "en": "Delete note"},
    "action_note_update_title": {"ru": "Изменение заметки", "en": "Update note"},
    "action_note_replace_title": {"ru": "Замена в заметке", "en": "Replace in note"},
    "action_timer_title": {"ru": "Таймер", "en": "Timer"},
    "action_alarm_title": {"ru": "Будильник", "en": "Alarm"},
    "action_reminder_title": {"ru": "Напоминание", "en": "Reminder"},
    "action_help_title": {"ru": "Помощь", "en": "Help"},
    "btn_alert_repeat": {"ru": "Повторить", "en": "Repeat"},
    "btn_alert_stop": {"ru": "Выключить", "en": "Stop"},
    "btn_alert_snooze": {"ru": "Отложить", "en": "Snooze"},
    "label_fired_timer": {"ru": "Сработало: Таймер", "en": "Fired: Timer"},
    "label_fired_alarm": {"ru": "Сработало: Будильник", "en": "Fired: Alarm"},
    "label_fired_reminder": {"ru": "Сработало: Напоминание", "en": "Fired: Reminder"},
    "section_alerts": {"ru": "Сигналы", "en": "Alerts"},
    "label_alerts_enabled": {"ru": "Звук таймера/напоминаний", "en": "Timer/Reminder sound"},
    "label_alerts_sound": {"ru": "Мелодия", "en": "Sound"},
    "label_alerts_custom": {"ru": "Пользовательские звуки", "en": "Custom sounds"},
    "label_alerts_volume": {"ru": "Громкость сигнала", "en": "Alert volume"},
    "label_alerts_loop": {"ru": "Loop сигнала", "en": "Loop alert"},
    "btn_test_alert": {"ru": "Тест сигнала", "en": "Test alert"},
    "label_snooze_default": {"ru": "Snooze по умолчанию (мин)", "en": "Default snooze (min)"},
    "label_snooze_quick": {"ru": "Показывать быстрые snooze", "en": "Show quick snooze"},
    "label_snooze_quick_set": {"ru": "Набор быстрых кнопок", "en": "Quick buttons"},
    "label_snooze_dropdown": {"ru": "Показывать dropdown", "en": "Show dropdown"},
    "label_snooze_dropdown_set": {"ru": "Варианты dropdown", "en": "Dropdown options"},
    "label_timer_restart": {"ru": "Повторить заново", "en": "Restart timer"},
    "label_duration": {"ru": "Длительность", "en": "Duration"},
    "label_system_notifications": {"ru": "Системные уведомления", "en": "System notifications"},
    "label_notify_text": {"ru": "Показывать текст", "en": "Show text"},
    "label_notify_icon": {"ru": "Иконка в уведомлении", "en": "Icon in notification"},
    "label_notify_tray_dup": {"ru": "Дублировать в трее", "en": "Duplicate in tray"},
    "btn_test_notify": {"ru": "Тест уведомления", "en": "Test notification"},
    "label_alert_popup": {"ru": "Показывать карточку", "en": "Show alert card"},
    "label_alert_popup_timeout": {"ru": "Автозакрытие (сек)", "en": "Auto close (sec)"},
    "msg_stt_fallback": {
        "ru": "Модель речи {from_lang} недоступна, использую {to_lang}.",
        "en": "{from_lang} voice model not available, using {to_lang}.",
    },
    "msg_stt_model_missing": {
        "ru": "Модель распознавания речи не найдена. Установите модели Vosk.",
        "en": "Speech model not found. Install Vosk models.",
    },
    "msg_stt_model_found": {
        "ru": "Модель найдена ✅ {path}",
        "en": "Model found ✅ {path}",
    },
    "tooltip_listen_disabled_vosk": {
        "ru": "Нужна модель Vosk. Откройте Настройки -> Распознавание речи -> Указать папку модели.",
        "en": "Vosk model is required. Open Settings -> Speech recognition -> Choose model folder.",
    },
    "dialog_vosk_help_title": {
        "ru": "Как установить модель Vosk",
        "en": "How to install a Vosk model",
    },
    "dialog_vosk_help_body": {
        "ru": "1) Скачайте модель на сайте Vosk.\n2) Распакуйте в отдельную папку.\n3) Внутри должны быть conf/ и graph/ (или am/).\n4) Укажите эту папку в настройках.\nПримеры: .\\models\\vosk-model-small-ru-0.22 или C:\\Models\\vosk-model-small-ru-0.22",
        "en": "1) Download a model from the Vosk website.\n2) Extract it to a separate folder.\n3) The folder must contain conf/ and graph/ (or am/).\n4) Choose that folder in settings.\nExamples: .\\models\\vosk-model-small-en-us-0.15 or C:\\Models\\vosk-model-small-en-us-0.15",
    },
    "helper_vosk_unpack": {
        "ru": "Распакуйте модель так, чтобы внутри папки были conf/, graph/ или am/.",
        "en": "Extract the model so the folder contains conf/, graph/, or am/.",
    },
    "msg_not_set": {"ru": "не задан", "en": "not set"},
    "msg_vosk_model_ok": {
        "ru": "Модель Vosk найдена: {path}",
        "en": "Vosk model found: {path}",
    },
    "msg_vosk_model_bad": {
        "ru": "Не найден валидный путь к Vosk модели (нужны папки am и conf).",
        "en": "Valid Vosk model path not found (am and conf folders are required).",
    },
    "action_event_title": {"ru": "Событие", "en": "Event"},
    "action_volume_title": {"ru": "Громкость", "en": "Volume"},
    "action_tts_test_title": {"ru": "Тест звука", "en": "Sound test"},
    "action_voice_title": {"ru": "Голос", "en": "Voice"},
    "action_weather_title": {"ru": "Погода", "en": "Weather"},
    "action_settings_title": {"ru": "Настройки", "en": "Settings"},
    "status_ok": {"ru": "ОК", "en": "OK"},
    "status_error": {"ru": "ОШИБКА", "en": "ERROR"},
    "action_wake_title": {"ru": "Ключевая фраза", "en": "Wake word"},
    "state_on": {"ru": "вкл", "en": "on"},
    "state_off": {"ru": "выкл", "en": "off"},
    "map_default_name": {"ru": "Яндекс Карты", "en": "Yandex Maps"},
    "msg_alerts_disabled": {"ru": "Все оповещения отключены.", "en": "All alerts disabled."},
    "msg_alert_sound_missing": {
        "ru": "Не нашёл звук оповещения. Проверь настройки.",
        "en": "Alert sound not found. Check settings.",
    },
    "msg_alert_handled": {"ru": "Оповещение обработано.", "en": "Alert handled."},
    "msg_notify_failed": {"ru": "Не удалось показать уведомление.", "en": "Failed to show notification."},
    "msg_event_not_found": {"ru": "Событие не найдено.", "en": "Event not found."},
    "msg_timer_stopped": {"ru": "✅ Таймер остановлен.", "en": "✅ Timer stopped."},
    "msg_alarm_stopped": {"ru": "✅ Будильник выключен.", "en": "✅ Alarm turned off."},
    "msg_reminder_cancelled": {"ru": "✅ Напоминание отменено.", "en": "✅ Reminder cancelled."},
    "msg_timer_snoozed": {
        "ru": "⏰ Таймер отложен на {minutes} мин. Следующее срабатывание в {time}.",
        "en": "⏰ Timer snoozed for {minutes} min. Next at {time}.",
    },
    "msg_alarm_snoozed": {
        "ru": "⏰ Будильник отложен на {minutes} мин. Следующее срабатывание в {time}.",
        "en": "⏰ Alarm snoozed for {minutes} min. Next at {time}.",
    },
    "msg_reminder_snoozed": {
        "ru": "⏰ Напоминание отложено на {minutes} мин. Следующее срабатывание в {time}.",
        "en": "⏰ Reminder snoozed for {minutes} min. Next at {time}.",
    },
    "msg_timer_restarted_detail": {
        "ru": "🔁 Таймер запущен заново на {duration}.",
        "en": "🔁 Timer restarted for {duration}.",
    },
    "msg_action_unavailable_type": {
        "ru": "Действие недоступно для: {type}.",
        "en": "Action is not available for: {type}.",
    },
    "help_title": {"ru": "Помощь", "en": "Help"},
    "about_title": {"ru": "Антошка — голосовой помощник", "en": "Antoshka — voice assistant"},
    "about_subtitle": {
        "ru": "Кроссплатформенный помощник для команд и диалога",
        "en": "Cross-platform assistant for commands and dialogue",
    },
    "about_section_idea": {"ru": "Идея проекта", "en": "Project idea"},
    "about_section_features": {"ru": "Что умеет", "en": "Capabilities"},
    "about_section_examples": {"ru": "Горячие примеры команд", "en": "Quick command examples"},
    "about_section_tech": {"ru": "Техническая информация", "en": "Technical info"},
    "about_copy": {"ru": "Скопировать информацию", "en": "Copy info"},
    "about_close": {"ru": "Закрыть", "en": "Close"},
    "about_copied": {"ru": "Скопировано", "en": "Copied"},
    "section_info": {"ru": "Информация", "en": "Information"},
    "btn_about": {"ru": "О программе", "en": "About"},
    "section_chat": {"ru": "Чат", "en": "Chat"},
    "label_show_suggestions": {"ru": "Показывать подсказки в чате", "en": "Show suggestions"},
    "label_suggest_send_on_click": {"ru": "Клик отправляет сразу", "en": "Send on click"},
    "suggestion_tip_insert": {"ru": "Вставить в чат", "en": "Insert into input"},
    "suggestion_tip_send": {"ru": "Отправить", "en": "Send"},
}


_COMMANDS: Dict[str, Dict[str, Dict[str, List[str] | str]]] = {'help': {'name': {'ru': 'Помощь', 'en': 'Help'},
          'desc': {'ru': 'Список команд', 'en': 'Commands list'},
          'examples': {'ru': ['помощь', 'что ты умеешь', 'покажи команды'],
                       'en': ['help', 'what can you do', 'show commands']}},
 'greet': {'name': {'ru': 'Приветствие', 'en': 'Greeting'},
           'desc': {'ru': 'Поздороваться', 'en': 'Say hello'},
           'examples': {'ru': ['привет', 'добрый день'], 'en': ['hello', 'good morning']}},
 'time': {'name': {'ru': 'Текущее время', 'en': 'Current time'},
          'desc': {'ru': 'Сказать время', 'en': 'Tell the time'},
          'examples': {'ru': ['который час', 'сколько времени'], 'en': ['what time is it', 'current time']}},
 'date': {'name': {'ru': 'Текущая дата', 'en': 'Current date'},
          'desc': {'ru': 'Сказать дату', 'en': 'Tell the date'},
          'examples': {'ru': ['какая дата', 'какое сегодня число'], 'en': ['what date is it', "today's date"]}},
 'open_url': {'name': {'ru': 'Открыть сайт', 'en': 'Open website'},
              'desc': {'ru': 'Открыть сайт в браузере', 'en': 'Open a website in browser'},
              'examples': {'ru': ['открой ютуб', 'открой гугл'], 'en': ['open youtube', 'open google']}},
 'search_web': {'name': {'ru': 'Поиск в интернете', 'en': 'Web search'},
                'desc': {'ru': 'Найти в интернете', 'en': 'Search the web'},
                'examples': {'ru': ['найди в интернете лучшие фильмы 2025', 'поиск в интернете новости'],
                             'en': ['search the web for best movies 2025']}},
 'open_mail': {'name': {'ru': 'Почта', 'en': 'Mail'},
               'desc': {'ru': 'Открыть почту', 'en': 'Open mail'},
               'examples': {'ru': ['открой почту',
                                   'открой яндекс почту',
                                   'открой аутлук',
                                   'открой айклауд',
                                   'открой яху',
                                   'открой протон',
                                   'открой мэйл ру'],
                            'en': ['open mail',
                                   'open gmail',
                                   'open outlook',
                                   'open icloud',
                                   'open yahoo mail',
                                   'open proton mail']}},
 'open_calendar': {'name': {'ru': 'Календарь', 'en': 'Calendar'},
                   'desc': {'ru': 'Открыть календарь', 'en': 'Open calendar'},
                   'examples': {'ru': ['открой календарь'], 'en': ['open calendar']}},
 'open_map': {'name': {'ru': 'Карта', 'en': 'Map'},
              'desc': {'ru': 'Открыть карту', 'en': 'Open map'},
              'examples': {'ru': ['открой карту', 'карта москвы'], 'en': ['open map', 'open map of london']}},
 'screenshot': {'name': {'ru': 'Скриншот', 'en': 'Screenshot'},
                'desc': {'ru': 'Сделать снимок экрана', 'en': 'Take a screenshot'},
                'examples': {'ru': ['сделай скриншот'], 'en': ['take a screenshot']}},
 'weather': {'name': {'ru': 'Погода', 'en': 'Weather'},
             'desc': {'ru': 'Открыть прогноз погоды', 'en': 'Open weather forecast'},
             'examples': {'ru': ['погода в москве', 'какая погода'], 'en': ['weather in london']}},
 'open_path': {'name': {'ru': 'Открыть файл или папку', 'en': 'Open file or folder'},
               'desc': {'ru': 'Открыть путь', 'en': 'Open a path'},
               'examples': {'ru': ['открой папку документы'], 'en': ['open folder documents']}},
 'open_app': {'name': {'ru': 'Открыть приложение', 'en': 'Open app'},
              'desc': {'ru': 'Запустить приложение', 'en': 'Launch an app'},
              'examples': {'ru': ['открой калькулятор'], 'en': ['open calculator']}},
 'note_create': {'name': {'ru': 'Создать заметку', 'en': 'Create a note'},
                 'desc': {'ru': 'Добавить заметку', 'en': 'Add a note'},
                 'examples': {'ru': ['создай заметку: купить молоко'], 'en': ['create a note: buy milk']}},
 'note_list': {'name': {'ru': 'Показать заметки', 'en': 'List notes'},
               'desc': {'ru': 'Список заметок', 'en': 'Show notes list'},
               'examples': {'ru': ['покажи заметки'], 'en': ['list notes']}},
 'note_delete': {'name': {'ru': 'Удалить заметку', 'en': 'Delete a note'},
                 'desc': {'ru': 'Удалить заметку по номеру', 'en': 'Delete a note by index'},
                 'examples': {'ru': ['удали заметку 2'], 'en': ['delete note 2']}},
 'note_update': {'name': {'ru': 'Изменить заметку', 'en': 'Update a note'},
                 'desc': {'ru': 'Изменить текст заметки', 'en': 'Update note text'},
                 'examples': {'ru': ['изменить заметку 2 на купить хлеб'], 'en': ['update note 2 to buy bread']}},
 'note_replace': {'name': {'ru': 'Заменить в заметке', 'en': 'Replace in note'},
                  'desc': {'ru': 'Заменить фрагмент текста в заметке', 'en': 'Replace text in a note'},
                  'examples': {'ru': ['замени в заметке 1 молоко на хлеб'],
                               'en': ['replace in note 1 milk with bread']}},
 'timer_set': {'name': {'ru': 'Таймер', 'en': 'Timer'},
               'desc': {'ru': 'Поставить таймер', 'en': 'Set a timer'},
               'examples': {'ru': ['поставь таймер на 5 минут'], 'en': ['set a timer for 5 minutes']}},
 'timer_cancel': {'name': {'ru': 'Отмена таймера', 'en': 'Cancel timer'},
                  'desc': {'ru': 'Отменить активные таймеры', 'en': 'Cancel active timers'},
                  'examples': {'ru': ['отмени таймер'], 'en': ['cancel timer']}},
 'alarm_set': {'name': {'ru': 'Будильник', 'en': 'Alarm'},
               'desc': {'ru': 'Поставить будильник', 'en': 'Set an alarm'},
               'examples': {'ru': ['поставь будильник на 07:30'], 'en': ['set an alarm for 07:30']}},
 'alarm_cancel': {'name': {'ru': 'Отмена будильника', 'en': 'Cancel alarm'},
                  'desc': {'ru': 'Отменить активные будильники', 'en': 'Cancel active alarms'},
                  'examples': {'ru': ['отмени будильник'], 'en': ['cancel alarm']}},
 'reminder_set': {'name': {'ru': 'Напоминание', 'en': 'Reminder'},
                   'desc': {'ru': 'Создать напоминание', 'en': 'Create a reminder'},
                   'examples': {'ru': ['напомни купить хлеб в 18:30'], 'en': ['remind me to buy bread at 18:30']}},
 'event_add': {'name': {'ru': 'Событие', 'en': 'Event'},
               'desc': {'ru': 'Добавить событие', 'en': 'Add an event'},
               'examples': {'ru': ['создай событие встреча на 10.02.2026 14:00'],
                            'en': ['add event meeting on 2026-02-10 14:00']}},
 'event_list': {'name': {'ru': 'Список событий', 'en': 'Event list'},
                'desc': {'ru': 'Показать события', 'en': 'Show events'},
                'examples': {'ru': ['покажи события'], 'en': ['show events']}},
 'volume_set': {'name': {'ru': 'Громкость', 'en': 'Volume'},
                'desc': {'ru': 'Изменить громкость', 'en': 'Change volume'},
                'examples': {'ru': ['сделай громкость 40'], 'en': ['set volume to 40']}},
 'tts_test': {'name': {'ru': 'Проверка звука', 'en': 'Sound test'},
              'desc': {'ru': 'Проверить озвучку', 'en': 'Test voice output'},
              'examples': {'ru': ['проверка звука'], 'en': ['sound test']}},
 'settings_tts': {'name': {'ru': 'Голос', 'en': 'Voice'},
                  'desc': {'ru': 'Включить или выключить голос', 'en': 'Enable or disable voice'},
                  'examples': {'ru': ['выключи голос', 'включи голос'], 'en': ['disable voice', 'enable voice']}},
 'settings_wake': {'name': {'ru': 'Ключевая фраза', 'en': 'Wake word'},
                   'desc': {'ru': 'Включить или выключить прослушку', 'en': 'Enable or disable wake word'},
                   'examples': {'ru': ['включи прослушку', 'выключи прослушку'],
                                'en': ['enable wake word', 'disable wake word']}},
 'settings_language': {'name': {'ru': 'Язык', 'en': 'Language'},
                       'desc': {'ru': 'Изменить язык', 'en': 'Change language'},
                       'examples': {'ru': ['установи язык русский'], 'en': ['set language en']}},
 'settings_theme': {'name': {'ru': 'Тема', 'en': 'Theme'},
                    'desc': {'ru': 'Изменить тему', 'en': 'Change theme'},
                    'examples': {'ru': ['установи тему неон'], 'en': ['set theme neon']}},
 'settings_accent': {'name': {'ru': 'Акцент', 'en': 'Accent'},
                     'desc': {'ru': 'Изменить цвет акцента', 'en': 'Change accent color'},
                     'examples': {'ru': ['установи акцент #7dd3fc'], 'en': ['set accent #7dd3fc']}},
 'settings_bg_intensity': {'name': {'ru': 'Фон', 'en': 'Background'},
                           'desc': {'ru': 'Изменить яркость фона',
                                    'en': 'Change background intensity'},
                           'examples': {'ru': ['установи фон 70'], 'en': ['set background 70']}},
 'settings_tts_rate': {'name': {'ru': 'Скорость голоса', 'en': 'Voice rate'},
                       'desc': {'ru': 'Изменить скорость голоса', 'en': 'Change voice rate'},
                       'examples': {'ru': ['установи скорость 180'], 'en': ['set voice rate 180']}},
 'settings_tts_volume': {'name': {'ru': 'Громкость голоса', 'en': 'Voice volume'},
                         'desc': {'ru': 'Изменить громкость голоса', 'en': 'Change voice volume'},
                         'examples': {'ru': ['установи громкость голоса 70'],
                                      'en': ['set voice volume 70']}},
 'chat': {'name': {'ru': 'Диалог', 'en': 'Chat'},
          'desc': {'ru': 'Свободный диалог', 'en': 'Free-form chat'},
          'examples': {'ru': ['как дела?', 'что ты умеешь?'], 'en': ['how are you?', 'what can you do?']}},
 'exit': {'name': {'ru': 'Выход', 'en': 'Exit'},
          'desc': {'ru': 'Закрыть приложение', 'en': 'Exit the app'},
          'examples': {'ru': ['выход', 'пока'], 'en': ['exit', 'bye']}},
 'clear_chat': {'name': {'ru': 'Очистить чат', 'en': 'Clear chat'},
                'desc': {'ru': 'Очистить сообщения', 'en': 'Clear messages'},
                'examples': {'ru': ['очисти чат', 'сбрось диалог'], 'en': ['clear chat', 'reset dialog']}}}


_EXAMPLES: Dict[str, List[str]] = {
    "ru": [
        "Как дела?",
        "Что ты умеешь?",
        "Помощь",
        "Открой ютуб",
        "Найди в интернете лучшие фильмы 2025",
        "Поставь таймер на 5 минут",
        "Сделай громкость 40",
        "Создай заметку: купить молоко",
        "Какая сегодня дата?",
    ],
    "en": [
        "How are you?",
        "What can you do?",
        "Help",
        "Open YouTube",
        "Search the web for best movies 2025",
        "Set a timer for 5 minutes",
        "Set volume to 40",
        "Create a note: buy milk",
        "What's the date today?",
    ],
}

_FALLBACK_TEXT = {
    "ru": "Текст недоступен",
    "en": "Text unavailable",
}


def _looks_mojibake(value: str) -> bool:
    if not value:
        return False
    if "????" in value or "�" in value:
        return True
    return any(tok in value for tok in ("Ð", "Ñ", "Â", "â€", "Ã"))


def t(key: str, lang: str) -> str:
    lang = (lang or "ru").lower()
    if key in _UI:
        value = _UI[key].get(lang) or _UI[key].get("ru") or _UI[key].get("en") or ""
        if not value:
            from core.logger import setup_logger

            setup_logger().warning("I18N_MISSING_VALUE key=%s lang=%s", key, lang)
            return _FALLBACK_TEXT.get(lang, _FALLBACK_TEXT.get("en", ""))
        if _looks_mojibake(value):
            from core.logger import setup_logger

            setup_logger().warning("I18N_MOJIBAKE key=%s lang=%s", key, lang)
            return _UI[key].get("en", value) or _FALLBACK_TEXT.get(lang, _FALLBACK_TEXT.get("en", ""))
        return value
    from core.logger import setup_logger

    setup_logger().warning("I18N_MISSING key=%s lang=%s", key, lang)
    return _FALLBACK_TEXT.get(lang, _FALLBACK_TEXT.get("en", ""))


def command_name(cmd: str, lang: str) -> str:
    entry = _COMMANDS.get(cmd, {})
    value = entry.get("name", {}).get(lang) or entry.get("name", {}).get("en") or cmd
    if _looks_mojibake(str(value)):
        from core.logger import setup_logger

        setup_logger().warning("I18N_MOJIBAKE_CMD name=%s lang=%s", cmd, lang)
        return entry.get("name", {}).get("en", cmd)
    return value


def command_desc(cmd: str, lang: str) -> str:
    entry = _COMMANDS.get(cmd, {})
    value = entry.get("desc", {}).get(lang) or entry.get("desc", {}).get("en") or cmd
    if _looks_mojibake(str(value)):
        from core.logger import setup_logger

        setup_logger().warning("I18N_MOJIBAKE_CMD desc=%s lang=%s", cmd, lang)
        return entry.get("desc", {}).get("en", cmd)
    return value


def command_examples(cmd: str, lang: str) -> List[str]:
    entry = _COMMANDS.get(cmd, {})
    examples = entry.get("examples", {}).get(lang, []) or entry.get("examples", {}).get("en", [])
    return list(examples) if examples else []


def check_i18n_integrity() -> None:
    from core.logger import setup_logger

    logger = setup_logger()
    for key, langs in _UI.items():
        if not isinstance(langs, dict):
            continue
        for lang, value in langs.items():
            if _looks_mojibake(str(value)):
                logger.warning("I18N_MOJIBAKE key=%s lang=%s", key, lang)
    for cmd, entry in _COMMANDS.items():
        for field in ("name", "desc"):
            value = entry.get(field, {})
            if isinstance(value, dict):
                for lang, text in value.items():
                    if _looks_mojibake(str(text)):
                        logger.warning("I18N_MOJIBAKE_CMD %s=%s lang=%s", field, cmd, lang)


def help_lines(lang: str, command_ids: List[str]) -> List[str]:
    if (lang or "ru").lower() == "en":
        header = "I'm Antoshka. Here's what I can do:"
    else:
        header = "Я Антошка. Вот что я умею:"
    lines = [header]
    for cmd in command_ids:
        name = command_name(cmd, lang)
        desc = command_desc(cmd, lang)
        ex = command_examples(cmd, lang)
        if ex:
            example = ex[0]
            if (lang or "ru").lower() != "en":
                for candidate in ex:
                    if not any("A" <= ch <= "Z" or "a" <= ch <= "z" for ch in candidate):
                        example = candidate
                        break
            if (lang or "ru").lower() == "en":
                lines.append(f"- {name}: {desc}. Example: \"{example}\"")
            else:
                lines.append(f"- {name}: {desc}. Пример: «{example}»")
        else:
            lines.append(f"- {name}: {desc}")
    return lines


def examples(lang: str) -> List[str]:
    lang = (lang or "ru").lower()
    return _EXAMPLES.get(lang, _EXAMPLES["ru"])


_CAPABILITIES = [
    {
        "id": "basic",
        "icon": "✨",
        "help_title": {"ru": "Базовые", "en": "Basics"},
        "help_desc": {"ru": "Приветствие, помощь, проверка ИИ.", "en": "Greetings, help, and AI check."},
        "help_examples": {
            "ru": ["привет", "помощь", "что ты умеешь", "проверь ии"],
            "en": ["hello", "help", "what can you do", "check ai"],
        },
        "about_title": {"ru": "Общение", "en": "Conversation"},
        "about_features": {
            "ru": ["чат с историей", "ответы на команды", "очистка чата"],
            "en": ["chat with history", "command responses", "clear chat"],
        },
    },
    {
        "id": "timers",
        "icon": "⏱",
        "help_title": {"ru": "Таймеры и будильники", "en": "Timers and alarms"},
        "help_desc": {"ru": "Таймер, будильник и напоминания.", "en": "Timers, alarms, and reminders."},
        "help_examples": {
            "ru": ["поставь таймер на 5 минут", "поставь будильник на 07:30", "напомни в 18:30"],
            "en": ["set a timer for 5 minutes", "set an alarm for 07:30", "remind me at 18:30"],
        },
        "about_title": {"ru": "Таймеры и напоминания", "en": "Timers and reminders"},
        "about_features": {
            "ru": ["таймер", "будильник", "напоминания", "snooze/stop/restart"],
            "en": ["timers", "alarms", "reminders", "snooze/stop/restart"],
        },
    },
    {
        "id": "notes",
        "icon": "📝",
        "help_title": {"ru": "Заметки", "en": "Notes"},
        "help_desc": {"ru": "Создание, список, правка заметок.", "en": "Create, list, and edit notes."},
        "help_examples": {
            "ru": ["создай заметку: купить молоко", "покажи заметки", "удали заметку 2"],
            "en": ["create a note: buy milk", "list notes", "delete note 2"],
        },
        "about_title": {"ru": "Заметки", "en": "Notes"},
        "about_features": {
            "ru": ["создание", "список", "удаление", "редактирование"],
            "en": ["create", "list", "delete", "edit"],
        },
    },
    {
        "id": "browser",
        "icon": "🌐",
        "help_title": {"ru": "Браузер и поиск", "en": "Browser and search"},
        "help_desc": {"ru": "Открыть сайты и поиск.", "en": "Open websites and search."},
        "help_examples": {
            "ru": ["открой ютуб", "открой гугл", "поиск в интернете новости"],
            "en": ["open youtube", "open google", "search the web for news"],
        },
        "about_title": {"ru": "Интернет", "en": "Internet"},
        "about_features": {
            "ru": ["открытие сайтов", "поиск", "карты", "почта"],
            "en": ["open websites", "search", "maps", "mail"],
        },
    },
    {
        "id": "system",
        "icon": "🖥",
        "help_title": {"ru": "Система", "en": "System"},
        "help_desc": {"ru": "Громкость, приложения, скриншот.", "en": "Volume, apps, screenshot."},
        "help_examples": {
            "ru": ["сделай громкость 40", "открой калькулятор", "сделай скриншот"],
            "en": ["set volume to 40", "open calculator", "take a screenshot"],
        },
        "about_title": {"ru": "Система", "en": "System"},
        "about_features": {
            "ru": ["громкость", "открытие файлов/папок", "скриншоты", "приложения"],
            "en": ["volume", "open files/folders", "screenshots", "apps"],
        },
    },
    {
        "id": "settings",
        "icon": "⚙",
        "help_title": {"ru": "Настройки", "en": "Settings"},
        "help_desc": {"ru": "Язык, голос, тема, таймауты.", "en": "Language, voice, theme, timeouts."},
        "help_examples": {
            "ru": ["установи язык русский", "установи тему неон", "установи скорость 180"],
            "en": ["set language to english", "set theme neon", "set voice rate 180"],
        },
        "about_title": {"ru": "Настройки", "en": "Settings"},
        "about_features": {
            "ru": ["язык RU/EN/Auto", "тема и цвет", "таймауты", "уведомления"],
            "en": ["language RU/EN/Auto", "theme & color", "timeouts", "notifications"],
        },
    },
    {
        "id": "voice",
        "icon": "🎙",
        "help_title": {"ru": "Голос", "en": "Voice"},
        "help_desc": {"ru": "Распознавание речи и wake word.", "en": "Speech recognition and wake word."},
        "help_examples": {
            "ru": ["включи прослушку", "выключи прослушку"],
            "en": ["enable wake word", "disable wake word"],
        },
        "about_title": {"ru": "Голос", "en": "Voice"},
        "about_features": {
            "ru": ["STT", "wake word «Антошка»", "выбор микрофона", "тест микрофона"],
            "en": ["STT", "wake word \"Antoshka\"", "microphone selection", "mic test"],
        },
    },
    {
        "id": "tts",
        "icon": "🔊",
        "help_title": {"ru": "Озвучка", "en": "Speech"},
        "help_desc": {"ru": "Озвучивание и тест звука.", "en": "Voice output and sound test."},
        "help_examples": {
            "ru": ["проверка звука", "включи голос", "выключи голос"],
            "en": ["sound test", "enable voice", "disable voice"],
        },
        "about_title": {"ru": "Озвучка", "en": "Speech"},
        "about_features": {
            "ru": ["TTS", "голоса RU/EN", "тест озвучки"],
            "en": ["TTS", "RU/EN voices", "speech test"],
        },
    },
]


def help_sections(lang: str) -> List[Dict[str, str | List[str]]]:
    out: List[Dict[str, str | List[str]]] = []
    for sec in _CAPABILITIES:
        out.append(
            {
                "id": sec.get("id", ""),
                "title": sec["help_title"].get(lang, sec["help_title"]["en"]),
                "desc": sec["help_desc"].get(lang, sec["help_desc"]["en"]),
                "icon": sec.get("icon", ""),
                "examples": list(sec["help_examples"].get(lang, sec["help_examples"]["en"])),
            }
        )
    return out


def about_capabilities(lang: str) -> List[Dict[str, str | List[str]]]:
    out: List[Dict[str, str | List[str]]] = []
    for sec in _CAPABILITIES:
        out.append(
            {
                "id": sec.get("id", ""),
                "title": sec["about_title"].get(lang, sec["about_title"]["en"]),
                "icon": sec.get("icon", ""),
                "features": list(sec["about_features"].get(lang, sec["about_features"]["en"])),
            }
        )
    return out


def about_examples(lang: str) -> List[str]:
    out: List[str] = []
    for sec in _CAPABILITIES:
        if sec.get("id") == "timers":
            out.extend(sec["help_examples"].get(lang, sec["help_examples"]["en"]))
    for sec in _CAPABILITIES:
        if sec.get("id") == "notes":
            out.extend(sec["help_examples"].get(lang, sec["help_examples"]["en"]))
    return out[:6]


_SUGGESTIONS_CACHE: dict[str, dict] = {}


def reset_suggestions_cache() -> None:
    _SUGGESTIONS_CACHE.clear()

def _load_suggestions(lang: str, force_reload: bool = False) -> dict:
    from core.resources import resource_path
    from core.logger import setup_logger
    from services.storage import read_json

    lang = (lang or "en").lower()
    if not force_reload and lang in _SUGGESTIONS_CACHE:
        return _SUGGESTIONS_CACHE[lang]

    logger = setup_logger()
    filename = f"suggestions_{lang}.json"
    path = resource_path(Path("config") / filename)
    data = read_json(path, default={})
    if not isinstance(data, dict):
        data = {}
    _SUGGESTIONS_CACHE[lang] = data
    if not data:
        logger.warning("Suggestions file empty: %s", path)
    if lang == "ru":
        joined = " ".join(
            str(item)
            for group in data.values()
            if isinstance(group, list)
            for item in group
        )
        if joined and not any(ch.isalpha() and "А" <= ch <= "я" for ch in joined):
            logger.warning("Suggestions Cyrillic missing: %s", path)
            data = {}
            _SUGGESTIONS_CACHE[lang] = data
    return data


_SUGGESTIONS_FALLBACK = {
    "ru": [
        "Помощь",
        "Что ты умеешь?",
        "Поставь таймер на 10 секунд",
        "Поставь будильник на 07:30",
        "Напомни мне через 5 минут",
    ],
    "en": [
        "Help",
        "What can you do?",
        "Set a timer for 10 seconds",
        "Set an alarm for 07:30",
        "Remind me in 5 minutes",
    ],
}


def suggestions_for_context(lang: str, context: str, force_reload: bool = False) -> List[str]:
    import random
    from core.logger import setup_logger

    logger = setup_logger()
    lang = (lang or "en").lower()
    ctx = (context or "default").lower()

    data = _load_suggestions(lang, force_reload=force_reload)
    if ctx == "unknown" and "unknown_fallback" in data:
        ctx = "unknown_fallback"
    general = list(data.get("general_chat", []))
    pool = list(data.get(ctx, []))
    if len(pool) < 5:
        pool.extend([x for x in general if x not in pool])
    if len(pool) < 5:
        pool.extend([x for x in data.get("start", []) if x not in pool])

    pool = [str(x) for x in pool if isinstance(x, str) and x.strip()]
    if any(_looks_mojibake(x) for x in pool):
        logger.warning("SUGGESTIONS_MOJIBAKE lang=%s ctx=%s", lang, ctx)
        pool = [x for x in pool if not _looks_mojibake(x)]

    unique = list(dict.fromkeys(pool))
    if len(unique) >= 5:
        picked = random.sample(unique, k=5)
    else:
        picked = unique

    if len(picked) < 5:
        fallback = _SUGGESTIONS_FALLBACK.get(lang, _SUGGESTIONS_FALLBACK.get("en", []))
        for item in fallback:
            if item not in picked:
                picked.append(item)
            if len(picked) >= 5:
                break

    picked = picked[:5]
    logger.info(
        "SUGGESTIONS_PICK lang=%s ctx=%s pool=%s picked=%s",
        lang,
        ctx,
        len(unique),
        len(picked),
    )
    return picked
