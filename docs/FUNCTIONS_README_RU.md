# Antoshka: Подробная Карта Функций И Реализации

Этот файл объясняет, что умеет Antoshka и где это реализовано в коде.

## 1. Точки входа

- GUI: `antoshka_ui.py`
- CLI: `antoshka.py`

Обе поддерживают:
- `--self-test` -> `core/selftest.py`
- `--smoke` -> `core/selftest.py`

## 2. Основные слои

- UI слой: `ui/qt_app.py`
- Диалог/оркестрация: `core/dialogue.py`
- Роутинг команд: `core/router.py`, `commands/registry.py`, `commands/builtins.py`
- Конфиг и сохранение: `config/settings.py`, `core/config.py`, `services/storage.py`
- Голосовой ввод/вывод: `core/stt.py`, `core/stt_vosk.py`, `services/tts/tts_worker.py`
- Таймеры/напоминания/алармы: `services/scheduler.py`, `alerts/`
- Интеграции: `services/`, `adapters/windows.py`

## 3. Функции UI (Qt)

Главное окно:
- `AntoshkaWindow` в `ui/qt_app.py`

Ключевые действия:
- Отправка текста: `_send_text()`
- Слушать/стоп: `_toggle_listen()`, `_listen()`, `_stop_listen()`
- Открыть настройки: `_open_settings()`
- Открыть историю: `_open_history()`
- Открыть громкость: `_open_volume()`
- Переключить ИИ: `_toggle_ai_mode()`
- Очистить чат: `_clear_chat_clicked()`

Статусы и уведомления:
- Статус UI: `_set_status()`
- Всплывающие уведомления в приложении: `InAppToast`, `_show_in_app_toast()`
- Сообщения в чат: `_append_message()`
- Системные уведомления/трей: `_init_tray_and_notifications()`, `_notify_system_event()`

## 4. Распознавание речи (STT / Vosk)

Файлы:
- `core/stt.py` (выбор режима, fallback, статус)
- `core/stt_vosk.py` (цикл распознавания с микрофона)

Ключевая логика:
- Единый статус STT: `get_stt_status(settings)` в `core/stt.py`
- Валидация модели: `validate_vosk_model_dir(path)` в `core/stt.py`
- Автопоиск модели:
  - `./models/vosk`
  - `./models/vosk-model*`
  - папки рядом с exe
  - `_internal/models/...`
  - пути для frozen (`sys._MEIPASS`, `resource_path`)
- Мягкий fallback в текстовый режим: `create_stt(settings)`

Интеграция с UI:
- Обновление статуса: `ui/qt_app.py::_report_stt_status()`
- Включение/выключение кнопки "Слушать": `_apply_stt_mode_ui()`
- Баннер без спама: `update_or_set_banner()` / `clear_banner()`
- Защитный диалог при клике без модели: `_show_vosk_required_dialog()`

## 5. Система настроек

Файлы:
- Дефолты: `config/settings.py` (`DEFAULT_SETTINGS`)
- Загрузка/сохранение: `core/config.py` (`load_settings`, `save_settings`)
- Окно настроек: `ui/qt_app.py::_open_settings()`

Поток применения:
1. Пользователь меняет параметры в UI
2. `_save_settings(...)` обновляет `self.settings`
3. `save_settings(self.settings)` пишет `config/settings.json`
4. `_on_settings_changed(self.settings)` применяет без перезапуска:
   - язык
   - STT/TTS
   - wake word
   - тему
   - состояния кнопок/tooltip/баннеров

## 6. Блок Vosk в настройках

Локация:
- `ui/qt_app.py::_open_settings()`

Содержит:
- текущий путь модели
- статус найдена/не найдена
- кнопку выбора папки
- кнопку инструкции
- кнопку открытия страницы моделей

Применение:
- после выбора пути сразу: `save_settings` -> `_on_settings_changed` -> реинициализация STT
- перезапуск приложения не нужен

## 7. Интернационализация (i18n)

Файл:
- `core/i18n.py`

Функция:
- `t(key, lang)` возвращает локализованную строку с fallback

Ключи:
- `btn_*` кнопки
- `label_*` подписи
- `msg_*` системные и чат-сообщения

Правило:
- пользовательские системные тексты должны идти через `tr(...)` (`t(...)`).

## 8. Диалог и выполнение команд

Пайплайн:
1. Ввод (голос/текст) попадает в `ui/qt_app.py::_process_text()`
2. Роутинг через `core/dialogue.py` + `core/router.py`
3. Хендлеры из `commands/builtins.py`
4. Возврат `ActionResult`/текста в UI

Домены команд:
- приветствие/помощь
- время/дата
- браузер/поиск/URL
- запуск приложений/открытие путей
- заметки (create/list/update/delete/replace)
- таймеры/будильники/напоминания/события
- голосовые настройки (язык/тема/голос)
- погода
- выход/очистка чата

## 9. Таймеры, будильники, напоминания, события

Файлы:
- планировщик: `services/scheduler.py`
- UI/алерты: `alerts/` + обработка в `ui/qt_app.py`

Действия в UI:
- snooze (отложить)
- stop (остановить)
- restart (перезапустить)

Отображение:
- карточка в чате
- popup окно
- системное уведомление/трей (при включении)

## 10. Озвучка (TTS)

Файлы:
- `services/tts/tts_worker.py`
- `services/tts/voices.py`
- `core/tts.py` (CLI)

Поведение:
- авто-выбор провайдера
- обновление голоса/скорости/тона/громкости из настроек
- асинхронная озвучка из UI (`_say_tts_async`)

## 11. AI/LLM

Файлы:
- `llm/client.py`
- переключатели в `ui/qt_app.py`

Поведение:
- при недоступном API ключе локальные команды продолжают работать
- AI режим включается/выключается на лету
- очередь ответов управляется без блокировки UI

## 12. Слой безопасности

Файл:
- `core/safety.py`

Назначение:
- подтверждение потенциально опасных действий
- фраза подтверждения и TTL берутся из настроек

## 13. Тесты и проверки

Основные тесты:
- `tests/` (роутер, команды, парсеры, заметки, i18n, STT-хелперы, alerts)

UI guard-тесты:
- `tests/test_qt_key_buttons.py`
  - disable "Слушать" без STT
  - отсутствие дублей баннера STT
  - re-enable после появления валидной модели
  - guard-диалог для missing model

Проверки релиза:
- `tools/smoke_test.py`
- `core/selftest.py`

## 14. Сборка и упаковка

Spec-файлы:
- folder build: `Antoshka_pyinstaller.spec`
- onefile build: `Antoshka_onefile.spec`

Скрипты:
- `build.ps1`
- `build_onefile.ps1`

Артефакты:
- `dist/AntoshkaApp/AntoshkaApp.exe`
- `dist/AntoshkaApp_Windows.zip`

## 15. Быстрый индекс "где искать фичу X"

- Логика кнопки "Слушать" -> `ui/qt_app.py::_toggle_listen`, `_apply_stt_mode_ui`
- Статус STT/валидация модели -> `core/stt.py`
- Цикл распознавания Vosk -> `core/stt_vosk.py`
- Сохранение/применение настроек -> `ui/qt_app.py::_save_settings`, `_on_settings_changed`
- i18n строки -> `core/i18n.py`
- Реализация команд -> `commands/builtins.py`
- Планировщик/алерты -> `services/scheduler.py`, `alerts/`, `ui/qt_app.py`

