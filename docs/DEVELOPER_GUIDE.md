## Антошка — Руководство разработчика

### Архитектура
- `ui/qt_app.py` — основной UI, окно, чат, настройки.
- `core/` — диалог, безопасность, i18n, STT/TTS.
- `commands/` — команды и паттерны.
- `services/` — заметки, напоминания, микрофон, история, хранение.
- `adapters/` — платформенные вызовы (Windows).
- `config/` — настройки и дефолты.

### Важные точки интеграции
1. `core/dialogue.py` — главный вход в логику команд.
2. `commands/builtins.py` — регистрация команд и их обработчики.
3. `core/safety.py` — подтверждения и опасные действия.
4. `services/audio/microphone.py` — микрофон и VU meter.
5. `core/stt_vosk.py` — голосовое распознавание.
6. `services/tts/` — озвучка.

### Добавление новой команды
1. В `commands/builtins.py`:
   - добавить `_cmd(...)`
   - добавить `_handle_*`
2. В `core/i18n.py`:
   - добавить тексты команд (name/desc/examples)
   - добавить сообщения (msg_*)
3. При необходимости: обновить `core/safety.py` (allow/confirm).

### Настройки
Дефолты: `config/settings.py`  
Файл пользователя: `config/settings.json`

### Логи
Файл логов: `logs/app.log`

### Проверки перед билдом
1. Установлены зависимости.
2. Модели Vosk скачаны:
   - `models/vosk`
   - `models/vosk_en`
3. `config/settings.json` в UTF‑8 без “кракозябр”.
4. UI запускается из `antoshka_ui.py`.

