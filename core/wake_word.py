from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from core.logger import setup_logger


@dataclass
class WakeWordConfig:
    model_path: str = "models/vosk"
    samplerate: int = 16000
    device: Optional[int] = None
    wake_phrases: tuple[str, ...] = ("антошка откройся", "антошка, откройся")
    rms_threshold: float = 0.005


class WakeWordListener:
    def __init__(self, config: WakeWordConfig, on_wake: Callable[[str], None]):
        self.log = setup_logger()
        self.config = config
        self.on_wake = on_wake
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._model = None
        self._KaldiRecognizer = None

        try:
            from vosk import KaldiRecognizer, Model  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Vosk unavailable: {e}") from e

        self._KaldiRecognizer = KaldiRecognizer

        mp = Path(config.model_path)
        if not mp.exists():
            raise FileNotFoundError(f"Vosk model not found at {mp}")
        self._model = Model(str(mp))
        self.log.info("Wake word model loaded: %s", mp)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        if self._model is None or self._KaldiRecognizer is None:
            return
        grammar = json.dumps(list(self.config.wake_phrases), ensure_ascii=False)
        rec = self._KaldiRecognizer(self._model, self.config.samplerate, grammar)
        rec.SetWords(True)

        def callback(indata, frames, time_info, status):
            if status:
                self.log.warning("wake word sounddevice status: %s", status)
            if self._stop.is_set():
                raise sd.CallbackStop()
            samples = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(samples * samples) + 1e-12))
            if rms < self.config.rms_threshold:
                return
            if rec.AcceptWaveform(bytes(indata)):
                result = json.loads(rec.Result())
                text = (result.get("text") or "").strip().lower()
                if text:
                    for phrase in self.config.wake_phrases:
                        if phrase in text:
                            self.on_wake(text)
                            rec.Reset()
                            break

        try:
            with sd.RawInputStream(
                samplerate=self.config.samplerate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback,
                device=self.config.device,
            ):
                self.log.info("Wake word listening started")
                while not self._stop.is_set():
                    time.sleep(0.1)
        except Exception as e:  # noqa: BLE001
            self.log.error("Wake word listener stopped: %s", e)
