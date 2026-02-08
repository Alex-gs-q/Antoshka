from __future__ import annotations

import json
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer, Model

from core.logger import setup_logger


@dataclass
class VoskConfig:
    model_path: str = "models/vosk"
    samplerate: int = 16000
    device: Optional[int] = None
    max_listen_seconds: int = 8
    silence_rms_threshold: float = 0.008  # tweak if needed
    silence_seconds_to_stop: float = 1.0


class VoskSTT:
    def __init__(self, config: VoskConfig):
        self.logger = setup_logger()
        self.config = config
        self._logged_listen = False

        mp = Path(config.model_path)
        if not mp.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {mp}. Run: .\\.venv\\Scripts\\python.exe tools\\download_vosk_model.py"
            )

        self.model = Model(str(mp))
        self.logger.info("Vosk STT initialized, model=%s", mp)

    @staticmethod
    def _safe_queue_get(q: "queue.Queue[bytes]", timeout: float) -> Optional[bytes]:
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    def listen(self) -> Optional[str]:
        """
        Records from microphone until silence or timeout.
        Return:
          - None on interrupt
          - "" if nothing recognized
          - text if recognized
        """
        q: "queue.Queue[bytes]" = queue.Queue()
        started = time.time()
        last_voice_time = time.time()

        rec = KaldiRecognizer(self.model, self.config.samplerate)
        rec.SetWords(True)

        def callback(indata, frames, time_info, status):
            if status:
                self.logger.warning("sounddevice status: %s", status)
            q.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=self.config.samplerate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback,
                device=self.config.device,
            ):
                if not self._logged_listen:
                    self.logger.info("Vosk listening... (speak now)")
                    self._logged_listen = True
                while True:
                    if time.time() - started > self.config.max_listen_seconds:
                        break

                    data = self._safe_queue_get(q, timeout=1)
                    if data is None:
                        continue
                    # compute RMS for silence detection
                    samples = (
                        np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    )
                    rms = float(np.sqrt(np.mean(samples * samples) + 1e-12))
                    if rms > self.config.silence_rms_threshold:
                        last_voice_time = time.time()

                    rec.AcceptWaveform(data)

                    if (
                        time.time() - last_voice_time
                        > self.config.silence_seconds_to_stop
                    ):
                        break

        except (KeyboardInterrupt, EOFError):
            return None

        try:
            result = json.loads(rec.FinalResult())
            text = (result.get("text") or "").strip()
        except Exception:
            text = ""

        return text
