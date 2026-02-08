from core.config import load_settings
from core.logger import setup_logger


def main() -> None:
    settings = load_settings()
    logger = setup_logger(level=settings["app"]["log_level"])

    logger.info("Antoshka started")
    logger.info("STT mode: %s", settings["stt"]["mode"])
    logger.info("Dangerous mode: %s", settings["safety"]["dangerous_mode"])
    logger.info("LLM provider: %s", settings["llm"]["provider"])


if __name__ == "__main__":
    main()
