from __future__ import annotations

import importlib
import logging
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Callable

from core.logger import setup_logger
from core.paths import data_dir, logs_dir
from core.resources import resource_path

WATCHDOG_SECONDS = 15.0


class SelfTestFailure(RuntimeError):
    pass


def _safe_logger() -> logging.Logger:
    try:
        return setup_logger()
    except Exception:
        logger = logging.getLogger("antoshka-selftest")
        if not logger.handlers:
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        return logger


def _report_paths() -> list[Path]:
    paths: list[Path] = []
    try:
        paths.append(logs_dir() / "pre_release_report.txt")
    except Exception:
        pass
    try:
        exe_dir = Path(sys.executable).resolve().parent
        paths.append(exe_dir / "pre_release_report.txt")
    except Exception:
        pass
    try:
        paths.append(Path.cwd() / "logs" / "pre_release_report.txt")
    except Exception:
        pass
    try:
        paths.append(Path.cwd() / "pre_release_report.txt")
    except Exception:
        pass
    dedup: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    return dedup


def _write_report(lines: list[str]) -> Path | None:
    for path in _report_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return path
        except Exception:
            continue
    return None


def _deadline_guard(started_at: float, stage: str, limit: float = WATCHDOG_SECONDS) -> None:
    if (time.perf_counter() - started_at) > limit:
        raise SelfTestFailure(f"timeout at stage: {stage}")


def _has_non_ascii(value: str) -> bool:
    return any(ord(ch) > 127 for ch in value)


def _append_frozen_path_warning(log: logging.Logger, report: list[str]) -> None:
    if not getattr(sys, "frozen", False):
        return
    exe_path = str(Path(sys.executable).resolve())
    cwd = str(Path.cwd())
    if _has_non_ascii(exe_path) or _has_non_ascii(cwd):
        warn = "WARNING: non-ascii path detected in frozen mode; prefer C:\\Antoshka\\ for onefile"
        report.append(warn)
        log.warning(warn)


def _run_cases_with_router(started_at: float) -> tuple[object, int]:
    from core.app_context import AppContext
    from core.router import CommandRouter
    from services.scheduler import Scheduler

    ctx = AppContext(
        notify=lambda _: None,
        data_dir=data_dir(),
        scheduler=Scheduler(notify=lambda _: None),
        volume=None,
        llm_client=None,
    )
    router = CommandRouter(ctx)
    cases = [
        ("privet", "greet", "ru"),
        ("pomoshch", "help", "ru"),
        ("komandy", "help", "ru"),
        ("kotoryy chas", "time", "ru"),
        ("kakaya data", "date", "ru"),
        ("otkroy sait vk", "open_url", "ru"),
        ("naydi v internete kotikov", "search_web", "ru"),
        ("otkroy kartu", "open_map", "ru"),
        ("otkroy papku zagruzki", "open_path", "ru"),
        ("otkroy prilozhenie kalkulyator", "open_app", "ru"),
        ("sozdai zametku kupit moloko", "note_create", "ru"),
        ("pokazhi zametki", "note_list", "ru"),
        ("udali zametku 1", "note_delete", "ru"),
        ("postav timer na 5 minut", "timer_set", "ru"),
        ("postav budilnik na 07:30", "alarm_set", "ru"),
        ("napomni kupit hleb cherez 10 minut", "reminder_set", "ru"),
        ("pogoda v moskve", "weather", "ru"),
        ("sozdai sobytie vstrecha na 10.02.2026 15:30", "event_add", "ru"),
        ("pokazhi sobytiya", "event_list", "ru"),
        ("ochisti chat", "clear_chat", "ru"),
        ("vyhod", "exit", "ru"),
        ("hello", "greet", "en"),
        ("help", "help", "en"),
        ("what time is it", "time", "en"),
        ("what date is it", "date", "en"),
        ("open youtube", "open_url", "en"),
        ("open mail", "open_mail", "en"),
        ("open calendar", "open_calendar", "en"),
        ("open folder", "open_path", "en"),
        ("open file", "open_path", "en"),
        ("set a timer for 10 minutes", "timer_set", "en"),
        ("set an alarm for 07:30", "alarm_set", "en"),
        ("remind me in 20 minutes", "reminder_set", "en"),
        ("pogoda", "weather", "en"),
        ("exit", "exit", "en"),
    ]
    for text, expected, lang in cases:
        _deadline_guard(started_at, "router_cases")
        res = router.route(text, lang=lang)
        if not res:
            raise SelfTestFailure(f"router no match: {text}")
        if res.name != expected:
            raise SelfTestFailure(f"router mismatch: {text} -> {res.name}, expected {expected}")
    return router.registry, len(cases)


def _check_time_parse(started_at: float) -> None:
    from services.time_parse import parse_duration_seconds

    cases = [("5 sec", 5), ("10s", 10), ("2 min", 120), ("1h20min", 4800), ("cherez 2 minuty", 120)]
    for text, expected in cases:
        _deadline_guard(started_at, "time_parse")
        got = parse_duration_seconds(text)
        if got != expected:
            raise SelfTestFailure(f"time_parse mismatch: {text} -> {got}, expected {expected}")


def _check_suggestions(started_at: float, registry: object) -> None:
    from core.suggestions import pick_suggestions

    for lang in ("ru", "en"):
        _deadline_guard(started_at, "suggestions")
        picked = pick_suggestions(registry, lang, "default", k=5)
        if len(picked) != 5:
            raise SelfTestFailure(f"suggestions count={len(picked)} lang={lang}")
        all_examples = set(registry.get_all_examples(lang))
        if not all(item in all_examples for item in picked):
            raise SelfTestFailure(f"suggestions out-of-registry lang={lang}")


def _check_i18n_keys(started_at: float) -> None:
    from core.i18n import _UI, t

    for key in _UI.keys():
        _deadline_guard(started_at, "i18n_keys")
        if not (key.startswith("btn_") or key.startswith("msg_") or key.startswith("label_")):
            continue
        ru = t(key, "ru")
        en = t(key, "en")
        if ru == key or en == key:
            raise SelfTestFailure(f"raw i18n key leaked: {key}")


def _check_resources(started_at: float) -> None:
    required_dirs = ("config", "assets", "data", "img", "Music")
    for rel in required_dirs:
        _deadline_guard(started_at, "resources")
        p = resource_path(rel)
        if not p.exists():
            raise SelfTestFailure(f"resource missing: {rel} ({p})")
        if not p.is_dir():
            raise SelfTestFailure(f"resource is not dir: {rel} ({p})")

    model = resource_path("models/vosk")
    if not model.exists():
        raise SelfTestFailure(f"model path missing: {model}")
    if model.is_file():
        return
    try:
        has_entries = any(model.iterdir())
    except Exception as e:
        raise SelfTestFailure(f"model check failed: {model}: {e}") from e
    if not has_entries:
        raise SelfTestFailure(f"model path is empty: {model}")


def _check_imports(started_at: float) -> None:
    modules = [
        "core.app_context",
        "core.router",
        "commands.registry",
        "commands.builtins",
        "services.time_parse",
        "core.suggestions",
        "core.i18n",
        "core.text_norm",
        "core.resources",
    ]
    for mod in modules:
        _deadline_guard(started_at, "imports")
        importlib.import_module(mod)


def _self_test_impl() -> int:
    started_at = time.perf_counter()
    log = _safe_logger()
    report: list[str] = []
    report.append("SELF-TEST REPORT")
    report.append(f"python={sys.version.split()[0]}")
    report.append(f"frozen={getattr(sys, 'frozen', False)}")
    report.append(f"cwd={Path.cwd()}")
    report.append(f"executable={Path(sys.executable).resolve()}")
    _append_frozen_path_warning(log, report)
    try:
        _check_imports(started_at)
        report.append("imports: OK")
        registry, count = _run_cases_with_router(started_at)
        report.append(f"router: OK ({count} cases)")
        _check_time_parse(started_at)
        report.append("time_parse: OK")
        _check_suggestions(started_at, registry)
        report.append("suggestions: OK")
        _check_i18n_keys(started_at)
        report.append("i18n: OK")
        _check_resources(started_at)
        report.append("resources: OK")
        elapsed = time.perf_counter() - started_at
        report.append(f"elapsed_sec={elapsed:.3f}")
        path = _write_report(report)
        if path:
            report.append(f"report_path={path}")
        log.info("SELF-TEST OK elapsed=%.3fs", elapsed)
        print("SELF-TEST OK")
        return 0
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - started_at
        reason = str(e).strip() or e.__class__.__name__
        report.append(f"error={reason}")
        report.append(f"elapsed_sec={elapsed:.3f}")
        report.append("traceback:")
        report.extend(traceback.format_exc().splitlines())
        path = _write_report(report)
        if path:
            log.error("SELF-TEST FAIL: %s (report=%s)", reason, path)
        else:
            log.error("SELF-TEST FAIL: %s", reason)
        print(f"SELF-TEST FAIL: {reason}")
        return 1


def _smoke_impl() -> int:
    started_at = time.perf_counter()
    log = _safe_logger()
    report = ["SMOKE REPORT"]
    report.append(f"frozen={getattr(sys, 'frozen', False)}")
    _append_frozen_path_warning(log, report)
    try:
        from core.app_context import AppContext
        from core.config import load_settings
        from core.dialogue import Dialogue, DialogueConfig
        from core.i18n import help_sections
        from core.router import CommandRouter
        from core.suggestions import pick_suggestions
        from services.scheduler import Scheduler

        settings = load_settings()
        _deadline_guard(started_at, "smoke_settings")
        hs = help_sections(settings.get("app", {}).get("language", "ru"))
        report.append(f"help_sections={len(hs)}")

        app_ctx = AppContext(
            notify=lambda _: None,
            data_dir=data_dir(),
            scheduler=Scheduler(notify=lambda _: None),
            volume=None,
        )
        dlg = Dialogue(DialogueConfig(app_context=app_ctx))
        out = dlg.handle_text("pomoshch", language="ru", allow_llm=False)
        if not out:
            raise SelfTestFailure("dialogue empty output")
        report.append("dialogue=OK")

        router = CommandRouter(app_ctx)
        cases = [
            ("privet", "greet", "ru"),
            ("pomoshch", "help", "ru"),
            ("kotoryy chas", "time", "ru"),
            ("open youtube", "open_url", "en"),
            ("open calendar", "open_calendar", "en"),
            ("set a timer for 10 minutes", "timer_set", "en"),
            ("exit", "exit", "en"),
        ]
        for text, expected, lang in cases:
            _deadline_guard(started_at, "smoke_router")
            res = router.route(text, lang=lang)
            if not res or res.name != expected:
                raise SelfTestFailure(f"smoke route mismatch: {text} -> {getattr(res, 'name', None)}")
        report.append(f"router=OK ({len(cases)} cases)")

        for lang in ("ru", "en"):
            _deadline_guard(started_at, "smoke_suggestions")
            picked = pick_suggestions(router.registry, lang, "default", k=5)
            if len(picked) != 5:
                raise SelfTestFailure(f"smoke suggestions count={len(picked)} lang={lang}")
        report.append("suggestions=OK")

        elapsed = time.perf_counter() - started_at
        report.append(f"elapsed_sec={elapsed:.3f}")
        path = _write_report(report)
        if path:
            report.append(f"report_path={path}")
        log.info("SMOKE OK elapsed=%.3fs", elapsed)
        print("SMOKE OK")
        return 0
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - started_at
        reason = str(e).strip() or e.__class__.__name__
        report.append(f"error={reason}")
        report.append(f"elapsed_sec={elapsed:.3f}")
        report.append("traceback:")
        report.extend(traceback.format_exc().splitlines())
        path = _write_report(report)
        if path:
            log.error("SMOKE FAIL: %s (report=%s)", reason, path)
        else:
            log.error("SMOKE FAIL: %s", reason)
        print(f"SMOKE FAIL: {reason}")
        return 1


def _run_with_watchdog(fn: Callable[[], int], label: str, timeout: float = WATCHDOG_SECONDS) -> int:
    result: dict[str, int] = {"code": 1}
    error: dict[str, str] = {}

    def _worker() -> None:
        try:
            result["code"] = int(fn())
        except Exception as e:  # noqa: BLE001
            error["msg"] = str(e) or e.__class__.__name__
            result["code"] = 1

    t = threading.Thread(target=_worker, name=f"{label}-worker", daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        msg = f"watchdog timeout > {int(timeout)}s"
        _write_report([f"{label.upper()} REPORT", f"error={msg}"])
        print(f"{label.upper()} FAIL: {msg}")
        return 1
    if error:
        print(f"{label.upper()} FAIL: {error['msg']}")
        return 1
    return int(result["code"])


def run_self_test() -> int:
    return _run_with_watchdog(_self_test_impl, "self-test", timeout=WATCHDOG_SECONDS)


def run_smoke() -> int:
    return _run_with_watchdog(_smoke_impl, "smoke", timeout=WATCHDOG_SECONDS)
