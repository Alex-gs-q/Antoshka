from core.config import load_settings
from core.dialogue import Dialogue, DialogueConfig
from core.logger import setup_logger
from core.tts import TTS, TTSConfig


def main():
    logger = setup_logger()
    settings = load_settings()

    dangerous_mode = bool(settings.get("safety", {}).get("dangerous_mode", False))

    logger.info("Antoshka started")
    logger.info("STT mode: text")
    logger.info("Dangerous mode: %s", dangerous_mode)

    dialogue = Dialogue(DialogueConfig(dangerous_mode=dangerous_mode))

    # --- TTS init (один раз при старте) ---
    tts_raw = settings.get("tts", {}) or {}
    tts = TTS(
        TTSConfig(
            enabled=bool(tts_raw.get("enabled", True)),
            rate=int(tts_raw.get("rate", 180)),
            volume=float(tts_raw.get("volume", 1.0)),
            voice_name_contains=tts_raw.get("voice_name_contains"),
        )
    )

    start_msg = "Антошка: текстовый режим. Напиши команду (или 'помощь'). Для выхода: 'выход'."
    print(start_msg)
    tts.say(start_msg)

    while True:
        try:
            text = input("Ты: ").strip()
        except (EOFError, KeyboardInterrupt):
            bye = "Антошка: пока!"
            print("\n" + bye)
            tts.say("Пока!")
            break

        answer = dialogue.handle_text(text)

        if answer == "__EXIT__":
            bye = "Антошка: пока!"
            print(bye)
            tts.say("Пока!")
            break

        print(f"Антошка: {answer}")
        tts.say(answer)


if __name__ == "__main__":
    main()
