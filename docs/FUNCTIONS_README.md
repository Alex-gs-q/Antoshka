# Antoshka: Functions And Code Map

This document explains what Antoshka can do and where each feature is implemented in code.

## 1. Entry Points

- GUI entry: `antoshka_ui.py`
- CLI entry: `antoshka.py`

Both support:
- `--self-test` -> `core/selftest.py`
- `--smoke` -> `core/selftest.py`

## 2. Main Layers

- UI layer: `ui/qt_app.py`
- Dialogue/orchestration: `core/dialogue.py`
- Command routing: `core/router.py`, `commands/registry.py`, `commands/builtins.py`
- Configuration and persistence: `config/settings.py`, `core/config.py`, `services/storage.py`
- Voice input/output: `core/stt.py`, `core/stt_vosk.py`, `services/tts/tts_worker.py`
- Alerts/timers/reminders: `services/scheduler.py`, `alerts/`
- Integrations: `services/` and `adapters/windows.py`

## 3. UI Functions (Qt)

Main window class:
- `AntoshkaWindow` in `ui/qt_app.py`

Top-level UI actions:
- Send text: `_send_text()`
- Listen/stop listen: `_toggle_listen()`, `_listen()`, `_stop_listen()`
- Open settings: `_open_settings()`
- Open history: `_open_history()`
- Open volume: `_open_volume()`
- Toggle AI mode: `_toggle_ai_mode()`
- Clear chat: `_clear_chat_clicked()`

Status and notifications:
- In-app status: `_set_status()`
- Toasts: `InAppToast` and `_show_in_app_toast()`
- Chat messages: `_append_message()`
- System notifications/tray: `_init_tray_and_notifications()`, `_notify_system_event()`

## 4. Speech Recognition (STT / Vosk)

Main files:
- `core/stt.py` (selection/fallback/status)
- `core/stt_vosk.py` (Vosk microphone recognition loop)

Key behavior:
- Single source of truth for STT availability: `get_stt_status(settings)` in `core/stt.py`
- Vosk model validation: `validate_vosk_model_dir(path)` in `core/stt.py`
- Model auto-discovery candidates:
  - `./models/vosk`
  - `./models/vosk-model*`
  - frozen app dirs (`sys._MEIPASS`, exe dir, `_internal/models/...`)
- Graceful fallback to text STT when model/deps are unavailable: `create_stt(settings)`

UI integration:
- Status refresh: `ui/qt_app.py::_report_stt_status()`
- Listen button state: `ui/qt_app.py::_apply_stt_mode_ui()`
- Missing model banner (non-spam): `update_or_set_banner()` / `clear_banner()`
- Guard dialog on listen click with missing model: `_show_vosk_required_dialog()`

## 5. Settings System

Files:
- Defaults: `config/settings.py` (`DEFAULT_SETTINGS`)
- Runtime load/save: `core/config.py` (`load_settings`, `save_settings`)
- UI settings dialog: `ui/qt_app.py::_open_settings()`

Save/apply flow:
1. User changes settings in UI
2. `_save_settings(...)` writes into `self.settings`
3. `save_settings(self.settings)` persists to `config/settings.json`
4. `_on_settings_changed(self.settings)` hot-applies:
   - language
   - STT/TTS
   - wake word
   - theme
   - button/tooltips/status

## 6. Vosk Settings Block (Release-safe)

Location:
- `ui/qt_app.py::_open_settings()`

Controls:
- model path label (`vosk_model_path`)
- status label (found/missing)
- choose folder button
- install-help dialog button
- open model page button

Immediate apply:
- after path selection: save settings -> `_on_settings_changed()` -> STT reinit
- no app restart required

## 7. Internationalization (i18n)

File:
- `core/i18n.py`

Function:
- `t(key, lang)` returns localized string with fallback protection

Used key groups:
- `btn_*` for buttons
- `label_*` for labels
- `msg_*` for user/system messages
- command metadata for help/examples

Important note:
- All system-visible messages should go through `tr(...)` (`t(...)` alias in UI code).

## 8. Dialogue And Command Execution

Pipeline:
1. User input (voice/text) enters `ui/qt_app.py::_process_text()`
2. Routed via `core/dialogue.py` + `core/router.py`
3. Command handlers from `commands/builtins.py`
4. Return `ActionResult`/text to UI

Command domains in `commands/builtins.py` include:
- greetings/help
- time/date
- browser/search/open URL
- open app/path
- notes CRUD
- timers/alarms/reminders/events
- settings commands (theme/language/voice)
- weather
- exit/clear chat

## 9. Timers, Alarms, Reminders, Events

Files:
- scheduling core: `services/scheduler.py`
- alert rendering/controls: `alerts/`, plus UI handlers in `ui/qt_app.py`

UI alert actions:
- snooze
- stop
- restart (for supported event types)

Display modes:
- chat alert card
- popup alert window
- optional tray/system notification duplication

## 10. TTS (Speech Output)

Files:
- `services/tts/tts_worker.py`
- `services/tts/voices.py`
- `core/tts.py` (CLI side)

Behavior:
- provider auto-selection
- runtime voice/rate/pitch/volume update from settings
- async queue playback from UI (`_say_tts_async`)

## 11. AI/LLM

Files:
- `llm/client.py`
- UI toggles in `ui/qt_app.py`

Behavior:
- if API key/provider is unavailable, app remains functional with local commands
- AI mode can be toggled live
- responses are queued/managed to avoid UI blocking

## 12. Safety Layer

File:
- `core/safety.py`

Purpose:
- protects potentially dangerous actions with confirmation workflow
- uses confirmation phrase and TTL from settings

## 13. Testing And Quality Gates

Core tests:
- `tests/` (router, commands, parsers, notes, STT helpers, i18n, alerts)

Added UI guard tests:
- `tests/test_qt_key_buttons.py`
  - listen disabled when STT unavailable
  - no duplicate STT banner
  - listen re-enabled after valid model appears
  - missing-model guard dialog path

Release checks:
- `tools/smoke_test.py`
- `core/selftest.py`

## 14. Build And Packaging

Specs:
- folder build: `Antoshka_pyinstaller.spec`
- onefile build: `Antoshka_onefile.spec`

Scripts:
- `build.ps1`
- `build_onefile.ps1`

Artifacts:
- `dist/AntoshkaApp/AntoshkaApp.exe`
- `dist/AntoshkaApp_Windows.zip`

## 15. If Someone Asks "Where Exactly Is Feature X?"

Use this quick map:
- Listen button logic -> `ui/qt_app.py::_toggle_listen`, `_apply_stt_mode_ui`
- STT availability/model validation -> `core/stt.py`
- Vosk recognizer audio loop -> `core/stt_vosk.py`
- Settings save/apply -> `ui/qt_app.py::_save_settings`, `_on_settings_changed`
- i18n strings -> `core/i18n.py`
- Command implementation -> `commands/builtins.py`
- Scheduler/alerts -> `services/scheduler.py`, `alerts/`, `ui/qt_app.py`

