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

## STT/TTS

- Text mode uses console input (CLI only).
- For microphone use Vosk: download a model into `models/vosk` and set `stt.mode` to `vosk` in `config/settings.json`.

## LLM

Set `OPENAI_API_KEY` in `.env` and `llm.provider` to `openai` in `config/settings.json`.

## Tests

```bash
pytest
```

## Build (Windows)

```bash
pip install -r requirements-dev.txt
python -m PyInstaller Antoshka.spec
```
