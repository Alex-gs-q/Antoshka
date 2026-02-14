from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

pytest.importorskip("pytestqt")

from config.settings import DEFAULT_SETTINGS
from ui.qt_app import AntoshkaWindow


class _DummyTTSWorker:
    def __init__(self) -> None:
        self._volume = 1.0

    def update_settings(self, _settings: dict) -> None:
        return

    def is_available(self) -> bool:
        return False

    def say(self, _text: str, lang: str = "ru") -> None:
        return

    def get_volume(self) -> float:
        return self._volume

    def set_volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, float(value)))

    def set_mute(self, _flag: bool) -> None:
        return


class _DummyAudioAlerts:
    def __init__(self, _parent) -> None:
        return

    def stop(self) -> None:
        return

    def play(self, _path: str, _loop: bool = False, _volume: int = 80) -> bool:
        return True


@pytest.fixture
def qt_window(qtbot, monkeypatch, tmp_path: Path) -> AntoshkaWindow:
    settings = deepcopy(DEFAULT_SETTINGS)
    settings.setdefault("app", {})["language"] = "ru"
    settings.setdefault("stt", {})["mode"] = "vosk"
    settings.setdefault("stt", {})["language"] = "ru"
    settings.setdefault("stt", {})["vosk_model_path"] = str(tmp_path / "missing-model")
    settings.setdefault("ui", {})["show_start_screen"] = False
    settings.setdefault("ui", {})["wake_word"] = False
    settings.setdefault("ui", {})["ai_mode"] = False
    settings.setdefault("ui", {})["ai_mode_autostart"] = False

    monkeypatch.setattr("ui.qt_app.load_settings", lambda: deepcopy(settings))
    monkeypatch.setattr("ui.qt_app.save_settings", lambda _settings: None)
    monkeypatch.setattr("ui.qt_app.AudioAlerts", _DummyAudioAlerts)
    monkeypatch.setattr("ui.qt_app.AntoshkaWindow._init_tts", lambda self: setattr(self, "tts_worker", _DummyTTSWorker()))
    def _fake_init_llm(self) -> None:
        self.llm_client = None
        self.llm_error = None

    monkeypatch.setattr("ui.qt_app.AntoshkaWindow._init_llm", _fake_init_llm)
    monkeypatch.setattr("ui.qt_app.AntoshkaWindow._init_tray_and_notifications", lambda self: None)
    monkeypatch.setattr("ui.qt_app.AntoshkaWindow._init_wake_word", lambda self: None)
    monkeypatch.setattr("ui.qt_app.AntoshkaWindow._say_startup", lambda self: None)

    window = AntoshkaWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def _make_valid_model(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "conf").mkdir(exist_ok=True)
    (path / "graph").mkdir(exist_ok=True)


def test_listen_disabled_when_vosk_missing(qt_window: AntoshkaWindow) -> None:
    assert qt_window._stt_available is False
    assert qt_window.listen_btn.isEnabled() is False
    assert qt_window.status_banner.isVisible() is True
    assert "Vosk" in qt_window.listen_btn.toolTip()
    assert "msg_" not in qt_window.listen_btn.toolTip()


def test_stt_banner_is_not_duplicated(qt_window: AntoshkaWindow) -> None:
    qt_window._report_stt_status()
    qt_window._report_stt_status()
    assert "stt_missing_model" in qt_window._active_banners
    assert len([k for k in qt_window._active_banners.keys() if k == "stt_missing_model"]) == 1
    assert qt_window._pending_notices == []


def test_listen_becomes_enabled_after_valid_model_path(qt_window: AntoshkaWindow, tmp_path: Path) -> None:
    model_dir = tmp_path / "vosk-model-small-ru"
    _make_valid_model(model_dir)
    updated = deepcopy(qt_window.settings)
    updated.setdefault("stt", {})["vosk_model_path"] = str(model_dir)
    updated.setdefault("stt", {})["mode"] = "vosk"
    qt_window._on_settings_changed(updated)
    assert qt_window._stt_available is True
    assert qt_window.listen_btn.isEnabled() is True
    assert qt_window.status_banner.isVisible() is False


def test_toggle_listen_uses_guard_dialog_when_stt_unavailable(qt_window: AntoshkaWindow, monkeypatch) -> None:
    called = {"count": 0}
    monkeypatch.setattr(qt_window, "_show_vosk_required_dialog", lambda: called.__setitem__("count", called["count"] + 1))
    qt_window._toggle_listen()
    assert called["count"] == 1
