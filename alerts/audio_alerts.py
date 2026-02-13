from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from core.logger import setup_logger

class AudioAlerts(QObject):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.log = setup_logger()
        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)
        self._loop = False

    def set_volume(self, volume: int) -> None:
        vol = max(0, min(100, int(volume))) / 100.0
        self._audio.setVolume(vol)

    def play(self, sound_path: Path, loop: bool = False) -> None:
        self._loop = bool(loop)
        self._player.setSource(QUrl.fromLocalFile(str(sound_path)))
        try:
            self._player.setLoops(QMediaPlayer.Infinite if loop else 1)
        except Exception as e:  # noqa: BLE001
            self.log.exception("Alert setLoops failed: %s", e)
        self._player.play()

    def stop(self) -> None:
        self._player.stop()
