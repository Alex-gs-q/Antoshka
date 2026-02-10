from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from core.resources import resource_path


@dataclass(frozen=True)
class AlertSound:
    label: str
    path: Path
    rel: str


def list_alert_sounds() -> List[AlertSound]:
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


class AlertSoundPlayer(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)

    def play(self, path: Path, volume: int = 80) -> None:
        self._audio.setVolume(max(0, min(100, int(volume))) / 100.0)
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        try:
            self._player.setLoops(QMediaPlayer.Infinite)
        except Exception:
            pass
        self._player.play()

    def stop(self) -> None:
        self._player.stop()
