from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from core.logger import setup_logger

try:
    import sounddevice as sd
except Exception:  # noqa: BLE001
    sd = None


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    max_input_channels: int
    default_samplerate: float


def list_input_devices() -> List[InputDevice]:
    if sd is None:
        return []
    devices = []
    for idx, info in enumerate(sd.query_devices()):
        if info.get("max_input_channels", 0) > 0:
            devices.append(
                InputDevice(
                    index=idx,
                    name=str(info.get("name", f"Device {idx}")),
                    max_input_channels=int(info.get("max_input_channels", 0)),
                    default_samplerate=float(info.get("default_samplerate", 16000.0)),
                )
            )
    return devices


class MicLevelMonitor:
    def __init__(self, device: Optional[int] = None, samplerate: int = 16000):
        self.logger = setup_logger()
        self.device = device
        self.samplerate = samplerate
        self._level = 0.0
        self._lock = threading.Lock()
        self._stream = None
        self._last_error: Optional[str] = None
        self._log_once = False
        self._last_restart = 0.0
        self._effective_samplerate = samplerate
        self._invalid_device = False

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def start(self) -> None:
        if sd is None:
            self._last_error = "sounddevice_not_installed"
            return
        if self._stream is not None:
            return
        self._invalid_device = False

        dtype = "int16"
        channels = 1
        self.device = _validate_input_device(self.device, self.logger)
        if self.device is None:
            self._invalid_device = True
        self._effective_samplerate = _resolve_samplerate(self.device, self.samplerate)

        def callback(indata, frames, time_info, status):
            try:
                if status:
                    self._last_error = str(status)
                if not self._log_once:
                    self._log_once = True
                    self.logger.info(
                        "Mic callback: type=%s dtype=%s channels=%s frames=%s device=%s",
                        type(indata),
                        dtype,
                        channels,
                        frames,
                        self.device,
                    )
                if dtype == "int16":
                    data = np.frombuffer(indata, dtype=np.int16)
                    if channels > 1:
                        data = data.reshape(-1, channels).mean(axis=1)
                    samples = data.astype(np.float32) / 32768.0
                else:
                    data = np.frombuffer(indata, dtype=np.float32)
                    if channels > 1:
                        data = data.reshape(-1, channels).mean(axis=1)
                    samples = data
                rms = float(np.sqrt(np.mean(samples * samples) + 1e-12))
                with self._lock:
                    self._level = rms
            except Exception as e:  # noqa: BLE001
                self._last_error = str(e)
                self.logger.exception("Mic callback error: %s", e)

        try:
            self.logger.info("MicLevelMonitor start: device=%s", self.device)
            self._stream = sd.RawInputStream(
                samplerate=self._effective_samplerate,
                blocksize=1024,
                dtype=dtype,
                channels=channels,
                callback=callback,
                device=self.device,
            )
            self._stream.start()
        except Exception as e:  # noqa: BLE001
            self._last_error = str(e)
            self.logger.exception("MicLevelMonitor start failed: %s", e)
            self._stream = None
            if "Invalid device" in str(e):
                # Fallback to default device once
                self.logger.warning("Invalid device %s. Falling back to default.", self.device)
                self.device = None
                self._invalid_device = False
                self._effective_samplerate = _resolve_samplerate(self.device, self.samplerate)
                try:
                    self._stream = sd.RawInputStream(
                        samplerate=self._effective_samplerate,
                        blocksize=1024,
                        dtype=dtype,
                        channels=channels,
                        callback=callback,
                        device=self.device,
                    )
                    self._stream.start()
                    self.logger.info("MicLevelMonitor fallback started with default device")
                    return
                except Exception as e2:  # noqa: BLE001
                    self._last_error = str(e2)
                    self.logger.exception("MicLevelMonitor fallback failed: %s", e2)
                    self._stream = None
                    self._invalid_device = True

    def stop(self) -> None:
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception as e:  # noqa: BLE001
            self.logger.exception("MicLevelMonitor stop failed: %s", e)
        finally:
            self._stream = None

    def is_active(self) -> bool:
        return bool(self._stream is not None and getattr(self._stream, "active", False))

    def restart_if_inactive(self) -> None:
        now = time.monotonic()
        if self.is_active():
            return
        if self._invalid_device:
            return
        if self._last_error and "Invalid device" in str(self._last_error):
            self._invalid_device = True
            return
        if now - self._last_restart < 1.0:
            return
        self._last_restart = now
        self.logger.warning("Mic stream inactive, restarting")
        self.stop()
        self.start()

    def get_level(self) -> float:
        with self._lock:
            return float(self._level)


def test_microphone(
    device: Optional[int] = None, duration_seconds: float = 2.5, samplerate: int = 16000
) -> tuple[bool, float, Optional[str]]:
    logger = setup_logger()
    if sd is None:
        return False, 0.0, "sounddevice_not_installed"
    device = _validate_input_device(device, logger)
    level = 0.0
    last_error = None
    log_once = False
    dtype = "int16"
    channels = 1
    effective_samplerate = _resolve_samplerate(device, samplerate)

    def callback(indata, frames, time_info, status):
        nonlocal level, last_error, log_once
        try:
            if status:
                last_error = str(status)
            if not log_once:
                log_once = True
                logger.info(
                    "Mic test callback: type=%s dtype=%s channels=%s frames=%s device=%s",
                    type(indata),
                    dtype,
                    channels,
                    frames,
                    device,
                )
            if dtype == "int16":
                data = np.frombuffer(indata, dtype=np.int16)
                if channels > 1:
                    data = data.reshape(-1, channels).mean(axis=1)
                samples = data.astype(np.float32) / 32768.0
            else:
                data = np.frombuffer(indata, dtype=np.float32)
                if channels > 1:
                    data = data.reshape(-1, channels).mean(axis=1)
                samples = data
            rms = float(np.sqrt(np.mean(samples * samples) + 1e-12))
            level = max(level, rms)
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            logger.exception("Mic test callback error: %s", e)

    try:
        with sd.RawInputStream(
            samplerate=effective_samplerate,
            blocksize=1024,
            dtype=dtype,
            channels=channels,
            callback=callback,
            device=device,
        ):
            time.sleep(duration_seconds)
    except Exception as e:  # noqa: BLE001
        logger.exception("Mic test failed: %s", e)
        return False, level, str(e)

    ok = level >= 0.01
    logger.info("Mic test result: %s (level=%.4f)", "ok" if ok else "error", level)
    return ok, level, last_error


def _resolve_samplerate(device: Optional[int], requested: int) -> int:
    if sd is None:
        return requested
    try:
        if device is None:
            return requested
        info = sd.query_devices(device, "input")
        default_rate = int(float(info.get("default_samplerate", requested)))
        try:
            sd.check_input_settings(device=device, channels=1, dtype="int16", samplerate=requested)
            return requested
        except Exception:
            return default_rate
    except Exception:
        return requested


def _validate_input_device(device: Optional[int], logger) -> Optional[int]:
    if sd is None:
        return None
    if device is None:
        return None
    try:
        info = sd.query_devices(device, "input")
        if int(info.get("max_input_channels", 0)) <= 0:
            logger.warning("Invalid input device (no input channels): %s", device)
            return None
        return device
    except Exception as e:  # noqa: BLE001
        logger.warning("Invalid input device: %s (%s)", device, e)
        return None
