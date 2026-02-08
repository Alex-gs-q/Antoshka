import sys

from core.config import load_settings
from core.actions import ActionResult
from pathlib import Path

from core.app_context import AppContext
from core.dialogue import Dialogue, DialogueConfig
from core.logger import setup_logger
from core.stt import create_stt
from core.tts import TTS, TTSConfig
from llm.client import LLMClient, LLMConfig
from services.scheduler import Scheduler
from services.volume import VolumeController


def _configure_stdio_utf8() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    _configure_stdio_utf8()
    logger = setup_logger()
    settings = load_settings()

    # safety
    dangerous_mode = bool(settings.get("safety", {}).get("dangerous_mode", False))

    # TTS
    tts_raw = settings.get("tts", {}) or {}
    tts = TTS(
        TTSConfig(
            enabled=bool(tts_raw.get("enabled", True)),
            rate=int(tts_raw.get("rate", 180)),
            volume=float(tts_raw.get("volume", 1.0)),
            voice_name_contains=tts_raw.get("voice_name_contains"),
        )
    )

    logger.info("Antoshka started")
    logger.info("STT mode: %s", (settings.get("stt", {}) or {}).get("mode", "text"))
    logger.info("Dangerous mode: %s", dangerous_mode)

    # LLM
    llm_client = None
    llm_raw = settings.get("llm", {}) or {}
    try:
        llm_client = LLMClient(
            LLMConfig(
                provider=str(llm_raw.get("provider", "dummy")),
                model=str(llm_raw.get("model", "gpt-4o-mini")),
                history_max_messages=int(llm_raw.get("history_max_messages", 10)),
            )
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM disabled: %s", e)

    def notify(message: str) -> None:
        print(f"Антошка: {message}")
        tts.say(message)

    scheduler = Scheduler(notify=notify)

    volume = None
    if tts.engine is not None:
        volume = VolumeController(
            get_level=tts.get_volume,
            set_level=tts.set_volume,
            set_mute_fn=tts.set_mute,
        )

    app_context = AppContext(
        notify=notify,
        data_dir=Path("data"),
        scheduler=scheduler,
        volume=volume,
        llm_client=llm_client,
    )

    dialogue = Dialogue(
        DialogueConfig(
            dangerous_mode=dangerous_mode,
            llm_client=llm_client,
            app_context=app_context,
        )
    )

    # STT
    stt = create_stt(settings)

    hello = "текстовый режим. Напиши команду (или 'помощь'). Для выхода: 'выход'."
    print(f"Антошка: {hello}")
    tts.say(hello)

    while True:
        text = stt.listen()

        if text is None:
            print("\nАнтошка: пока!")
            tts.say("Пока!")
            break

        if text == "":
            continue

        answer = dialogue.handle_text(text)

        if answer == "__EXIT__":
            print("Антошка: пока!")
            tts.say("Пока!")
            break

        print(f"Антошка: {answer}")
        tts.say(answer)


if __name__ == "__main__":
    main()
