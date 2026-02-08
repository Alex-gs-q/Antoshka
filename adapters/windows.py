from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional

from core.logger import setup_logger

logger = setup_logger()


def open_url(url: str) -> bool:
    """Открыть URL в браузере по умолчанию."""
    try:
        webbrowser.open(url, new=2)
        logger.info("WindowsAdapter: opened url=%s", url)
        return True
    except Exception as e:
        logger.exception("WindowsAdapter: failed to open url=%s err=%s", url, e)
        return False


def open_path(path: str) -> bool:
    """Открыть файл/папку в проводнике или связанной программе."""
    try:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()

        if not p.exists():
            logger.warning("WindowsAdapter: path not found=%s", str(p))
            return False

        os.startfile(str(p))  # noqa: S606 (windows only)
        logger.info("WindowsAdapter: opened path=%s", str(p))
        return True
    except Exception as e:
        logger.exception("WindowsAdapter: failed to open path=%s err=%s", path, e)
        return False


def run_app(command: str, args: Optional[list[str]] = None) -> bool:
    """
    Запустить приложение.
    command: имя (notepad) или путь к exe
    args: список аргументов
    """
    args = args or []
    try:
        subprocess.Popen([command, *args], shell=False)  # noqa: S603
        logger.info("WindowsAdapter: started app=%s args=%s", command, args)
        return True
    except FileNotFoundError:
        logger.warning("WindowsAdapter: app not found=%s", command)
        return False
    except Exception as e:
        logger.exception("WindowsAdapter: failed to run app=%s err=%s", command, e)
        return False
