from core.config import load_settings
from core.dialogue import Dialogue, DialogueConfig
from core.logger import setup_logger
from core.stt import create_stt
from core.tts import TTS, TTSConfig


def main():
    logger = setup_logger()
    settings = load_settings()

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

    dialogue = Dialogue(DialogueConfig(dangerous_mode=dangerous_mode))

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
