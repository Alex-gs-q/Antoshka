from __future__ import annotations

import math
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPoint, QSize, QTimer, QUrl
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.actions import ActionResult
from core.app_context import AppContext
from core.config import load_settings, save_settings
from core.dialogue import Dialogue, DialogueConfig
from core.logger import setup_logger
from core.resources import resource_path
from core.stt import TextSTT, create_stt
from core.tts import TTS, TTSConfig
from core.wake_word import WakeWordListener, WakeWordConfig
from llm.client import LLMClient, LLMConfig
from services.chat_history import append_chat
from services.scheduler import Scheduler
from services.storage import read_json
from services.volume import VolumeController


@dataclass(frozen=True)
class IconSet:
    mic: str = "btn_mic_48.png"
    mic_active: str = "btn_mic_active_48.png"
    stop: str = "btn_stop_48.png"
    stop_active: str = "btn_stop_active_48.png"
    history: str = "btn_history_48.png"
    history_active: str = "btn_history_active_48.png"
    volume: str = "btn_volume_48.png"
    volume_active: str = "btn_volume_active_48.png"
    ai: str = "btn_ai_48.png"
    ai_active: str = "btn_ai_active_48.png"
    settings: str = "btn_settings_48.png"
    settings_active: str = "btn_settings_active_48.png"
    app_icon: str = "app_icon_v3_256.png"


class GradientBackground(QWidget):
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#0b0f18"))
        grad.setColorAt(1.0, QColor("#111827"))
        painter.fillRect(self.rect(), grad)


class IconButton(QPushButton):
    def __init__(self, icon_off: QIcon, icon_on: Optional[QIcon] = None, text: str = ""):
        super().__init__(text)
        self._icon_off = icon_off
        self._icon_on = icon_on or icon_off
        self._active = False
        self.setIcon(self._icon_off)
        self.setIconSize(QSize(48, 48))
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(False)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setIcon(self._icon_on if active else self._icon_off)

    def is_active(self) -> bool:
        return self._active


class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool, action_widget: QWidget | None = None):
        super().__init__()
        self.setObjectName("ChatBubble")
        self._is_user = is_user
        self._wave_phase = 0.0
        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(40)
        self._wave_timer.timeout.connect(self._tick_wave)
        self._wave_active = False
        self._emphasis = 0.4

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setObjectName("BubbleText")
        layout.addWidget(label)
        if action_widget is not None:
            layout.addWidget(action_widget)
        if is_user:
            self.setProperty("kind", "user")
        else:
            self.setProperty("kind", "bot")

    def set_wave_active(self, active: bool) -> None:
        if self._is_user:
            return
        self._wave_active = active
        if active:
            self.set_emphasis(1.0)
            if not self._wave_timer.isActive():
                self._wave_timer.start()
        else:
            self._wave_timer.stop()
            self.set_emphasis(0.4)
            self.update()

    def set_emphasis(self, level: float) -> None:
        self._emphasis = max(0.2, min(1.0, float(level)))
        self.update()

    def _tick_wave(self) -> None:
        self._wave_phase += 0.12
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._is_user:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        pen = painter.pen()
        pen.setWidthF(1.6 + 1.2 * self._emphasis)
        pen.setColor(QColor(120, 190, 255, int(160 * self._emphasis)))
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 14, 14)

        if not self._wave_active:
            return
        h = rect.height()
        base_y = rect.top() + h * 0.65
        for idx, amp in enumerate([6, 4.5, 3]):
            path = []
            for x in range(int(rect.left()), int(rect.right()), 6):
                phase = self._wave_phase + idx * 1.3
                y = base_y + (idx * 6) + amp * (0.5 + 0.5 * math.sin((x - rect.left()) * 0.04 + phase))
                path.append(QPoint(x, int(y)))
            color = QColor(120, 180, 255, 70 - idx * 10)
            painter.setPen(color)
            for i in range(1, len(path)):
                painter.drawLine(path[i - 1], path[i])


class ActionCard(QFrame):
    def __init__(self, title: str, details: str = "", status: str = "ok", url: str | None = None):
        super().__init__()
        self.setObjectName("ActionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("ActionTitle")
        layout.addWidget(title_lbl)

        if details:
            details_lbl = QLabel(details)
            details_lbl.setObjectName("ActionDetails")
            details_lbl.setWordWrap(True)
            layout.addWidget(details_lbl)

        if url:
            link = QLabel(f"<a href=\"{url}\">{url}</a>")
            link.setOpenExternalLinks(False)
            link.linkActivated.connect(lambda u: QDesktopServices.openUrl(QUrl(u)))
            link.setObjectName("ActionLink")
            layout.addWidget(link)

        status_lbl = QLabel(status.upper())
        status_lbl.setObjectName("ActionStatus")
        layout.addWidget(status_lbl)


class AntoshkaWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.log = setup_logger()
        self.settings = load_settings()
        self.icons = IconSet()
        self._first_message = True
        self._tts_warned = False
        self.listening = False
        self.ai_mode = bool(self.settings.get("ui", {}).get("ai_mode", False))
        self._last_status = ""

        self._init_tts()
        self._init_llm()
        self._init_stt()
        self._init_context()
        self._init_ui()
        self._init_wake_word()
        self._apply_stt_mode_ui()
        self._sync_ai_button()
        self._say_startup()

    def _init_tts(self) -> None:
        tts_raw = self.settings.get("tts", {}) or {}
        self.tts = TTS(
            TTSConfig(
                enabled=bool(tts_raw.get("enabled", True)),
                provider=str(tts_raw.get("provider", "auto")),
                rate=int(tts_raw.get("rate", 180)),
                volume=float(tts_raw.get("volume", 1.0)),
                voice=str(tts_raw.get("voice", "ru-RU-DmitryNeural")),
                pitch=int(tts_raw.get("pitch", 0)),
                voice_name_contains=tts_raw.get("voice_name_contains"),
            )
        )

    def _init_llm(self) -> None:
        llm_raw = self.settings.get("llm", {}) or {}
        try:
            self.llm_client = LLMClient(
                LLMConfig(
                    provider=str(llm_raw.get("provider", "dummy")),
                    model=str(llm_raw.get("model", "gpt-4o-mini")),
                    history_max_messages=int(llm_raw.get("history_max_messages", 10)),
                )
            )
            self.llm_error = None
        except Exception as e:  # noqa: BLE001
            self.log.warning("LLM disabled: %s", e)
            self.llm_client = None
            self.llm_error = str(e)

    def _init_stt(self) -> None:
        self.stt = create_stt(self.settings)

    def _init_context(self) -> None:
        self.scheduler = Scheduler(notify=self._notify)
        volume = None
        if self.tts.engine is not None:
            volume = VolumeController(
                get_level=self.tts.get_volume,
                set_level=self.tts.set_volume,
                set_mute_fn=self.tts.set_mute,
            )
        self.app_context = AppContext(
            notify=self._notify,
            data_dir=Path("data"),
            scheduler=self.scheduler,
            volume=volume,
            llm_client=self.llm_client,
            on_settings_changed=self._on_settings_changed,
        )
        self.dialogue = Dialogue(
            DialogueConfig(
                dangerous_mode=bool(self.settings.get("safety", {}).get("dangerous_mode", False)),
                llm_client=self.llm_client,
                app_context=self.app_context,
            )
        )

    def _on_settings_changed(self, settings: dict) -> None:
        self.settings = settings
        self._init_tts()
        self._init_stt()
        self._init_context()
        self._init_wake_word()
        self._apply_stt_mode_ui()
        self._apply_styles()

    def _init_ui(self) -> None:
        self.setWindowTitle("Antoshka")
        self.setMinimumSize(820, 520)
        app_icon = resource_path(Path("assets") / "icons" / self.icons.app_icon)
        if app_icon.exists():
            self.setWindowIcon(QIcon(str(app_icon)))

        root = GradientBackground()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        self._build_topbar(root_layout)
        self._build_chat(root_layout)
        self._build_input(root_layout)
        self._build_actions(root_layout)
        self._apply_styles()

    def _build_topbar(self, root_layout: QVBoxLayout) -> None:
        top = QHBoxLayout()
        icon_label = QLabel()
        icon_path = resource_path(Path("assets") / "icons" / self.icons.app_icon)
        if icon_path.exists():
            icon_label.setPixmap(QPixmap(str(icon_path)).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        top.addWidget(icon_label)
        title_box = QVBoxLayout()
        title = QLabel("Antoshka")
        title.setObjectName("Title")
        status = QLabel("")
        status.setObjectName("Status")
        self.status_label = status
        title_box.addWidget(title)
        title_box.addWidget(status)
        top.addLayout(title_box)
        top.addStretch(1)
        self.ai_badge = QLabel("AI")
        self.ai_badge.setObjectName("AIBadge")
        self.ai_badge.hide()
        top.addWidget(self.ai_badge)
        settings_btn = IconButton(self._icon(self.icons.settings), self._icon(self.icons.settings_active))
        settings_btn.clicked.connect(self._open_settings)
        settings_btn.setObjectName("IconOnly")
        top.addWidget(settings_btn)
        root_layout.addLayout(top)

    def _build_chat(self, root_layout: QVBoxLayout) -> None:
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setObjectName("ChatScroll")
        self.chat_container = QWidget()
        self.chat_container_layout = QVBoxLayout(self.chat_container)
        self.chat_container_layout.setAlignment(Qt.AlignTop)
        self.chat_container_layout.setSpacing(8)
        self.chat_scroll.setWidget(self.chat_container)
        root_layout.addWidget(self.chat_scroll, stretch=1)

    def _build_input(self, root_layout: QVBoxLayout) -> None:
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.returnPressed.connect(self._send_text)
        input_row.addWidget(self.input, stretch=1)
        self.input_mic = IconButton(self._icon(self.icons.mic), self._icon(self.icons.mic_active))
        self.input_mic.pressed.connect(self._push_to_talk_start)
        self.input_mic.released.connect(self._push_to_talk_stop)
        input_row.addWidget(self.input_mic)
        root_layout.addLayout(input_row)

    def _build_actions(self, root_layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.listen_btn = IconButton(self._icon(self.icons.mic), self._icon(self.icons.mic_active), "Listen")
        self.listen_btn.clicked.connect(self._listen)
        row.addWidget(self.listen_btn)
        self.stop_btn = IconButton(self._icon(self.icons.stop), self._icon(self.icons.stop_active), "Stop")
        self.stop_btn.clicked.connect(self._stop_listen)
        row.addWidget(self.stop_btn)
        self.history_btn = IconButton(self._icon(self.icons.history), self._icon(self.icons.history_active), "History")
        self.history_btn.clicked.connect(self._open_history)
        row.addWidget(self.history_btn)
        self.volume_btn = IconButton(self._icon(self.icons.volume), self._icon(self.icons.volume_active), "Volume")
        self.volume_btn.clicked.connect(self._open_volume)
        row.addWidget(self.volume_btn)
        self.ai_btn = IconButton(self._icon(self.icons.ai), self._icon(self.icons.ai_active), "AI")
        self.ai_btn.clicked.connect(self._toggle_ai_mode)
        row.addWidget(self.ai_btn)
        row.addStretch(1)
        root_layout.addLayout(row)

    def _apply_styles(self) -> None:
        font = QFont("Bahnschrift", 11)
        QApplication.instance().setFont(font)
        theme = str(self.settings.get("ui", {}).get("theme", "dark")).lower()
        if theme == "light":
            self.setStyleSheet("""
                QWidget { color: #111827; }
                QMainWindow { background: transparent; }
                #Title { font-size: 20px; font-weight: 600; color: #0f172a; }
                #Status { font-size: 12px; color: #475569; }
                QLineEdit { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px 14px; color: #0f172a; }
                QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 12px; padding: 10px 12px; }
                #IconOnly { padding: 6px; }
                #ChatScroll { background: transparent; border: none; }
                QScrollArea > QWidget > QWidget { background: transparent; }
                QFrame#ChatBubble[kind="user"] { background: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 14px; }
                QFrame#ChatBubble[kind="bot"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; }
                #BubbleText { font-size: 13px; }
                #ActionCard { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; }
                #ActionTitle { font-size: 12px; font-weight: 700; color: #0f172a; }
                #ActionDetails { font-size: 12px; color: #475569; }
                #ActionLink { font-size: 11px; color: #0ea5e9; }
                #ActionStatus { font-size: 10px; color: #0f766e; }
                #AIBadge { background: #0ea5e9; color: #ffffff; padding: 4px 10px; border-radius: 10px; font-weight: 700; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { color: #e5e7ff; }
                QMainWindow { background: transparent; }
                #Title { font-size: 20px; font-weight: 600; color: #f1f4ff; }
                #Status { font-size: 12px; color: #9aa6c8; }
                QLineEdit { background: #0f1524; border: 1px solid #20283a; border-radius: 12px; padding: 12px 14px; color: #e5e7ff; }
                QPushButton { background: #151b2b; border: 1px solid #222a40; border-radius: 12px; padding: 10px 12px; }
                #IconOnly { padding: 6px; }
                #ChatScroll { background: transparent; border: none; }
                QScrollArea > QWidget > QWidget { background: transparent; }
                QFrame#ChatBubble[kind="user"] { background: #1a2338; border: 1px solid #28324a; border-radius: 14px; }
                QFrame#ChatBubble[kind="bot"] { background: #121a2b; border: 1px solid #212b40; border-radius: 14px; }
                #BubbleText { font-size: 13px; }
                #ActionCard { background: #0f172a; border: 1px solid #26304a; border-radius: 12px; }
                #ActionTitle { font-size: 12px; font-weight: 700; color: #e5e7ff; }
                #ActionDetails { font-size: 12px; color: #a4afcc; }
                #ActionLink { font-size: 11px; color: #7dd3fc; }
                #ActionStatus { font-size: 10px; color: #5eead4; }
                #AIBadge { background: #22d3ee; color: #0b1020; padding: 4px 10px; border-radius: 10px; font-weight: 700; }
            """)

    def _icon(self, name: str) -> QIcon:
        path = resource_path(Path("assets") / "icons" / name)
        return QIcon(str(path)) if path.exists() else QIcon()

    def _append_message(self, text: str, is_user: bool) -> None:
        bubble = ChatBubble(text, is_user)
        if is_user:
            wrap = QHBoxLayout()
            wrap.addStretch(1)
            wrap.addWidget(bubble)
            w = QWidget()
            w.setLayout(wrap)
            container = w
        else:
            container = bubble
            self._last_bot_bubble = bubble
        self.chat_container_layout.addWidget(container)
        QTimer.singleShot(0, self, lambda: self._scroll_to_bottom())

    def _append_action(self, result: ActionResult) -> None:
        card = ActionCard(result.title, result.details, result.status, result.url)
        bubble = ChatBubble(result.text, is_user=False, action_widget=card)
        self.chat_container_layout.addWidget(bubble)
        self._last_bot_bubble = bubble
        QTimer.singleShot(0, self, lambda: self._scroll_to_bottom())

    def _scroll_to_bottom(self) -> None:
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _notify(self, message: str) -> None:
        def _update() -> None:
            self._append_message(message, is_user=False)
            self._set_status("speaking")
            self._say_tts_async(message)
            self._set_status("ready")
        QTimer.singleShot(0, self, _update)

    def _set_status(self, text: str) -> None:
        if text == self._last_status:
            return
        self._last_status = text
        self.status_label.setText(f"voice assistant ? status: {text}")
        bubble = getattr(self, "_last_bot_bubble", None)
        if bubble:
            t = text.lower()
            if "speak" in t or "think" in t or "listen" in t:
                bubble.set_emphasis(1.0)
            else:
                bubble.set_emphasis(0.4)

    def _send_text(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self._process_text(text)

    def _process_text(self, text: str) -> None:
        if self._first_message:
            self._first_message = False
        self.input.clear()
        self._append_message(text, is_user=True)
        self._set_status("thinking")

        def _worker() -> None:
            try:
                if self.ai_mode and self.llm_client is not None:
                    append_chat(Path("data"), "user", text)
                    answer = self.llm_client.ask(text)
                    append_chat(Path("data"), "assistant", answer)
                elif self.ai_mode and self.llm_client is None:
                    answer = "AI nedostupen. Prover OPENAI_API_KEY i nastroyki."
                else:
                    answer = self.dialogue.handle_text(text)
            except Exception as e:  # noqa: BLE001
                self.log.exception("UI worker failed: %s", e)
                answer = "Proizoshla oshibka. Prover logi."

            if isinstance(answer, ActionResult):
                answer_text = answer.to_text()
            else:
                answer_text = str(answer)

            if not answer_text.strip():
                answer = "Ne ponyal komandu. Skazhi 'pomoshch'."
                answer_text = str(answer)

            if answer == "__EXIT__":
                QTimer.singleShot(0, self, self.close)
                return

            def _update() -> None:
                if isinstance(answer, ActionResult):
                    self._append_action(answer)
                else:
                    self._append_message(answer_text, is_user=False)
                self._set_status("speaking")
                self._say_tts_async(answer_text)
                self._set_status("ready")

            QTimer.singleShot(0, self, _update)

        threading.Thread(target=_worker, daemon=True).start()

    def _listen(self) -> None:
        if isinstance(self.stt, TextSTT):
            self._set_status("text mode")
            return
        if self.listening:
            return
        self.listening = True
        self.listen_btn.set_active(True)
        self.input_mic.set_active(True)
        self._set_status("listening")

        def _worker() -> None:
            try:
                text = self.stt.listen()
            except Exception:
                text = ""
            QTimer.singleShot(0, self, lambda: self._on_listen_result(text))

        threading.Thread(target=_worker, daemon=True).start()

    def _stop_listen(self) -> None:
        self.listen_btn.set_active(False)
        self.input_mic.set_active(False)
        self.listening = False
        try:
            self.stt.stop()
        except Exception:
            pass
        self._set_status("stopped")

    def _on_listen_result(self, text: Optional[str]) -> None:
        self.listening = False
        self.listen_btn.set_active(False)
        self.input_mic.set_active(False)
        if text is None:
            self._set_status("stopped")
            return
        if text.strip():
            self._process_text(text)
        else:
            self._set_status("ready")
            self._append_message("No speech detected. Try speaking louder.", is_user=False)

    def _push_to_talk_start(self) -> None:
        self._listen()

    def _push_to_talk_stop(self) -> None:
        self._stop_listen()

    def _open_settings(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setMinimumSize(460, 320)
        layout = QVBoxLayout(dlg)

        stt_mode = QComboBox()
        stt_mode.addItems(["auto", "text", "vosk"])
        stt_mode.setCurrentText(str(self.settings.get("stt", {}).get("mode", "text")))
        tts_enabled = QCheckBox("TTS enabled")
        tts_enabled.setChecked(bool(self.settings.get("tts", {}).get("enabled", True)))
        tts_provider = QComboBox()
        tts_provider.addItems(["auto", "pyttsx3", "edge"])
        tts_provider.setCurrentText(str(self.settings.get("tts", {}).get("provider", "auto")))
        tts_rate = QSlider(Qt.Horizontal)
        tts_rate.setRange(120, 240)
        tts_rate.setValue(int(self.settings.get("tts", {}).get("rate", 180)))
        tts_pitch = QSlider(Qt.Horizontal)
        tts_pitch.setRange(-50, 50)
        tts_pitch.setValue(int(self.settings.get("tts", {}).get("pitch", 0)))
        wake_word = QCheckBox("Wake word: Antoshka")
        wake_word.setChecked(bool(self.settings.get("ui", {}).get("wake_word", False)))

        layout.addWidget(QLabel("STT mode"))
        layout.addWidget(stt_mode)
        layout.addWidget(tts_enabled)
        layout.addWidget(QLabel("TTS provider"))
        layout.addWidget(tts_provider)
        layout.addWidget(QLabel("Rate"))
        layout.addWidget(tts_rate)
        layout.addWidget(QLabel("Pitch"))
        layout.addWidget(tts_pitch)
        layout.addWidget(wake_word)

        tts_test = QPushButton("Test sound")
        tts_test.clicked.connect(self._tts_test)
        layout.addWidget(tts_test)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(
            lambda: self._save_settings(
                dlg,
                stt_mode.currentText(),
                tts_enabled.isChecked(),
                tts_provider.currentText(),
                tts_rate.value(),
                tts_pitch.value(),
                wake_word.isChecked(),
            )
        )
        layout.addWidget(save_btn)
        dlg.exec()

    def _tts_test(self) -> None:
        self._set_status("speaking")
        self._say_tts_async("Proverka zvuka.")
        self._set_status("ready")

    def _save_settings(self, dlg: QDialog, stt_mode: str, tts_enabled: bool, tts_provider: str, tts_rate: int, tts_pitch: int, wake_word: bool) -> None:
        self.settings.setdefault("stt", {})["mode"] = stt_mode
        self.settings.setdefault("tts", {})["enabled"] = bool(tts_enabled)
        self.settings.setdefault("tts", {})["provider"] = tts_provider
        self.settings.setdefault("tts", {})["rate"] = int(tts_rate)
        self.settings.setdefault("tts", {})["pitch"] = int(tts_pitch)
        self.settings.setdefault("ui", {})["wake_word"] = bool(wake_word)
        save_settings(self.settings)
        self._on_settings_changed(self.settings)
        dlg.accept()

    def _open_history(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("History")
        dlg.setMinimumSize(560, 420)
        layout = QVBoxLayout(dlg)
        history = read_json(Path("data") / "history.json", default=[])
        box = QTextEdit()
        box.setReadOnly(True)
        for item in history:
            role = item.get("role", "")
            text = item.get("text", "")
            ts = item.get("ts", "")
            box.append(f"[{ts}] {role}: {text}")
        layout.addWidget(box)
        dlg.exec()

    def _open_volume(self) -> None:
        if self.app_context.volume is None:
            self._notify("Volume control is not available on this device.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Volume")
        dlg.setMinimumSize(360, 200)
        layout = QVBoxLayout(dlg)
        current = self.app_context.volume.get_level()
        current = 1.0 if current is None else current
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(current * 100))
        layout.addWidget(slider)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(lambda: self._apply_volume(dlg, slider.value()))
        layout.addWidget(apply_btn)
        dlg.exec()

    def _apply_volume(self, dlg: QDialog, value: int) -> None:
        level = max(0, min(100, int(value))) / 100.0
        if self.app_context.volume:
            self.app_context.volume.set_absolute(level)
        dlg.accept()

    def _toggle_ai_mode(self) -> None:
        if self.llm_client is None:
            self._notify("AI not available. Check OPENAI_API_KEY.")
            return
        self.ai_mode = not self.ai_mode
        self.settings.setdefault("ui", {})["ai_mode"] = bool(self.ai_mode)
        save_settings(self.settings)
        self._sync_ai_button()

    def _sync_ai_button(self) -> None:
        try:
            self.ai_btn.set_active(bool(self.ai_mode))
            if self.ai_mode:
                self.ai_badge.show()
            else:
                self.ai_badge.hide()
        except Exception:
            pass

    def _say_startup(self) -> None:
        self._say_tts_async("Antoshka started")

    def _say_tts_async(self, text: str) -> None:
        def _start() -> None:
            self.log.info("TTS async start: len=%s", len(text or ""))
            bubble = getattr(self, "_last_bot_bubble", None)
            if not self.settings.get("tts", {}).get("enabled", True):
                if not self._tts_warned:
                    self._append_message("TTS disabled in settings.", is_user=False)
                    self._tts_warned = True
                return
            if self.tts.provider != "edge" and self.tts.engine is None:
                if not self._tts_warned:
                    self._append_message("TTS unavailable: pyttsx3 missing.", is_user=False)
                    self._tts_warned = True
                return
            if self.tts.last_error:
                if not self._tts_warned:
                    self._append_message(f"TTS error: {self.tts.last_error}", is_user=False)
                    self._tts_warned = True
                return
            if bubble:
                bubble.set_wave_active(True)

            def _worker() -> None:
                try:
                    self.tts.say(text)
                finally:
                    if bubble:
                        QTimer.singleShot(0, self, lambda: bubble.set_wave_active(False))

            threading.Thread(target=_worker, daemon=True).start()

        QTimer.singleShot(0, self, _start)

    def _apply_stt_mode_ui(self) -> None:
        if isinstance(self.stt, TextSTT):
            self.listen_btn.setEnabled(False)
            self.input_mic.setEnabled(False)
        else:
            self.listen_btn.setEnabled(True)
            self.input_mic.setEnabled(True)

    def _init_wake_word(self) -> None:
        if not self.settings.get("ui", {}).get("wake_word", False):
            return
        try:
            self.wake_listener = WakeWordListener(
                WakeWordConfig(
                    model_path=str(self.settings.get("stt", {}).get("vosk_model_path", "models/vosk"))
                ),
                on_wake=self._handle_wake,
            )
            self.wake_listener.start()
        except Exception as e:  # noqa: BLE001
            self.log.warning("Wake word disabled: %s", e)
            self._notify("Wake word unavailable: check microphone and Vosk model.")

    def _handle_wake(self, phrase: str | None = None) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._set_status("listening")
        self._say_tts_async("Slushayu")
        self._listen()


def run() -> None:
    app = QApplication(sys.argv)
    window = AntoshkaWindow()
    window.show()
    sys.exit(app.exec())
