import sys

from core.logger import setup_logger
from core.windows_appid import set_app_user_model_id
from ui.qt_app import run


def main() -> None:
    set_app_user_model_id("Antoshka.Assistant")
    if "--self-test" in sys.argv:
        logger = setup_logger()
        try:
            from tools.smoke_check import run_self_test
        except Exception as e:  # noqa: BLE001
            logger.exception("Self-test import failed: %s", e)
            raise SystemExit(1)
        raise SystemExit(run_self_test())
    run()


if __name__ == "__main__":
    main()
