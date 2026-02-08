from core.config import load_settings
from core.logger import setup_logger
from core.stt_vosk import VoskSTT, VoskConfig


def main():
    logger = setup_logger()
    settings = load_settings()

    stt_raw = settings.get("stt", {}) or {}
    model_path = stt_raw.get("vosk_model_path") or "models/vosk"

    stt = VoskSTT(VoskConfig(model_path=str(model_path)))
    print("Скажи фразу в микрофон (и замолчи на секунду). Таймаут 8 секунд...")

    text = stt.listen()
    print(f"Распознано: {text!r}")

    logger.info("STT smoke test done. text=%r", text)


if __name__ == "__main__":
    main()