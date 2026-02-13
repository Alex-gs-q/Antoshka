import sys

from core.config import load_settings
from core.app_context import AppContext
from core.dialogue import Dialogue, DialogueConfig
from core.i18n import t as tr, check_i18n_integrity
from core.language import resolve_language
from core.logger import setup_logger
from core.paths import data_dir
from core.stt import create_stt
from core.tts import TTS, TTSConfig
from core.windows_appid import set_app_user_model_id
from llm.client import LLMClient, LLMConfig
from services.scheduler import Scheduler
from services.volume import VolumeController


def _configure_stdio_utf8() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        setup_logger().exception("STDIO reconfigure failed: %s", e)


def main():
    set_app_user_model_id("Antoshka.Assistant")
    _configure_stdio_utf8()
    logger = setup_logger()
    check_i18n_integrity()
    if "--self-test" in sys.argv:
        try:
            from tools.smoke_check import run_self_test
        except Exception as e:  # noqa: BLE001
            logger.exception("Self-test import failed: %s", e)
            raise SystemExit(1)
        raise SystemExit(run_self_test())
    settings = load_settings()
    lang_mode = (settings.get("app", {}) or {}).get("language", "auto")
    current_lang = resolve_language(lang_mode, None, fallback="ru")

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
        if "OPENAI_API_KEY is missing" in str(e):
            msg = tr("msg_ai_missing_key", current_lang)
            print(f"{tr('app_name', current_lang)}: {msg}")

    def notify(message: str) -> None:
        prefix = tr("app_name", current_lang)
        print(f"{prefix}: {message}")
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
        data_dir=data_dir(),
        scheduler=scheduler,
        volume=volume,
        llm_client=llm_client,
        language_mode=lang_mode,
        language=current_lang,
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

    hello = tr("msg_console_hello", current_lang)
    print(f"{tr('app_name', current_lang)}: {hello}")
    tts.say(hello)

    while True:
        text = stt.listen()

        if text is None:
            print(f"\n{tr('app_name', current_lang)}: {tr('msg_bye', current_lang)}")
            tts.say(tr("msg_bye", current_lang))
            break

        if text == "":
            continue

        lang = resolve_language(lang_mode, text, fallback=current_lang)
        current_lang = lang
        app_context.language = lang
        answer = dialogue.handle_text(text, language=lang)

        if answer == "__EXIT__":
            print(f"{tr('app_name', current_lang)}: {tr('msg_bye', current_lang)}")
            tts.say(tr("msg_bye", current_lang))
            break

        print(f"Антошка: {answer}")
        tts.say(answer)


if __name__ == "__main__":
    main()
