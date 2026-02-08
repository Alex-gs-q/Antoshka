# Antoshka

Voice assistant with CLI and desktop UI.

## Run

CLI:

```bash
python antoshka.py
```

UI:

```bash
python antoshka_ui.py
```

## First Run (Windows)

If you get UnicodeEncodeError in console, run:

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

To avoid microphone/Vosk issues on the first run, set in `config/settings.json`:

```json
{
  "stt": {"mode": "text"},
  "ui": {"wake_word": false}
}
```

## STT/TTS

- Text mode uses console input (CLI only).
- For microphone use Vosk: download a model into `models/vosk` and set `stt.mode` to `vosk` in `config/settings.json`.
- TTS settings are in `config/settings.json` (provider/voice/rate/pitch).
- On Windows, `edge-tts` is used automatically when available (recommended).

## LLM

Set `OPENAI_API_KEY` in `.env` and `llm.provider` to `openai` in `config/settings.json`.
If the key is missing or looks like a placeholder, UI shows a clear diagnostic message and falls back to local commands.

## Wake Word

- Enable in Settings: `Wake word: on`.
- Phrase: "antoshka slushay" (translit).
- Requires Vosk model and microphone permissions.

## Tests

```bash
pytest
```

## Build (Windows)

```bash
pip install -r requirements-dev.txt
python -m PyInstaller Antoshka_pyinstaller.spec
```
