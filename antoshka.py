from core.logger import setup_logger


def main() -> None:
    logger = setup_logger(level="INFO")
    logger.info("Antoshka MVP: starting...")


if __name__ == "__main__":
    main()
