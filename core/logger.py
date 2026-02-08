import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "antoshka", level: str = "INFO") -> logging.Logger:
    """
    Создает и возвращает логгер.
    Пишет:
    - в консоль
    - в logs/antoshka.log (с ротацией)
    """
    logger = logging.getLogger(name)

    # чтобы не дублировались хендлеры при повторном вызове
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "antoshka.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Консоль
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Файл с ротацией (1MB * 3 файла)
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    logger.info("Logger initialized")
    return logger
