import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile


def setup_logger(name: str = "antoshka", level: str = "INFO") -> logging.Logger:
    """
    Creates and returns a logger.
    Writes:
    - to console
    - to logs/app.log (rotating)
    """
    logger = logging.getLogger(name)

    # avoid duplicate handlers
    if logger.handlers:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        _ensure_app_log_handler(logger)
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    logs_dir = _get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "antoshka.log"
    app_log_file = logs_dir / "app.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    app_file_handler = RotatingFileHandler(
        filename=str(app_log_file),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    app_file_handler.setFormatter(fmt)
    logger.addHandler(app_file_handler)

    logger.propagate = False
    logger.info("Logger initialized")
    return logger


def _ensure_app_log_handler(logger: logging.Logger) -> None:
    logs_dir = _get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_file = str(logs_dir / "app.log")
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            if str(handler.baseFilename) == app_log_file:
                return
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app_file_handler = RotatingFileHandler(
        filename=app_log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    app_file_handler.setFormatter(fmt)
    logger.addHandler(app_file_handler)


def _get_logs_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Antoshka" / "logs"
    try:
        return Path("logs").resolve()
    except Exception:
        return Path(tempfile.gettempdir()) / "Antoshka" / "logs"
