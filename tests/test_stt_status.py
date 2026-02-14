from __future__ import annotations

from pathlib import Path

from core.stt import get_stt_status, validate_vosk_model_dir


def _base_settings(mode: str = "vosk") -> dict:
    return {
        "app": {"language": "ru"},
        "stt": {"mode": mode, "language": "ru", "vosk_model_path": ""},
    }


def test_validate_vosk_model_dir_requires_conf_and_structure(tmp_path: Path) -> None:
    model_dir = tmp_path / "vosk-model-small-ru"
    model_dir.mkdir()
    (model_dir / "conf").mkdir()
    assert not validate_vosk_model_dir(model_dir)
    (model_dir / "graph").mkdir()
    assert validate_vosk_model_dir(model_dir)


def test_get_stt_status_detects_configured_model(tmp_path: Path) -> None:
    model_dir = tmp_path / "my-model"
    model_dir.mkdir()
    (model_dir / "conf").mkdir()
    (model_dir / "graph").mkdir()
    settings = _base_settings("vosk")
    settings["stt"]["vosk_model_path"] = str(model_dir)
    status = get_stt_status(settings)
    assert status.available is True
    assert status.code == "ready"
    assert status.resolved_model_path == model_dir


def test_get_stt_status_missing_model(tmp_path: Path, monkeypatch) -> None:
    import core.stt as stt_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(stt_module, "resource_path", lambda rel: (tmp_path / rel))
    settings = _base_settings("vosk")
    status = get_stt_status(settings)
    assert status.available is False
    assert status.code == "missing_model"
