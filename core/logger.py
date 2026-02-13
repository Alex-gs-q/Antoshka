import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import tempfile
from typing import Optional

from core.paths import logs_dir


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

    log_dir_path = _get_logs_dir()
    try:
        log_dir_path.mkdir(parents=True, exist_ok=True)
    except Exception:
        log_dir_path = Path(tempfile.gettempdir()) / "Antoshka" / "logs"
        log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file = log_dir_path / "antoshka.log"
    app_log_file = log_dir_path / "app.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(_MaskSecretsFilter())
    logger.addHandler(console)

    file_handler = _make_rotating_handler(log_file, fmt)
    if file_handler is not None:
        logger.addHandler(file_handler)

    app_file_handler = _make_rotating_handler(app_log_file, fmt)
    if app_file_handler is not None:
        logger.addHandler(app_file_handler)

    logger.propagate = False
    logger.info("Logger initialized")
    return logger


def _ensure_app_log_handler(logger: logging.Logger) -> None:
    log_dir_path = _get_logs_dir()
    try:
        log_dir_path.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    app_log_file = str(log_dir_path / "app.log")
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            if str(handler.baseFilename) == app_log_file:
                return
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = _make_rotating_handler(Path(app_log_file), fmt)
    if handler is not None:
        logger.addHandler(handler)


def _get_logs_dir() -> Path:
    if getattr(sys, "frozen", False):
        return logs_dir()
    try:
        return Path("logs").resolve()
    except Exception:
        return Path(tempfile.gettempdir()) / "Antoshka" / "logs"


class _MaskSecretsFilter(logging.Filter):
    _re_key = re.compile(r"(sk-[A-Za-z0-9]{8,})")
    _re_env = re.compile(r"(OPENAI_API_KEY=)([^\s]+)")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        msg = self._re_key.sub("sk-****", msg)
        msg = self._re_env.sub(r"\1****", msg)
        record.msg = msg
        record.args = ()
        return True


def _make_rotating_handler(path: Path, fmt: logging.Formatter) -> Optional[RotatingFileHandler]:
    try:
        handler = RotatingFileHandler(
            filename=str(path),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(fmt)
        handler.addFilter(_MaskSecretsFilter())
        return handler
    except Exception:
        return None
