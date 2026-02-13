import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--self-test", action="store_true", dest="self_test")
    parser.add_argument("--smoke", action="store_true")
    args, _unknown = parser.parse_known_args(argv)
    return args


def _detect_activation_arg(values: list[str]) -> str | None:
    for arg in values:
        if "action=" in arg and "id=" in arg:
            return arg
    return None


def main() -> None:
    args = _parse_args()

    if args.self_test:
        from core.selftest import run_self_test

        raise SystemExit(run_self_test())

    if args.smoke:
        from core.selftest import run_smoke

        raise SystemExit(run_smoke())

    from core.windows_appid import set_app_user_model_id
    from ui.qt_app import run

    set_app_user_model_id("Antoshka.Assistant")
    activation_args = _detect_activation_arg(sys.argv[1:])
    run(activation_args)


if __name__ == "__main__":
    main()
