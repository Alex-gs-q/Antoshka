from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from core.resources import resource_path
from core.logger import setup_logger


@dataclass(frozen=True)
class AlertSound:
    label: str
    path: Path
    rel: str


def list_alert_sounds() -> List[AlertSound]:
    return _list_default_sounds()


def _list_default_sounds() -> List[AlertSound]:
    candidates = [
        Path("Music") / "Kioko - The Phantom Traveler.mp3",
        Path("Music") / "Pyotr Ilyich Tchaikovsky - The Nutcracker Suite, Op. 71a. III. Waltz of the Flowers.mp3",
    ]
    sounds: List[AlertSound] = []
    for rel in candidates:
        path = resource_path(rel)
        if path.exists():
            sounds.append(AlertSound(label=rel.stem, path=path, rel=str(rel)))
    return sounds


def list_all_alert_sounds(settings: dict | None) -> List[AlertSound]:
    sounds = _list_default_sounds()
    ui = (settings or {}).get("ui", {}) or {}
    custom = ui.get("alerts_custom_sounds", [])
    if isinstance(custom, list):
        for item in custom:
            if isinstance(item, str):
                path = Path(item)
                label = path.stem
            elif isinstance(item, dict):
                path = Path(str(item.get("path") or ""))
                label = str(item.get("name") or path.stem or "custom")
            else:
                continue
            if not str(path):
                continue
            sounds.append(AlertSound(label=label, path=path, rel=str(path)))
    return sounds


class AlertSoundPlayer(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.log = setup_logger()
        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)

    def play(self, path: Path, volume: int = 80) -> None:
        self._audio.setVolume(max(0, min(100, int(volume))) / 100.0)
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        try:
            self._player.setLoops(QMediaPlayer.Infinite)
        except Exception as e:  # noqa: BLE001
            self.log.exception("AlertSound setLoops failed: %s", e)
        self._player.play()

    def stop(self) -> None:
        self._player.stop()
