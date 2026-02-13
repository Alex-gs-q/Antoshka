from __future__ import annotations

import sys

from core.logger import setup_logger

def set_app_user_model_id(app_id: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(app_id))
    except Exception as e:  # noqa: BLE001
        setup_logger().exception("AppUserModelID setup failed: %s", e)
