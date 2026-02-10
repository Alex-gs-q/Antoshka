from __future__ import annotations

import math
import sys
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPoint, QSize, QTimer, QUrl, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QAction,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QGraphicsOpacityEffect,
    QSystemTrayIcon,
)

from core.actions import ActionResult
from core.app_context import AppContext
from core.config import load_settings, save_settings
from core.dialogue import Dialogue, DialogueConfig
from core.language import normalize_language_mode, resolve_language
from core.i18n import t as tr, examples as sample_examples
from core.logger import setup_logger
from core.resources import resource_path
from core.stt import TextSTT, create_stt
from core.wake_word import WakeWordListener, WakeWordConfig
from llm.client import LLMClient, LLMConfig
from services.chat_history import append_chat, clear_chat_history
from services.scheduler import Scheduler
from services.storage import read_json
from services.history import clear_history
from services.volume import VolumeController
from services.audio.microphone import list_input_devices, MicLevelMonitor, test_microphone
from alerts.audio_alerts import AudioAlerts
from alerts.models import Event
from alerts.notifications import NotificationService, NotificationPayload
from alerts.settings import get_alert_settings
from services.audio.alert_sound import list_alert_sounds
from services.tts.tts_worker import TTSWorker
from services.tts.voices import list_edge_voices, list_pyttsx3_voices
from services.voice_timeout import get_voice_timeout_seconds, apply_timeout_ms
from ui.theme import build_theme, choose_font


@dataclass(frozen=True)
class IconSet:
    mic: str = "glyph_mic_96.png"
    mic_active: str = "glyph_mic_96.png"
    stop: str = "glyph_stop_96.png"
    stop_active: str = "glyph_stop_96.png"
    history: str = "glyph_history_96.png"
    history_active: str = "glyph_history_96.png"
    volume: str = "glyph_volume_96.png"
    volume_active: str = "glyph_volume_96.png"
    ai: str = "glyph_ai_96.png"
    ai_active: str = "glyph_ai_96.png"
    settings: str = "glyph_settings_96.png"
    settings_active: str = "glyph_settings_96.png"
    app_icon: str = "app_icon_v3_256.png"


class GradientBackground(QWidget):
    def __init__(self, theme):
        super().__init__()
        self._theme = theme

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, self._theme.bg_top)
        grad.setColorAt(1.0, self._theme.bg_bottom)
        painter.fillRect(self.rect(), grad)


class IconButton(QPushButton):
    def __init__(self, icon_off: QIcon, icon_on: Optional[QIcon] = None, text: str = ""):
        super().__init__(text)
        self._icon_off = icon_off
        self._icon_on = icon_on or icon_off
        self._active = False
        self.setIcon(self._icon_off)
        self.setIconSize(QSize(36, 36))
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(False)
        self.setObjectName("IconButton")

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setIcon(self._icon_on if active else self._icon_off)
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def is_active(self) -> bool:
        return self._active


class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool, theme, action_widget: QWidget | None = None):
        super().__init__()
        self.setObjectName("ChatBubble")
        self._is_user = is_user
        self._theme = theme
        self._wave_phase = 0.0
        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(40)
        self._wave_timer.timeout.connect(self._tick_wave)
        self._emphasis = 0.35

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
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
            self._wave_timer.start()

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.update()

    def set_emphasis(self, level: float) -> None:
        if self._is_user:
            return
        self._emphasis = max(0.2, min(1.0, float(level)))
        self.update()

    def _tick_wave(self) -> None:
        self._wave_phase += 0.10
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._is_user:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 14.0

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        painter.fillPath(path, self._theme.bot_bubble_bg)

        painter.setClipPath(path)
        base_y = rect.top() + rect.height() * 0.6
        wave_amp = 6.0 * self._emphasis
        spacing = 6.0
        for idx in range(4):
            points = []
            for x in range(int(rect.left()) + 6, int(rect.right()) - 6, 6):
                phase = self._wave_phase + idx * 1.1
                y = base_y + idx * spacing + wave_amp * math.sin((x - rect.left()) * 0.045 + phase)
                points.append(QPoint(x, int(y)))
            alpha = int(70 * self._emphasis) - idx * 8
            color = QColor(self._theme.accent.red(), self._theme.accent.green(), self._theme.accent.blue(), max(20, alpha))
            painter.setPen(QPen(color, 1.1))
            for i in range(1, len(points)):
                painter.drawLine(points[i - 1], points[i])
        painter.setClipping(False)

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, self._theme.accent)
        grad.setColorAt(1.0, self._theme.accent_2)
        pen = QPen(QBrush(grad), 1.6 + 1.2 * self._emphasis)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)


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

        status_lbl = QLabel(status)
        status_lbl.setObjectName("ActionStatus")
        layout.addWidget(status_lbl)


class EventCardWidget(QFrame):
    def __init__(
        self,
        title: str,
        subtitle: str,
        when_text: str,
        buttons_row: QWidget,
    ):
        super().__init__()
        self.setObjectName("EventCard")
        self._pulse_anim: QPropertyAnimation | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("EventTitle")
        layout.addWidget(title_lbl)

        if subtitle:
            subtitle_lbl = QLabel(subtitle)
            subtitle_lbl.setObjectName("EventSubtitle")
            subtitle_lbl.setWordWrap(True)
            layout.addWidget(subtitle_lbl)

        when_lbl = QLabel(when_text)
        when_lbl.setObjectName("EventWhen")
        layout.addWidget(when_lbl)

        self._status = QLabel("")
        self._status.setObjectName("EventStatus")
        layout.addWidget(self._status)

        layout.addWidget(buttons_row)

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0)
        self.setGraphicsEffect(effect)

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_alerting(self, active: bool) -> None:
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            return
        if active:
            if self._pulse_anim is None:
                anim = QPropertyAnimation(effect, b"opacity")
                anim.setStartValue(0.88)
                anim.setEndValue(1.0)
                anim.setDuration(900)
                anim.setEasingCurve(QEasingCurve.InOutSine)
                anim.setLoopCount(-1)
                anim.start()
                self._pulse_anim = anim
        else:
            if self._pulse_anim is not None:
                self._pulse_anim.stop()
                self._pulse_anim = None
            effect.setOpacity(1.0)

class StartScreen(QWidget):
    def __init__(self, theme, on_start):
        super().__init__()
        self._theme = theme
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._on_start = on_start

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)
        root.addStretch(1)

        self.hero = QWidget()
        hero_layout = QVBoxLayout(self.hero)
        hero_layout.setAlignment(Qt.AlignHCenter)
        hero_layout.setSpacing(10)

        self.logo = QLabel(tr("app_name", "ru"))
        self.logo.setObjectName("StartLogo")
        self.logo.setAlignment(Qt.AlignHCenter)
        self.title = QLabel(tr("start_title", "ru"))
        self.title.setObjectName("StartTitle")
        self.title.setAlignment(Qt.AlignHCenter)
        self.subtitle = QLabel(tr("start_subtitle", "ru"))
        self.subtitle.setObjectName("StartSubtitle")
        self.subtitle.setAlignment(Qt.AlignHCenter)

        hero_layout.addWidget(self.logo)
        hero_layout.addWidget(self.title)
        hero_layout.addWidget(self.subtitle)

        root.addWidget(self.hero, alignment=Qt.AlignHCenter)
        root.addStretch(1)

        self.examples_title = QLabel(tr("examples_title", "ru"))
        self.examples_title.setObjectName("StartExamplesTitle")
        self.examples = QLabel("")
        self.examples.setObjectName("StartExamples")
        self.examples.setAlignment(Qt.AlignHCenter)
        self.examples.setWordWrap(True)

        root.addWidget(self.examples_title, alignment=Qt.AlignHCenter)
        root.addWidget(self.examples, alignment=Qt.AlignHCenter)
        root.addStretch(1)

        self.start_btn = QPushButton(tr("start_button", "ru"))
        self.start_btn.setObjectName("StartButton")
        self.start_btn.clicked.connect(self._on_start)
        root.addWidget(self.start_btn, alignment=Qt.AlignHCenter)
        root.addStretch(1)

        self.hero.mousePressEvent = lambda _: self._on_start()
        self.mousePressEvent = lambda _: self._on_start()

    def set_theme(self, theme) -> None:
        self._theme = theme
        self.update()

    def set_language(self, lang: str) -> None:
        self.logo.setText(tr("app_name", lang))
        self.title.setText(tr("start_title", lang))
        self.subtitle.setText(tr("start_subtitle", lang))
        self.start_btn.setText(tr("start_button", lang))
        self.examples_title.setText(tr("examples_title", lang))
        items = sample_examples(lang)
        self.examples.setText(" • ".join(items))

    def _tick(self) -> None:
        self._phase += 0.08
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        base_y = rect.center().y()
        spacing = 10.0
        for idx in range(6):
            points = []
            for x in range(int(rect.left()), int(rect.right()), 8):
                phase = self._phase + idx * 1.2
                amp = 8 + idx * 1.2
                y = base_y + (idx - 2.5) * spacing + amp * math.sin((x - rect.left()) * 0.03 + phase)
                points.append(QPoint(x, int(y)))
            alpha = 70 - idx * 6
            color = QColor(self._theme.accent.red(), self._theme.accent.green(), self._theme.accent.blue(), max(20, alpha))
            painter.setPen(QPen(color, 1.1))
            for i in range(1, len(points)):
                painter.drawLine(points[i - 1], points[i])


class AntoshkaWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._pending_notices: list[str] = []
        self.settings = load_settings()
        log_level = (self.settings.get("app", {}) or {}).get("log_level", "INFO")
        self.log = setup_logger(level=str(log_level))
        self.debug_mode = bool((self.settings.get("app", {}) or {}).get("debug", False))
        self.icons = IconSet()
        self._first_message = True
        self._tts_warned = False
        self.listening = False
        self.ai_mode = bool(self.settings.get("ui", {}).get("ai_mode", False))
        self._last_status = ""
        self.wake_listener = None
        self.language_mode = normalize_language_mode(
            (self.settings.get("app", {}) or {}).get("language", "auto")
        )
        self.language = resolve_language(self.language_mode, None, fallback="ru")
        self.theme = build_theme(self.settings)

        self._init_tts()
        self._init_llm()
        self._init_stt()
        self._init_context()
        self._init_ui()
        self.alert_player = AudioAlerts(self)
        self._active_alert_meta: dict | None = None
        self._event_cards: dict[str, tuple[EventCardWidget, ChatBubble]] = {}
        self._init_tray_and_notifications()
        self._voice_timeout_timer = QTimer(self)
        self._voice_timeout_timer.setSingleShot(True)
        self._voice_timeout_timer.timeout.connect(self._on_voice_timeout)
        self._voice_timeout_request_id = 0
        self._voice_timeout_active_id: int | None = None
        self._voice_timeout_lang: str | None = None
        self._voice_timeout_seconds: int | None = None
        self._voice_timeout_expired_ids: set[int] = set()
        self._listen_interrupted = False
        self._init_wake_word()
        self._apply_stt_mode_ui()
        self._sync_ai_button()
        self._apply_language()
        if self.debug_mode:
            self._self_check()
        QTimer.singleShot(0, self, self._report_stt_status)
        self._flush_notices()
        self._say_startup()

    def _init_tts(self) -> None:
        self.tts_worker = TTSWorker(self.settings)

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
        self.log.info("STT init ok: %s", type(self.stt).__name__)

    def _init_tray_and_notifications(self) -> None:
        icon_path = resource_path(Path("assets") / "icons" / self.icons.app_icon)
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.messageClicked.connect(self._restore_window)
        menu = QMenu()
        stop_all = QAction(tr("btn_alert_stop", self.language), self)
        stop_all.triggered.connect(self._alert_stop_all)
        menu.addAction(stop_all)
        menu.addSeparator()
        quit_action = QAction(tr("btn_stop", self.language), self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.notifier = NotificationService(
            app_id="Antoshka.Assistant",
            on_click=self._restore_window,
            on_action=self._on_notification_action,
            tray_fallback=self.tray,
        )

    def _restore_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _enqueue_notice(self, message: str) -> None:
        if hasattr(self, "chat_container_layout"):
            self._append_message(message, is_user=False)
        else:
            self._pending_notices.append(message)

    def _flush_notices(self) -> None:
        if not self._pending_notices:
            return
        for msg in self._pending_notices:
            self._append_message(msg, is_user=False)
        self._pending_notices.clear()

    def _init_context(self) -> None:
        self.scheduler = Scheduler(notify=self._notify)
        volume = None
        if self.tts_worker is not None:
            volume = VolumeController(
                get_level=self.tts_worker.get_volume,
                set_level=self.tts_worker.set_volume,
                set_mute_fn=self.tts_worker.set_mute,
            )
        self.app_context = AppContext(
            notify=self._notify,
            data_dir=Path("data"),
            scheduler=self.scheduler,
            volume=volume,
            llm_client=self.llm_client,
            on_settings_changed=self._on_settings_changed,
            language_mode=self.language_mode,
            language=self.language,
        )
        self.dialogue = Dialogue(
            DialogueConfig(
                dangerous_mode=bool(self.settings.get("safety", {}).get("dangerous_mode", False)),
                llm_client=self.llm_client,
                app_context=self.app_context,
            )
        )

    def _on_settings_changed(self, settings: dict) -> None:
        prev_lang = self.language
        prev_mode = self.language_mode
        self.settings = settings
        self.language_mode = normalize_language_mode(
            (self.settings.get("app", {}) or {}).get("language", "auto")
        )
        self.language = resolve_language(self.language_mode, None, fallback="ru")
        if prev_lang != self.language:
            self.log.info("STT language switched %s->%s", prev_lang, self.language)
        if prev_mode != self.language_mode:
            self.log.info("STT language mode switched %s->%s", prev_mode, self.language_mode)
        if getattr(self, "app_context", None) is not None:
            self.app_context.language_mode = self.language_mode
            self.app_context.language = self.language
        if getattr(self, "tts_worker", None) is None:
            self._init_tts()
        else:
            self.tts_worker.update_settings(self.settings)
        self._init_stt()
        self._init_context()
        self._init_wake_word()
        self.theme = build_theme(self.settings)
        self._apply_stt_mode_ui()
        self._apply_styles()
        self._apply_language()
        self._report_stt_status()

    def _report_stt_status(self) -> None:
        requested_mode = (self.settings.get("stt", {}) or {}).get("mode", "text")
        fallback_from = getattr(self.stt, "_fallback_from", None)
        fallback_to = getattr(self.stt, "_lang", None)
        if fallback_from and fallback_to:
            msg = tr("msg_stt_fallback", self.language).format(
                from_lang=str(fallback_from).upper(), to_lang=str(fallback_to).upper()
            )
            self.log.warning("STT fallback: %s -> %s", fallback_from, fallback_to)
            self._enqueue_notice(msg)
        if isinstance(self.stt, TextSTT) and str(requested_mode) in {"vosk", "auto"}:
            self._enqueue_notice(tr("msg_stt_model_missing", self.language))

    def _init_ui(self) -> None:
        self.setWindowTitle(tr("app_name", self.language))
        self.setMinimumSize(820, 520)
        app_icon = resource_path(Path("assets") / "icons" / self.icons.app_icon)
        if app_icon.exists():
            self.setWindowIcon(QIcon(str(app_icon)))

        root = GradientBackground(self.theme)
        self.root = root
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.start_screen = StartScreen(self.theme, self._start_chat)
        self.stack.addWidget(self.start_screen)

        self.chat_page = QWidget()
        chat_layout = QVBoxLayout(self.chat_page)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(12)
        self._build_topbar(chat_layout)
        self._build_chat(chat_layout)
        self._build_input(chat_layout)
        self._build_actions(chat_layout)
        self.stack.addWidget(self.chat_page)

        show_start = bool(self.settings.get("ui", {}).get("show_start_screen", True))
        self.stack.setCurrentWidget(self.start_screen if show_start else self.chat_page)
        self.start_screen.set_language(self.language)
        self._apply_styles()

    def _build_topbar(self, root_layout: QVBoxLayout) -> None:
        top = QHBoxLayout()
        icon_label = QLabel()
        icon_path = resource_path(Path("assets") / "icons" / self.icons.app_icon)
        if icon_path.exists():
            icon_label.setPixmap(QPixmap(str(icon_path)).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        top.addWidget(icon_label)
        title_box = QVBoxLayout()
        title = QLabel(tr("app_name", self.language))
        title.setObjectName("Title")
        self.title_label = title
        status = QLabel("")
        status.setObjectName("Status")
        self.status_label = status
        title_box.addWidget(title)
        title_box.addWidget(status)
        top.addLayout(title_box)
        top.addStretch(1)
        self.ai_badge = QLabel(tr("btn_ai", self.language))
        self.ai_badge.setObjectName("AIBadge")
        self.ai_badge.hide()
        top.addWidget(self.ai_badge)
        settings_btn = IconButton(self._icon(self.icons.settings), self._icon(self.icons.settings_active))
        settings_btn.clicked.connect(self._open_settings)
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
        self.input.setPlaceholderText(tr("placeholder", self.language))
        self.input.returnPressed.connect(self._send_text)
        input_row.addWidget(self.input, stretch=1)
        self.input_mic = IconButton(self._icon(self.icons.mic), self._icon(self.icons.mic_active))
        self.input_mic.clicked.connect(self._toggle_listen)
        input_row.addWidget(self.input_mic)
        root_layout.addLayout(input_row)

    def _build_actions(self, root_layout: QVBoxLayout) -> None:
        self.actions_panel = QWidget()
        row = QHBoxLayout(self.actions_panel)
        row.setContentsMargins(0, 0, 0, 0)
        self.listen_btn = IconButton(self._icon(self.icons.mic), self._icon(self.icons.mic_active), tr("btn_listen", self.language))
        self.listen_btn.clicked.connect(self._toggle_listen)
        row.addWidget(self.listen_btn)
        self.stop_btn = IconButton(self._icon(self.icons.stop), self._icon(self.icons.stop_active), tr("btn_stop", self.language))
        self.stop_btn.clicked.connect(self._stop_listen)
        row.addWidget(self.stop_btn)
        self.history_btn = IconButton(self._icon(self.icons.history), self._icon(self.icons.history_active), tr("btn_history", self.language))
        self.history_btn.clicked.connect(self._open_history)
        row.addWidget(self.history_btn)
        self.volume_btn = IconButton(self._icon(self.icons.volume), self._icon(self.icons.volume_active), tr("btn_volume", self.language))
        self.volume_btn.clicked.connect(self._open_volume)
        row.addWidget(self.volume_btn)
        self.ai_btn = IconButton(self._icon(self.icons.ai), self._icon(self.icons.ai_active), tr("btn_ai", self.language))
        self.ai_btn.clicked.connect(self._toggle_ai_mode)
        row.addWidget(self.ai_btn)
        self.clear_btn = QPushButton(tr("btn_clear_chat", self.language))
        self.clear_btn.setObjectName("ClearChat")
        self.clear_btn.setIcon(self._icon(self.icons.stop))
        self.clear_btn.setIconSize(QSize(18, 18))
        self.clear_btn.clicked.connect(self._clear_chat_clicked)
        row.addWidget(self.clear_btn)
        row.addStretch(1)
        root_layout.addWidget(self.actions_panel)

    def _apply_styles(self) -> None:
        font = QFont(choose_font(), 11)
        QApplication.instance().setFont(font)
        theme = self.theme
        self.root.set_theme(theme)
        self.setStyleSheet(
            f"""
                QWidget {{ color: {theme.text_primary.name()}; }}
                QMainWindow {{ background: transparent; }}
                #Title {{ font-size: 20px; font-weight: 600; color: {theme.text_primary.name()}; }}
                #Status {{ font-size: 12px; color: {theme.text_muted.name()}; }}
                QLineEdit {{
                    background: {theme.input_bg.name()};
                    border: 1px solid {theme.input_border.name()};
                    border-radius: 12px;
                    padding: 12px 14px;
                    color: {theme.text_primary.name()};
                }}
                QPushButton {{
                    background: {theme.button_bg.name()};
                    border: 1px solid {theme.button_border.name()};
                    border-radius: 12px;
                    padding: 10px 12px;
                }}
                #IconButton {{
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 12px;
                    padding: 6px;
                }}
                #IconButton:hover {{
                    background: rgba(255, 255, 255, 0.04);
                    border-color: {theme.accent.name()};
                }}
                #IconButton:pressed {{
                    background: rgba(255, 255, 255, 0.08);
                    border-color: {theme.accent.name()};
                }}
                #IconButton[active="true"] {{
                    background: rgba(255, 255, 255, 0.10);
                    border-color: {theme.accent.name()};
                }}
                #ClearChat {{
                    background: transparent;
                    border: 1px solid {theme.button_border.name()};
                    border-radius: 12px;
                    padding: 8px 12px;
                }}
                #ClearChat:hover {{
                    border-color: {theme.accent.name()};
                    background: rgba(255, 255, 255, 0.04);
                }}
                #ClearChat:pressed {{
                    background: rgba(255, 255, 255, 0.08);
                }}
                #IconOnly {{ padding: 6px; }}
                #ChatScroll {{ background: transparent; border: none; }}
                QScrollArea > QWidget > QWidget {{ background: transparent; }}
                QFrame#ChatBubble[kind="user"] {{
                    background: {theme.user_bubble_bg.name()};
                    border: 1px solid {theme.user_bubble_border.name()};
                    border-radius: 14px;
                }}
                QFrame#ChatBubble[kind="bot"] {{
                    background: transparent;
                    border: none;
                }}
                #BubbleText {{ font-size: 13px; color: {theme.text_primary.name()}; }}
                #ActionCard {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                }}
                #ActionTitle {{ font-size: 12px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #ActionDetails {{ font-size: 12px; color: {theme.text_muted.name()}; }}
                #ActionLink {{ font-size: 11px; color: {theme.accent.name()}; }}
                #ActionStatus {{ font-size: 10px; color: {theme.accent.name()}; }}
                #EventCard {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                }}
                #EventTitle {{ font-size: 13px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #EventSubtitle {{ font-size: 12px; color: {theme.text_primary.name()}; }}
                #EventWhen {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #EventStatus {{ font-size: 11px; color: {theme.accent.name()}; }}
                #EventCard QPushButton {{
                    background: {theme.button_bg.name()};
                    border: 1px solid {theme.button_border.name()};
                    border-radius: 8px;
                    padding: 4px 8px;
                }}
                #EventCard QPushButton:hover {{
                    border-color: {theme.accent.name()};
                    background: rgba(255, 255, 255, 0.06);
                }}
                #EventCard QPushButton:pressed {{
                    background: rgba(255, 255, 255, 0.10);
                }}
                #AIBadge {{
                    background: {theme.accent.name()};
                    color: #0b1020;
                    padding: 4px 10px;
                    border-radius: 10px;
                    font-weight: 700;
                }}
                #SettingsCard {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                    padding: 10px;
                }}
                #SettingsLabel {{ font-size: 13px; color: {theme.text_primary.name()}; }}
                #HelperText {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #SectionTitle {{ font-size: 16px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #StartLogo {{ font-size: 24px; font-weight: 700; color: {theme.accent.name()}; }}
                #StartTitle {{ font-size: 26px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #StartSubtitle {{ font-size: 14px; color: {theme.text_muted.name()}; }}
                #StartExamplesTitle {{ font-size: 12px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #StartExamples {{ font-size: 12px; color: {theme.text_muted.name()}; }}
                #StartButton {{
                    background: {theme.accent.name()};
                    color: #0b1020;
                    border: none;
                    border-radius: 14px;
                    padding: 10px 22px;
                    font-weight: 700;
                }}
                QProgressBar {{
                    background: {theme.input_bg.name()};
                    border: 1px solid {theme.input_border.name()};
                    border-radius: 6px;
                    height: 12px;
                }}
                QProgressBar::chunk {{
                    background: {theme.accent.name()};
                    border-radius: 6px;
                }}
                QComboBox, QLineEdit, QSpinBox {{
                    min-height: 32px;
                    padding: 4px 8px;
                }}
            """
        )
        for bubble in self.findChildren(ChatBubble):
            bubble.set_theme(self.theme)
        if getattr(self, "start_screen", None) is not None:
            self.start_screen.set_theme(self.theme)

    def _apply_language(self) -> None:
        self.setWindowTitle(tr("app_name", self.language))
        if getattr(self, "start_screen", None) is not None:
            self.start_screen.set_language(self.language)
        if getattr(self, "title_label", None) is not None:
            self.title_label.setText(tr("app_name", self.language))
        self.input.setPlaceholderText(tr("placeholder", self.language))
        self.listen_btn.setText(tr("btn_listen", self.language))
        self.stop_btn.setText(tr("btn_stop", self.language))
        self.history_btn.setText(tr("btn_history", self.language))
        self.volume_btn.setText(tr("btn_volume", self.language))
        self.ai_btn.setText(tr("btn_ai", self.language))
        self.clear_btn.setText(tr("btn_clear_chat", self.language))
        self.ai_badge.setText(tr("btn_ai", self.language))

    def _start_chat(self) -> None:
        if self.stack.currentWidget() == self.chat_page:
            return
        hero = self.start_screen.hero
        effect = QGraphicsOpacityEffect(hero)
        hero.setGraphicsEffect(effect)
        start_rect = hero.geometry()
        end_rect = start_rect.adjusted(0, -40, 0, -40)
        end_rect.setWidth(int(start_rect.width() * 0.85))
        end_rect.setHeight(int(start_rect.height() * 0.85))
        end_rect.moveCenter(start_rect.center() + QPoint(0, -40))

        anim_geo = QPropertyAnimation(hero, b"geometry")
        anim_geo.setDuration(420)
        anim_geo.setStartValue(start_rect)
        anim_geo.setEndValue(end_rect)
        anim_geo.setEasingCurve(QEasingCurve.InOutCubic)

        anim_op = QPropertyAnimation(effect, b"opacity")
        anim_op.setDuration(420)
        anim_op.setStartValue(1.0)
        anim_op.setEndValue(0.0)
        anim_op.setEasingCurve(QEasingCurve.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_geo)
        group.addAnimation(anim_op)

        def _after() -> None:
            self.stack.setCurrentWidget(self.chat_page)
            self._animate_chat_entrance()

        group.finished.connect(_after)
        group.start()

    def _animate_chat_entrance(self) -> None:
        def _run() -> None:
            panel = self.actions_panel
            end_rect = panel.geometry()
            start_rect = end_rect.translated(0, 24)
            panel.setGeometry(start_rect)
            effect = QGraphicsOpacityEffect(panel)
            panel.setGraphicsEffect(effect)
            effect.setOpacity(0.0)

            anim_geo = QPropertyAnimation(panel, b"geometry")
            anim_geo.setDuration(360)
            anim_geo.setStartValue(start_rect)
            anim_geo.setEndValue(end_rect)
            anim_geo.setEasingCurve(QEasingCurve.OutCubic)

            anim_op = QPropertyAnimation(effect, b"opacity")
            anim_op.setDuration(360)
            anim_op.setStartValue(0.0)
            anim_op.setEndValue(1.0)
            anim_op.setEasingCurve(QEasingCurve.OutCubic)

            group = QParallelAnimationGroup(self)
            group.addAnimation(anim_geo)
            group.addAnimation(anim_op)
            group.start()

        QTimer.singleShot(0, self, _run)

    def _icon(self, name: str) -> QIcon:
        path = resource_path(Path("assets") / "icons" / name)
        return QIcon(str(path)) if path.exists() else QIcon()

    def _append_message(self, text: str, is_user: bool, action_widget: QWidget | None = None) -> ChatBubble:
        bubble = ChatBubble(text, is_user, self.theme, action_widget=action_widget)
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
        return bubble

    def _append_action(self, result: ActionResult) -> None:
        status_key = "status_ok" if (result.status or "").lower() == "ok" else "status_error"
        status_text = tr(status_key, self.language)
        card = ActionCard(result.title, result.details, status_text, result.url)
        bubble = ChatBubble(result.text, is_user=False, theme=self.theme, action_widget=card)
        self.chat_container_layout.addWidget(bubble)
        self._last_bot_bubble = bubble
        QTimer.singleShot(0, self, lambda: self._scroll_to_bottom())

    def _scroll_to_bottom(self) -> None:
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _resolve_language_for_text(self, text: str) -> str:
        lang = resolve_language(self.language_mode, text, fallback=self.language)
        if lang != self.language:
            self.language = lang
            if getattr(self, "app_context", None) is not None:
                self.app_context.language = lang
            self.log.info("Language detected: %s", lang)
            self._apply_language()
        return lang

    def _clear_chat_ui(self) -> None:
        layout = self.chat_container_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._append_message(tr("msg_chat_cleared", self.language), is_user=False)

    def _confirm_clear_history(self) -> bool:
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("confirm_clear_title", self.language))
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(tr("confirm_clear_text", self.language)))
        btn_row = QHBoxLayout()
        yes_btn = QPushButton(tr("confirm_yes", self.language))
        no_btn = QPushButton(tr("confirm_no", self.language))
        btn_row.addWidget(yes_btn)
        btn_row.addWidget(no_btn)
        layout.addLayout(btn_row)
        result = {"ok": False}

        def _yes() -> None:
            result["ok"] = True
            dlg.accept()

        def _no() -> None:
            result["ok"] = False
            dlg.reject()

        yes_btn.clicked.connect(_yes)
        no_btn.clicked.connect(_no)
        dlg.exec()
        return bool(result["ok"])

    def _clear_chat_flow(self) -> None:
        self._clear_chat_ui()
        if self._confirm_clear_history():
            clear_history(Path("data"))
            clear_chat_history(Path("data"))
            self.log.info("Chat history cleared")

    def _clear_chat_clicked(self) -> None:
        self._clear_chat_flow()

    def _notify(self, message: str | Event) -> None:
        def _update() -> None:
            if isinstance(message, Event):
                self._handle_alert_notify(message)
                return
            self._append_message(message, is_user=False)
            self._set_status("speaking")
            self._say_tts_async(message, self.language)
            self._set_status("ready")
        QTimer.singleShot(0, self, _update)

    def _handle_alert_notify(self, event: Event) -> None:
        kind = str(event.type)
        if kind == "timer":
            duration = str(event.payload.get("duration_text") or event.duration_sec or "")
            msg = tr("msg_timer_done", self.language).format(duration=duration)
        elif kind == "reminder":
            msg = tr("msg_reminder_prefix", self.language).format(text=str(event.payload.get("text", "")))
        elif kind == "alarm":
            msg = tr("msg_alarm_fired", self.language)
        else:
            msg = str(event.payload.get("message", ""))
        actions = self._build_alert_actions(event)
        subtitle = ""
        if kind == "timer":
            subtitle = f"{tr('label_duration', self.language)}: {duration}"
        elif kind == "reminder":
            subtitle = str(event.payload.get("text", ""))
        when_text = event.due_time.strftime("%H:%M:%S")
        if kind == "timer":
            title = tr("action_timer_title", self.language)
        elif kind == "reminder":
            title = tr("action_reminder_title", self.language)
        elif kind == "note":
            title = tr("action_note_title", self.language)
        else:
            title = tr("action_alarm_title", self.language)

        card = EventCardWidget(
            title=title,
            subtitle=subtitle,
            when_text=when_text,
            buttons_row=actions,
        )
        bubble = self._append_message(msg, is_user=False, action_widget=card)
        self._event_cards[event.id] = (card, bubble)
        self._animate_widget_in(bubble)
        card.set_alerting(True)
        bubble.set_emphasis(1.0)
        self._play_alert_sound_from_settings()
        self._active_alert_meta = event.payload
        self.log.info("ALERT start type=%s id=%s sound=%s", kind, event.id, self.settings.get("ui", {}).get("alerts_sound"))
        self._notify_system_event(event, msg)

    def _build_alert_actions(self, event: Event) -> QWidget:
        settings = get_alert_settings(self.settings)
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        if settings.get("snooze_quick_enabled", True):
            for minutes in settings.get("snooze_quick_buttons", []):
                btn = QPushButton(f"+{int(minutes)}")
                btn.clicked.connect(lambda _, m=int(minutes): self._alert_snooze(event.id, m))
                layout.addWidget(btn)

        if settings.get("snooze_dropdown_enabled", True):
            dropdown = QComboBox()
            for minutes in settings.get("snooze_dropdown_options", []):
                dropdown.addItem(f"{int(minutes)}", int(minutes))
            dropdown.activated.connect(
                lambda _, dd=dropdown: self._alert_snooze(event.id, int(dd.currentData() or settings.get("snooze_default_minutes", 5)))
            )
            layout.addWidget(dropdown)

        stop_btn = QPushButton(tr("btn_alert_stop", self.language))
        stop_btn.clicked.connect(lambda: self._alert_stop(event.id, "user"))
        layout.addWidget(stop_btn)

        if event.type == "timer" and settings.get("timer_restart_enabled", True):
            restart_btn = QPushButton(tr("btn_alert_repeat", self.language))
            restart_btn.clicked.connect(lambda: self._alert_restart(event))
            layout.addWidget(restart_btn)

        return box

    def _alert_snooze(self, event_id: str, minutes: int) -> None:
        minutes = max(1, int(minutes))
        event = self.app_context.scheduler.get_event(event_id)
        if not event:
            return
        event.snooze_count += 1
        new_due = datetime.now() + timedelta(minutes=minutes)
        ok = self.app_context.scheduler.reschedule_event(event_id, new_due)
        if ok:
            self._alert_stop(event_id, "snooze")
            self._update_event_card(event_id, tr("msg_snoozed", self.language).format(minutes=minutes))
            self.log.info("ALERT snooze id=%s minutes=%s", event_id, minutes)

    def _alert_restart(self, event: Event) -> None:
        new_id = self.app_context.scheduler.restart_timer(event.id)
        if not new_id:
            return
        self._alert_stop(event.id, "restart")
        self._update_event_card(event.id, tr("msg_timer_restarted", self.language))
        self.log.info("ALERT restart id=%s new_id=%s", event.id, new_id)

    def _alert_stop(self, event_id: str, reason: str) -> None:
        self._stop_alert_sound()
        self.app_context.scheduler.dismiss_event(event_id)
        self._update_event_card(event_id, tr("msg_alert_stopped", self.language))
        self._active_alert_meta = None
        self.log.info("ALERT stop id=%s reason=%s", event_id, reason)

    def _alert_stop_all(self) -> None:
        self._stop_alert_sound()
        count = self.app_context.scheduler.dismiss_all()
        for event_id in list(self._event_cards.keys()):
            self._update_event_card(event_id, tr("msg_alert_stopped", self.language))
        if count:
            msg = "Все оповещения отключены."
            if (self.language or "ru").lower() == "en":
                msg = "All alerts disabled."
            self._notify(msg)
        self.log.info("ALERT stop_all count=%s", count)

    def _update_event_card(self, event_id: str, status: str) -> None:
        item = self._event_cards.get(event_id)
        if not item:
            return
        card, bubble = item
        card.set_status(status)
        card.set_alerting(False)
        bubble.set_emphasis(0.4)

    def _notify_system_event(self, event: Event, message_text: str) -> None:
        ui = self.settings.get("ui", {}) or {}
        if not bool(ui.get("system_notifications", True)):
            return
        show_text = bool(ui.get("notify_show_text", True))
        show_icon = bool(ui.get("notify_show_icon", True))
        kind = event.type
        if kind == "timer":
            title = f"{tr('app_name', self.language)} — {tr('action_timer_title', self.language)}"
        elif kind == "reminder":
            title = f"{tr('app_name', self.language)} — {tr('action_reminder_title', self.language)}"
        elif kind == "alarm":
            title = f"{tr('app_name', self.language)} — {tr('action_alarm_title', self.language)}"
        else:
            title = f"{tr('app_name', self.language)}"
        body = message_text if show_text else tr("msg_alert_hidden", self.language)
        icon_path = resource_path(Path("assets") / "icons" / "app_icon_v3_256.png") if show_icon else None
        allow_repeat = kind == "timer" and bool(ui.get("timer_restart_enabled", True))
        action_repeat_label = tr("btn_alert_repeat", self.language) if allow_repeat else None
        action_stop_label = tr("btn_alert_stop", self.language)
        action_repeat_args = f"action=repeat;id={event.id};type={kind}" if allow_repeat else None
        action_stop_args = f"action=stop;id={event.id};type={kind}"
        payload = NotificationPayload(
            title=title,
            body=body,
            icon_path=icon_path,
            action_repeat_label=action_repeat_label,
            action_stop_label=action_stop_label,
            action_repeat_args=action_repeat_args,
            action_stop_args=action_stop_args,
        )
        self.log.info("NOTIFY_START type=%s id=%s", kind, event.id)
        ok = self.notifier.notify(payload)
        if ok:
            self.log.info("NOTIFY_OK type=%s id=%s", kind, event.id)

    def _on_notification_action(self, action: str, event_id: str, event_type: str) -> None:
        def _run() -> None:
            handled = False
            if action == "stop":
                if self.app_context.scheduler.get_event(event_id) is None:
                    self.log.warning("Notification action: event not found id=%s", event_id)
                else:
                    self._alert_stop(event_id, "notification")
                    handled = True
            elif action == "repeat":
                event = self.app_context.scheduler.get_event(event_id)
                if event is None:
                    self.log.warning("Notification action: event not found id=%s", event_id)
                elif event_type == "timer":
                    self._alert_restart(event)
                    handled = True
                else:
                    default_min = int(get_alert_settings(self.settings).get("snooze_default_minutes", 5))
                    self._alert_snooze(event_id, default_min)
                    handled = True
            if handled:
                msg = "Оповещение обработано."
                if (self.language or "ru").lower() == "en":
                    msg = "Alert handled."
                self._notify(msg)
            else:
                msg = "Событие не найдено."
                if (self.language or "ru").lower() == "en":
                    msg = "Event not found."
                self._notify(msg)

        QTimer.singleShot(0, _run)

    def _animate_widget_in(self, widget: QWidget) -> None:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(260)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()

    def _play_alert_sound_from_settings(self) -> None:
        settings = get_alert_settings(self.settings)
        if not bool(settings.get("alerts_enabled", True)):
            return
        rel = str(settings.get("alerts_sound", ""))
        volume = int(settings.get("alerts_volume", 80))
        loop = bool(settings.get("alerts_loop", True))
        self._play_alert_sound(rel, volume, loop=loop, test=False)

    def _play_alert_sound(self, rel_path: str, volume: int, loop: bool, test: bool = False) -> None:
        if not rel_path:
            return
        path = resource_path(Path(rel_path))
        if not path.exists():
            self.log.warning("Alert sound not found: %s", rel_path)
            return
        self.alert_player.set_volume(volume)
        self.alert_player.play(path, loop=loop)
        if test:
            QTimer.singleShot(2000, self, self._stop_alert_sound)

    def _stop_alert_sound(self) -> None:
        try:
            self.alert_player.stop()
        except Exception as e:  # noqa: BLE001
            self.log.warning("Alert stop failed: %s", e)

    def _set_status(self, text: str) -> None:
        if text == self._last_status:
            return
        self._last_status = text
        status_map = {
            "ready": tr("status_ready", self.language),
            "speaking": tr("status_speaking", self.language),
            "thinking": tr("status_thinking", self.language),
            "listening": tr("status_listening", self.language),
            "stopped": tr("status_stopped", self.language),
            "text mode": tr("status_text_mode", self.language),
        }
        shown = status_map.get(text, text)
        prefix = tr("status_prefix", self.language)
        self.status_label.setText(f"{prefix}: {shown}")
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
        self.log.info("UI send text: len=%s", len(text))
        self._process_text(text, from_voice=False)

    def _process_text(self, text: str, from_voice: bool = False) -> None:
        if self._first_message:
            self._first_message = False
        self._cancel_voice_timeout()
        self.input.clear()
        lang = self._resolve_language_for_text(text)
        self._append_message(text, is_user=True)
        self._set_status("thinking")
        request_id: int | None = None
        if from_voice:
            self.log.info("Voice request start: len=%s", len(text))
            request_id = self._start_voice_timeout(lang)

        def _worker() -> None:
            try:
                if self.ai_mode and self.llm_client is not None:
                    append_chat(Path("data"), "user", text)
                    answer = self.llm_client.ask(text)
                    append_chat(Path("data"), "assistant", answer)
                elif self.ai_mode and self.llm_client is None:
                    answer = tr("msg_ai_unavailable_cmd", lang)
                else:
                    answer = self.dialogue.handle_text(text, language=lang)
            except Exception as e:  # noqa: BLE001
                self.log.exception("UI worker failed: %s", e)
                answer = tr("msg_error_generic", lang)

            if isinstance(answer, ActionResult):
                answer_text = answer.to_text()
            else:
                answer_text = str(answer)

            if not answer_text.strip():
                answer = tr("msg_unknown_command", lang)
                answer_text = str(answer)

            if answer == "__EXIT__":
                if request_id is not None:
                    QTimer.singleShot(0, self, lambda: self._cancel_voice_timeout(request_id))
                QTimer.singleShot(0, self, self.close)
                return

            def _update() -> None:
                if request_id is not None and request_id in self._voice_timeout_expired_ids:
                    self._voice_timeout_expired_ids.discard(request_id)
                    self.log.info("Response ignored after timeout: id=%s", request_id)
                    return
                if request_id is not None:
                    self.log.info("Response received: id=%s", request_id)
                if isinstance(answer, ActionResult) and answer.action == "clear_chat":
                    self._clear_chat_flow()
                    self._set_status("ready")
                    return
                if isinstance(answer, ActionResult):
                    self._append_action(answer)
                else:
                    self._append_message(answer_text, is_user=False)
                self._set_status("speaking")
                self._say_tts_async(answer_text, lang)
                self._set_status("ready")

            QTimer.singleShot(0, self, _update)

        threading.Thread(target=_worker, daemon=True).start()

    def _start_voice_timeout(self, lang: str) -> int:
        self._cancel_voice_timeout()
        seconds = get_voice_timeout_seconds(self.settings, default=12)
        if seconds <= 0:
            return 0
        seconds = max(5, min(30, seconds))
        self._voice_timeout_request_id += 1
        request_id = self._voice_timeout_request_id
        self._voice_timeout_expired_ids.discard(request_id)
        self._voice_timeout_active_id = request_id
        self._voice_timeout_lang = lang
        self._voice_timeout_seconds = seconds
        applied_ms = apply_timeout_ms(seconds)
        self._voice_timeout_timer.start(applied_ms)
        self.log.info(
            "Response timeout start: %ss id=%s applied_timer=%sms",
            seconds,
            request_id,
            applied_ms,
        )
        return request_id

    def _cancel_voice_timeout(self, request_id: int | None = None) -> None:
        if self._voice_timeout_active_id is None:
            return
        if request_id is not None and request_id != self._voice_timeout_active_id:
            return
        if self._voice_timeout_timer.isActive():
            self._voice_timeout_timer.stop()
        self.log.info("Response timeout canceled: id=%s", self._voice_timeout_active_id)
        self._voice_timeout_active_id = None
        self._voice_timeout_lang = None
        self._voice_timeout_seconds = None

    def _on_voice_timeout(self) -> None:
        if self._voice_timeout_active_id is None:
            return
        seconds = int(self._voice_timeout_seconds or get_voice_timeout_seconds(self.settings, default=12))
        lang = self._voice_timeout_lang or self.language
        expired_id = self._voice_timeout_active_id
        self.log.info("Response timeout reached: %ss id=%s", seconds, expired_id)
        if expired_id is not None:
            self._voice_timeout_expired_ids.add(expired_id)
        self._voice_timeout_active_id = None
        self._voice_timeout_lang = None
        self._voice_timeout_seconds = None
        self._append_message(tr("msg_voice_timeout", lang).format(seconds=seconds), is_user=False)
        self._set_status("ready")

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
        self.log.info("STT start")

        def _worker() -> None:
            try:
                text = self.stt.listen()
            except Exception as e:  # noqa: BLE001
                self.log.exception("STT listen failed: %s", e)
                text = ""
            QTimer.singleShot(0, self, lambda: self._on_listen_result(text))

        threading.Thread(target=_worker, daemon=True).start()

    def _stop_listen(self) -> None:
        self.listen_btn.set_active(False)
        self.input_mic.set_active(False)
        self.listening = False
        self._listen_interrupted = True
        try:
            self.stt.stop()
        except Exception as e:  # noqa: BLE001
            self.log.exception("STT stop failed: %s", e)
        self.log.info("STT stop")
        self.log.info("Stop pressed: cancel timers")
        self._cancel_voice_timeout()
        self._set_status("stopped")

    def _on_listen_result(self, text: Optional[str]) -> None:
        self.listening = False
        self.listen_btn.set_active(False)
        self.input_mic.set_active(False)
        self.log.info("STT result: %s", text)
        if text is None:
            self._set_status("stopped")
            return
        if text.strip():
            self._listen_interrupted = False
            self._process_text(text, from_voice=True)
        else:
            if self._listen_interrupted:
                self._listen_interrupted = False
                self._set_status("ready")
                return
            self._set_status("ready")
            self._append_message(tr("msg_speech_empty", self.language), is_user=False)

    def _toggle_listen(self) -> None:
        self.log.info("UI mic toggle: listening=%s", self.listening)
        if self.listening:
            self._stop_listen()
        else:
            self._listen()

    def _open_settings(self) -> None:
        self.log.info("UI open settings")
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("settings_title", self.language))
        dlg.setMinimumSize(640, 720)
        self.log.info("Settings window build: min_size=%s sections=5", dlg.minimumSize())

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll, stretch=1)

        container = QWidget()
        scroll.setWidget(container)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        def card(title: str) -> tuple[QVBoxLayout, QGridLayout]:
            frame = QFrame()
            frame.setObjectName("SettingsCard")
            frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(14, 12, 14, 12)
            frame_layout.setSpacing(10)
            title_lbl = QLabel(title)
            title_lbl.setObjectName("SectionTitle")
            frame_layout.addWidget(title_lbl)
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(10)
            grid.setColumnStretch(1, 1)
            frame_layout.addLayout(grid)
            container_layout.addWidget(frame)
            return frame_layout, grid

        def add_row(grid: QGridLayout, row: int, label_text: str, widget: QWidget) -> int:
            label = QLabel(label_text)
            label.setObjectName("SettingsLabel")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            grid.addWidget(label, row, 0)
            grid.addWidget(widget, row, 1)
            return row + 1

        def add_helper(card_layout: QVBoxLayout, text: str) -> None:
            helper = QLabel(text)
            helper.setObjectName("HelperText")
            helper.setWordWrap(True)
            card_layout.addWidget(helper)

        # Language & STT
        lang_card, lang_grid = card(tr("section_language", self.language))
        lang_row = 0
        lang_mode = QComboBox()
        lang_mode.addItem(tr("opt_auto", self.language), "auto")
        lang_mode.addItem(tr("opt_ru", self.language), "ru")
        lang_mode.addItem(tr("opt_en", self.language), "en")
        current_lang = self.language_mode
        idx_lang = lang_mode.findData(current_lang)
        if idx_lang >= 0:
            lang_mode.setCurrentIndex(idx_lang)
        stt_mode = QComboBox()
        stt_mode.addItem(tr("opt_auto", self.language), "auto")
        stt_mode.addItem(tr("opt_text", self.language), "text")
        stt_mode.addItem(tr("opt_vosk", self.language), "vosk")
        idx_stt = stt_mode.findData(str(self.settings.get("stt", {}).get("mode", "text")))
        if idx_stt >= 0:
            stt_mode.setCurrentIndex(idx_stt)
        show_start = QCheckBox("")
        show_start.setChecked(bool(self.settings.get("ui", {}).get("show_start_screen", True)))
        voice_timeout = QSpinBox()
        voice_timeout.setRange(5, 30)
        voice_timeout.setSuffix(f" {tr('unit_seconds', self.language)}")
        voice_timeout.setValue(get_voice_timeout_seconds(self.settings, default=12))
        lang_row = add_row(lang_grid, lang_row, tr("label_language", self.language), lang_mode)
        lang_row = add_row(lang_grid, lang_row, tr("label_stt_mode", self.language), stt_mode)
        lang_row = add_row(lang_grid, lang_row, tr("label_show_start", self.language), show_start)
        lang_row = add_row(lang_grid, lang_row, tr("label_voice_timeout", self.language), voice_timeout)
        add_helper(lang_card, tr("helper_language", self.language))

        # Microphone
        mic_card, mic_grid = card(tr("section_mic", self.language))
        mic_row = 0
        devices = list_input_devices()
        mic_combo = QComboBox()
        mic_combo.addItem(tr("label_default_device", self.language), None)
        for d in devices:
            mic_combo.addItem(d.name, d.index)
        selected_device = (self.settings.get("stt", {}) or {}).get("device")
        if selected_device is not None:
            idx = mic_combo.findData(selected_device)
            if idx >= 0:
                mic_combo.setCurrentIndex(idx)
            else:
                self.log.warning("Saved mic device not found: %s. Falling back to default.", selected_device)
                mic_combo.setCurrentIndex(0)
        mic_level = QProgressBar()
        mic_level.setRange(0, 100)
        mic_status = QLabel("")
        mic_status.setObjectName("HelperText")
        mic_row = add_row(mic_grid, mic_row, tr("label_mic_device", self.language), mic_combo)
        mic_row = add_row(mic_grid, mic_row, tr("label_mic_level", self.language), mic_level)
        mic_test_btn = QPushButton(tr("btn_test_mic", self.language))
        mic_row = add_row(mic_grid, mic_row, tr("btn_test_mic", self.language), mic_test_btn)
        mic_card.addWidget(mic_status)
        add_helper(mic_card, tr("helper_mic", self.language))

        wake_was_active = self.wake_listener is not None
        if wake_was_active:
            try:
                self.wake_listener.stop()
            except Exception:
                pass
        mic_monitor = MicLevelMonitor(device=mic_combo.currentData())
        mic_monitor.start()
        mic_timer = QTimer(dlg)

        def _update_mic_level() -> None:
            mic_monitor.restart_if_inactive()
            level = mic_monitor.get_level()
            mic_level.setValue(int(max(0.0, min(1.0, level)) * 100))
            if mic_monitor.last_error:
                mic_status.setText(f"{mic_monitor.last_error}")

        mic_timer.timeout.connect(_update_mic_level)
        mic_timer.start(80)

        def _restart_monitor() -> None:
            mic_monitor.stop()
            mic_monitor.device = mic_combo.currentData()
            mic_monitor.start()
            self.log.info("Mic device selected: %s", mic_combo.currentData())

        mic_combo.currentIndexChanged.connect(_restart_monitor)

        def _mic_test() -> None:
            device = mic_combo.currentData()
            mic_status.setText(tr("msg_mic_testing", self.language))

            def _worker() -> None:
                ok, level, err = test_microphone(device=device, duration_seconds=2.5)
                msg = tr("msg_mic_ok", self.language) if ok else tr("msg_mic_error", self.language)
                if err:
                    msg = err

                def _update() -> None:
                    mic_status.setText(msg)
                    if ok:
                        self.log.info("Mic test ok: level=%s", level)
                    else:
                        self.log.warning("Mic test error: %s", msg)

                QTimer.singleShot(0, dlg, _update)

            threading.Thread(target=_worker, daemon=True).start()

        mic_test_btn.clicked.connect(_mic_test)

        # Theme
        theme_card, theme_grid = card(tr("section_theme", self.language))
        theme_row = 0
        theme_preset = QComboBox()
        theme_preset.addItems(["Dark", "Midnight", "Neon"])
        current_theme = str(self.settings.get("ui", {}).get("theme_preset", "dark")).title()
        idx_theme = theme_preset.findText(current_theme)
        if idx_theme >= 0:
            theme_preset.setCurrentIndex(idx_theme)
        accent_input = QLineEdit(str(self.settings.get("ui", {}).get("accent_color", "#7dd3fc")))
        intensity_slider = QSlider(Qt.Horizontal)
        intensity_slider.setRange(30, 100)
        intensity_slider.setValue(int(float(self.settings.get("ui", {}).get("background_intensity", 0.7)) * 100))
        theme_row = add_row(theme_grid, theme_row, tr("label_theme_preset", self.language), theme_preset)
        theme_row = add_row(theme_grid, theme_row, tr("label_accent", self.language), accent_input)
        theme_row = add_row(theme_grid, theme_row, tr("label_bg_intensity", self.language), intensity_slider)
        add_helper(theme_card, tr("helper_theme", self.language))

        # TTS
        tts_card, tts_grid = card(tr("section_tts", self.language))
        tts_row = 0
        tts_enabled = QCheckBox("")
        tts_enabled.setChecked(bool(self.settings.get("tts", {}).get("enabled", True)))
        tts_provider = QComboBox()
        tts_provider.addItem("auto", "auto")
        tts_provider.addItem("pyttsx3", "pyttsx3")
        tts_provider.addItem("edge", "edge")
        idx_provider = tts_provider.findData(str(self.settings.get("tts", {}).get("provider", "auto")))
        if idx_provider >= 0:
            tts_provider.setCurrentIndex(idx_provider)
        tts_rate = QSlider(Qt.Horizontal)
        tts_rate.setRange(100, 240)
        tts_rate.setValue(int(self.settings.get("tts", {}).get("rate", 180)))
        tts_volume = QSlider(Qt.Horizontal)
        tts_volume.setRange(0, 100)
        tts_volume.setValue(int(float(self.settings.get("tts", {}).get("volume", 1.0)) * 100))
        tts_pitch = QSlider(Qt.Horizontal)
        tts_pitch.setRange(-20, 20)
        tts_pitch.setValue(int(self.settings.get("tts", {}).get("pitch", 0)))
        voice_ru = QComboBox()
        voice_en = QComboBox()

        def _populate_voices() -> None:
            if tts_provider.currentData() == "pyttsx3":
                voices = list_pyttsx3_voices()
            else:
                voices = list_edge_voices()
            if not voices:
                voices = ["default"]
            voice_ru.clear()
            voice_en.clear()
            voice_ru.addItems(voices)
            voice_en.addItems(voices)
            cur_ru = str(self.settings.get("tts", {}).get("voice_ru", voices[0]))
            cur_en = str(self.settings.get("tts", {}).get("voice_en", voices[0]))
            idx_ru = voice_ru.findText(cur_ru)
            idx_en = voice_en.findText(cur_en)
            if idx_ru >= 0:
                voice_ru.setCurrentIndex(idx_ru)
            if idx_en >= 0:
                voice_en.setCurrentIndex(idx_en)

        _populate_voices()
        tts_provider.currentIndexChanged.connect(_populate_voices)

        tts_test = QPushButton(tr("btn_test_tts", self.language))
        tts_test.clicked.connect(self._tts_test)

        tts_row = add_row(tts_grid, tts_row, tr("label_tts_enabled", self.language), tts_enabled)
        tts_row = add_row(tts_grid, tts_row, tr("label_tts_provider", self.language), tts_provider)
        tts_row = add_row(tts_grid, tts_row, tr("label_tts_rate", self.language), tts_rate)
        tts_row = add_row(tts_grid, tts_row, tr("label_tts_volume", self.language), tts_volume)
        tts_row = add_row(tts_grid, tts_row, tr("label_tts_pitch", self.language), tts_pitch)
        tts_row = add_row(tts_grid, tts_row, tr("label_voice_ru", self.language), voice_ru)
        tts_row = add_row(tts_grid, tts_row, tr("label_voice_en", self.language), voice_en)
        tts_row = add_row(tts_grid, tts_row, tr("btn_test_tts", self.language), tts_test)
        add_helper(tts_card, tr("helper_tts", self.language))

        # Alerts
        alerts_card, alerts_grid = card(tr("section_alerts", self.language))
        alerts_row = 0
        alert_settings = get_alert_settings(self.settings)
        alerts_enabled = QCheckBox("")
        alerts_enabled.setChecked(bool(alert_settings.get("alerts_enabled", True)))
        alerts_loop = QCheckBox("")
        alerts_loop.setChecked(bool(alert_settings.get("alerts_loop", True)))
        alerts_sound = QComboBox()
        sounds = list_alert_sounds()
        if not sounds:
            alerts_sound.addItem("default", "")
        else:
            for s in sounds:
                alerts_sound.addItem(s.label, s.rel)
        current_sound = str(alert_settings.get("alerts_sound", ""))
        idx_sound = alerts_sound.findData(current_sound)
        if idx_sound >= 0:
            alerts_sound.setCurrentIndex(idx_sound)
        alerts_volume = QSlider(Qt.Horizontal)
        alerts_volume.setRange(0, 100)
        alerts_volume.setValue(int(alert_settings.get("alerts_volume", 80)))
        alerts_test = QPushButton(tr("btn_test_alert", self.language))

        def _test_alert() -> None:
            self._play_alert_sound(
                str(alerts_sound.currentData() or ""),
                alerts_volume.value(),
                loop=alerts_loop.isChecked(),
                test=True,
            )

        alerts_test.clicked.connect(_test_alert)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_enabled", self.language), alerts_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_sound", self.language), alerts_sound)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_volume", self.language), alerts_volume)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_loop", self.language), alerts_loop)
        alerts_row = add_row(alerts_grid, alerts_row, tr("btn_test_alert", self.language), alerts_test)

        notify_enabled = QCheckBox("")
        notify_enabled.setChecked(bool(alert_settings.get("system_notifications", True)))
        notify_show_text = QCheckBox("")
        notify_show_text.setChecked(bool(alert_settings.get("notify_show_text", True)))
        notify_show_icon = QCheckBox("")
        notify_show_icon.setChecked(bool(alert_settings.get("notify_show_icon", True)))
        notify_test = QPushButton(tr("btn_test_notify", self.language))

        def _test_notify() -> None:
            event = Event(type="timer", due_time=datetime.now(), payload={"message": "test"})
            msg = tr("msg_timer_done", self.language).format(duration="5 минут")
            self._notify_system_event(event, msg)

        notify_test.clicked.connect(_test_notify)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_system_notifications", self.language), notify_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_notify_text", self.language), notify_show_text)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_notify_icon", self.language), notify_show_icon)
        alerts_row = add_row(alerts_grid, alerts_row, tr("btn_test_notify", self.language), notify_test)

        snooze_default = QSpinBox()
        snooze_default.setRange(1, 30)
        snooze_default.setValue(int(alert_settings.get("snooze_default_minutes", 5)))
        snooze_quick_enabled = QCheckBox("")
        snooze_quick_enabled.setChecked(bool(alert_settings.get("snooze_quick_enabled", True)))
        snooze_dropdown_enabled = QCheckBox("")
        snooze_dropdown_enabled.setChecked(bool(alert_settings.get("snooze_dropdown_enabled", True)))
        timer_restart_enabled = QCheckBox("")
        timer_restart_enabled.setChecked(bool(alert_settings.get("timer_restart_enabled", True)))

        quick_row = QHBoxLayout()
        quick_checks: dict[int, QCheckBox] = {}
        for minutes in [1, 3, 5, 10, 15]:
            cb = QCheckBox(f"+{minutes}")
            cb.setChecked(minutes in alert_settings.get("snooze_quick_buttons", []))
            quick_checks[minutes] = cb
            quick_row.addWidget(cb)
        quick_widget = QWidget()
        quick_widget.setLayout(quick_row)

        dropdown_row = QHBoxLayout()
        dropdown_checks: dict[int, QCheckBox] = {}
        for minutes in [1, 3, 5, 10, 15, 30]:
            cb = QCheckBox(str(minutes))
            cb.setChecked(minutes in alert_settings.get("snooze_dropdown_options", []))
            dropdown_checks[minutes] = cb
            dropdown_row.addWidget(cb)
        dropdown_widget = QWidget()
        dropdown_widget.setLayout(dropdown_row)

        alerts_row = add_row(alerts_grid, alerts_row, tr("label_snooze_default", self.language), snooze_default)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_snooze_quick", self.language), snooze_quick_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_snooze_quick_set", self.language), quick_widget)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_snooze_dropdown", self.language), snooze_dropdown_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_snooze_dropdown_set", self.language), dropdown_widget)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_timer_restart", self.language), timer_restart_enabled)

        # Wake word
        wake_card, wake_grid = card(tr("section_wake", self.language))
        wake_row = 0
        wake_word = QCheckBox("")
        wake_word.setChecked(bool(self.settings.get("ui", {}).get("wake_word", False)))
        wake_row = add_row(wake_grid, wake_row, tr("label_wake_word", self.language), wake_word)
        add_helper(wake_card, tr("helper_wake", self.language))

        save_row = QHBoxLayout()
        save_btn = QPushButton(tr("btn_save", self.language))
        save_state = QLabel("")
        save_state.setObjectName("HelperText")
        save_row.addStretch(1)
        save_row.addWidget(save_state)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        def _save() -> None:
            self._save_settings(
                dlg,
                lang_mode.currentData(),
                stt_mode.currentData(),
                mic_combo.currentData(),
                tts_enabled.isChecked(),
                str(tts_provider.currentData()),
                tts_rate.value(),
                tts_volume.value(),
                tts_pitch.value(),
                voice_ru.currentText(),
                voice_en.currentText(),
                wake_word.isChecked(),
                alerts_enabled.isChecked(),
                str(alerts_sound.currentData() or ""),
                alerts_volume.value(),
                alerts_loop.isChecked(),
                snooze_default.value(),
                snooze_quick_enabled.isChecked(),
                [m for m, cb in quick_checks.items() if cb.isChecked()],
                snooze_dropdown_enabled.isChecked(),
                [m for m, cb in dropdown_checks.items() if cb.isChecked()],
                timer_restart_enabled.isChecked(),
                notify_enabled.isChecked(),
                notify_show_text.isChecked(),
                notify_show_icon.isChecked(),
                theme_preset.currentText(),
                accent_input.text().strip(),
                intensity_slider.value(),
                show_start.isChecked(),
                voice_timeout.value(),
            )
            save_state.setText(tr("settings_saved", self.language))
            QTimer.singleShot(1200, dlg, lambda: save_state.setText(""))

        save_btn.clicked.connect(_save)

        def _cleanup() -> None:
            mic_timer.stop()
            mic_monitor.stop()
            if wake_was_active and bool(self.settings.get("ui", {}).get("wake_word", False)):
                try:
                    self._init_wake_word()
                except Exception as e:  # noqa: BLE001
                    self.log.exception("Wake word restart failed: %s", e)

        dlg.finished.connect(_cleanup)
        dlg.exec()

    def _tts_test(self) -> None:
        self._set_status("speaking")
        self._say_tts_async(tr("msg_tts_test_phrase", self.language), self.language)
        self._set_status("ready")

    def _save_settings(
        self,
        dlg: QDialog,
        lang_mode_text: str,
        stt_mode: str,
        mic_device: int | None,
        tts_enabled: bool,
        tts_provider: str,
        tts_rate: int,
        tts_volume: int,
        tts_pitch: int,
        voice_ru: str,
        voice_en: str,
        wake_word: bool,
        alerts_enabled: bool,
        alerts_sound: str,
        alerts_volume: int,
        alerts_loop: bool,
        snooze_default_minutes: int,
        snooze_quick_enabled: bool,
        snooze_quick_buttons: list[int],
        snooze_dropdown_enabled: bool,
        snooze_dropdown_options: list[int],
        timer_restart_enabled: bool,
        notify_enabled: bool,
        notify_show_text: bool,
        notify_show_icon: bool,
        theme_preset: str,
        accent_color: str,
        intensity_value: int,
        show_start: bool,
        voice_timeout: int,
    ) -> None:
        lang_mode = (lang_mode_text or "auto").lower()
        self.settings.setdefault("app", {})["language"] = lang_mode
        self.settings.setdefault("stt", {})["mode"] = stt_mode
        self.settings.setdefault("stt", {})["device"] = mic_device
        self.settings.setdefault("stt", {})["language"] = lang_mode
        self.settings.setdefault("tts", {})["enabled"] = bool(tts_enabled)
        self.settings.setdefault("tts", {})["provider"] = tts_provider
        self.settings.setdefault("tts", {})["rate"] = int(tts_rate)
        self.settings.setdefault("tts", {})["volume"] = float(tts_volume) / 100.0
        self.settings.setdefault("tts", {})["pitch"] = int(tts_pitch)
        self.settings.setdefault("tts", {})["voice_ru"] = voice_ru
        self.settings.setdefault("tts", {})["voice_en"] = voice_en
        self.settings.setdefault("tts", {})["voice_name_contains_ru"] = voice_ru
        self.settings.setdefault("tts", {})["voice_name_contains_en"] = voice_en
        self.settings.setdefault("ui", {})["wake_word"] = bool(wake_word)
        self.settings.setdefault("ui", {})["alerts_enabled"] = bool(alerts_enabled)
        self.settings.setdefault("ui", {})["alerts_sound"] = str(alerts_sound or "")
        self.settings.setdefault("ui", {})["alerts_volume"] = int(alerts_volume)
        self.settings.setdefault("ui", {})["alerts_loop"] = bool(alerts_loop)
        self.settings.setdefault("ui", {})["snooze_default_minutes"] = int(snooze_default_minutes)
        self.settings.setdefault("ui", {})["snooze_quick_enabled"] = bool(snooze_quick_enabled)
        self.settings.setdefault("ui", {})["snooze_quick_buttons"] = list(snooze_quick_buttons)
        self.settings.setdefault("ui", {})["snooze_dropdown_enabled"] = bool(snooze_dropdown_enabled)
        self.settings.setdefault("ui", {})["snooze_dropdown_options"] = list(snooze_dropdown_options)
        self.settings.setdefault("ui", {})["timer_restart_enabled"] = bool(timer_restart_enabled)
        self.settings.setdefault("ui", {})["system_notifications"] = bool(notify_enabled)
        self.settings.setdefault("ui", {})["notify_show_text"] = bool(notify_show_text)
        self.settings.setdefault("ui", {})["notify_show_icon"] = bool(notify_show_icon)
        self.settings.setdefault("ui", {})["theme_preset"] = theme_preset.lower()
        self.settings.setdefault("ui", {})["accent_color"] = accent_color
        self.settings.setdefault("ui", {})["background_intensity"] = float(intensity_value) / 100.0
        self.settings.setdefault("ui", {})["show_start_screen"] = bool(show_start)
        self.settings.setdefault("ui", {})["voice_response_timeout_sec"] = int(voice_timeout)
        self.settings.setdefault("ui", {}).pop("voice_response_timeout", None)
        applied_ms = apply_timeout_ms(int(voice_timeout))
        self.log.info(
            "Timeout setting: ui=%ss stored=%ss applied_timer=%sms",
            voice_timeout,
            self.settings.get("ui", {}).get("voice_response_timeout_sec"),
            applied_ms,
        )
        save_settings(self.settings)
        self.log.info("Language selected: %s", lang_mode)
        self.log.info("Mic device saved: %s", mic_device)
        self._on_settings_changed(self.settings)

    def _open_history(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("title_history", self.language))
        dlg.setMinimumSize(560, 420)
        layout = QVBoxLayout(dlg)
        history = read_json(Path("data") / "history.json", default=[])
        box = QTextEdit()
        box.setReadOnly(True)
        for item in history:
            role = item.get("role", "")
            text = item.get("text", "")
            ts = item.get("ts", "")
            role_map = {
                "user": tr("role_user", self.language),
                "assistant": tr("role_assistant", self.language),
            }
            box.append(f"[{ts}] {role_map.get(role, role)}: {text}")
        layout.addWidget(box)
        dlg.exec()

    def _open_volume(self) -> None:
        if self.app_context.volume is None:
            self._notify(tr("msg_volume_unavailable", self.language))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("title_volume", self.language))
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
            self._notify(tr("msg_ai_unavailable", self.language))
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
        except Exception as e:  # noqa: BLE001
            self.log.debug("Sync AI button failed: %s", e)

    def _say_startup(self) -> None:
        self._say_tts_async(tr("msg_startup", self.language), self.language)

    def _say_tts_async(self, text: str, lang: str) -> None:
        def _start() -> None:
            self.log.info("TTS enqueue: len=%s lang=%s", len(text or ""), lang)
            if not self.settings.get("tts", {}).get("enabled", True):
                if not self._tts_warned:
                    self._append_message(tr("msg_tts_disabled", self.language), is_user=False)
                    self._tts_warned = True
                return
            if not self.tts_worker.is_available():
                if not self._tts_warned:
                    self._append_message(tr("msg_tts_unavailable", self.language), is_user=False)
                    self._tts_warned = True
                return
            self.tts_worker.say(text, lang=lang)

        QTimer.singleShot(0, self, _start)

    def _apply_stt_mode_ui(self) -> None:
        if isinstance(self.stt, TextSTT):
            self.listen_btn.setEnabled(False)
            self.input_mic.setEnabled(False)
        else:
            self.listen_btn.setEnabled(True)
            self.input_mic.setEnabled(True)

    def _init_wake_word(self) -> None:
        if self.wake_listener is not None:
            try:
                self.wake_listener.stop()
            except Exception as e:  # noqa: BLE001
                self.log.exception("Wake word stop failed: %s", e)
            self.wake_listener = None
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
            self.settings.setdefault("ui", {})["wake_word"] = False
            save_settings(self.settings)
            msg = tr("msg_wake_unavailable", self.language)
            if isinstance(e, (FileNotFoundError, RuntimeError)):
                msg = "Модель распознавания речи не найдена. Установите модели Vosk."
                if (self.language or "ru").lower() == "en":
                    msg = "Speech model not found. Install Vosk models."
            self._notify(msg)

    def _handle_wake(self, phrase: str | None = None) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._set_status("listening")
        self._say_tts_async(tr("msg_listening", self.language), self.language)
        self._listen()

    def _self_check(self) -> None:
        self.log.info("Debug self-check start")
        try:
            settings_path = Path("config") / "settings.json"
            self.log.info("Settings file exists=%s", settings_path.exists())
            env_path = Path(".env")
            self.log.info(".env exists=%s", env_path.exists())
            self.log.info("Language mode=%s language=%s", self.language_mode, self.language)
            stt_mode = (self.settings.get("stt", {}) or {}).get("mode")
            self.log.info("STT mode=%s type=%s", stt_mode, type(self.stt).__name__)
            tts_provider = (self.settings.get("tts", {}) or {}).get("provider")
            self.log.info("TTS provider=%s available=%s", tts_provider, self.tts_worker.is_available())
            llm_provider = (self.settings.get("llm", {}) or {}).get("provider")
            self.log.info("LLM provider=%s enabled=%s", llm_provider, self.llm_client is not None)
            devices = list_input_devices()
            self.log.info("Mic devices=%s", len(devices))
            self.log.info("UI handlers: send=%s mic=%s", bool(self.input), bool(self.listen_btn))
        except Exception as e:  # noqa: BLE001
            self.log.exception("Self-check failed: %s", e)


def _parse_notification_args(arg: str) -> tuple[str, str, str] | None:
    if not arg:
        return None
    parts = dict(item.split("=", 1) for item in arg.split(";") if "=" in item)
    action = parts.get("action", "")
    event_id = parts.get("id", "")
    event_type = parts.get("type", "")
    if not action or not event_id or not event_type:
        return None
    return action, event_id, event_type


def run(activation_args: str | None = None) -> None:
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    window = AntoshkaWindow()
    if activation_args:
        parsed = _parse_notification_args(activation_args)
        if parsed:
            action, event_id, event_type = parsed
            QTimer.singleShot(
                0, lambda: window._on_notification_action(action, event_id, event_type)
            )
    window.show()
    sys.exit(app.exec())
