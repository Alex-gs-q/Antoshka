from __future__ import annotations

import math
import sys
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt,
    QPoint,
    QRect,
    QSize,
    QTimer,
    QUrl,
    QEasingCurve,
    QPropertyAnimation,
    QParallelAnimationGroup,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QGuiApplication,
    QPalette,
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
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QListWidget,
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
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QSystemTrayIcon,
    QStyle,
)

from core.actions import ActionResult
from core.app_context import AppContext
from core.config import load_settings, save_settings
from core.dialogue import Dialogue, DialogueConfig
from core.language import normalize_language_mode, resolve_language
from core.i18n import (
    t as tr,
    examples as sample_examples,
    command_name,
    command_desc,
    check_i18n_integrity,
    about_capabilities,
    about_examples,
)
from core.suggestions import pick_suggestions
from core.version import __version__
from core.logger import setup_logger
from core.resources import resource_path
from core.paths import data_dir, logs_dir
from core.stt import TextSTT, create_stt
from core.wake_word import WakeWordListener, WakeWordConfig
from llm.client import LLMClient, LLMConfig
from services.chat_history import append_chat, clear_chat_history
from services.scheduler import Scheduler
from services.storage import read_json
from services.history import clear_history
from services.volume import VolumeController
from services.time_parse import parse_time_of_day
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
            action_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
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
        debug_overlay: bool = False,
    ):
        super().__init__()
        self.setObjectName("EventCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setProperty("alert", True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.style().unpolish(self)
        self.style().polish(self)
        self._debug_overlay = debug_overlay
        self._buttons_widget = buttons_row
        self._pulse_anim: QPropertyAnimation | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        header = QFrame()
        header.setObjectName("AlertHeader")
        header.setAttribute(Qt.WA_StyledBackground, True)
        header.setAutoFillBackground(True)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(6, 3, 6, 3)
        header_layout.setSpacing(4)
        header_label = QLabel("ALERT")
        header_label.setObjectName("AlertHeaderText")
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)
        layout.addWidget(header)

        if self._debug_overlay:
            dbg = QLabel("DEBUG")
            dbg.setObjectName("AlertDebugBadge")
            layout.addWidget(dbg)

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

        buttons_row.setAttribute(Qt.WA_StyledBackground, True)
        buttons_row.setAutoFillBackground(True)
        buttons_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addWidget(buttons_row)

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0)
        self.setGraphicsEffect(effect)
        self.setMinimumHeight(0)
        self._apply_alert_style()

    def _apply_alert_style(self) -> None:
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#0B1220"))
        pal.setColor(QPalette.WindowText, QColor("#EAF1FF"))
        self.setPalette(pal)
        self.setStyleSheet(
            """
            #EventCard {
                background: #0B1220;
                border: 2px solid #4CC9FF;
                border-radius: 12px;
            }
            #AlertHeader {
                background: #4CC9FF;
                border-radius: 8px;
            }
            #AlertHeaderText { color: #0B1220; font-weight: 800; }
            #EventTitle { color: #EAF1FF; }
            #EventSubtitle { color: #EAF1FF; }
            #EventWhen { color: #BBD0F5; }
            #EventStatus { color: #7CD7FF; }
            #AlertDebugBadge { color: #FF4D4D; font-size: 10px; font-weight: 700; }
            #EventButtons {
                background: #0F213A;
                border: 2px solid #7CD7FF;
                border-radius: 12px;
            }
            #EventButtons[debug="true"] { border: 2px solid #FF4D4D; }
            #EventCard QPushButton {
                background: #173153;
                border: 2px solid #7CD7FF;
                border-radius: 8px;
                padding: 6px 10px;
                color: #EAF1FF;
            }
            #EventCard QPushButton:hover { border-color: #9BE6FF; background: #1E3B63; }
            #EventCard QPushButton:pressed { background: #0E1A2B; }
            #EventCard QPushButton:disabled {
                background: #2A2A2A; border-color: #555555; color: #999999;
            }
            """
        )

    def set_status(self, text: str) -> None:
        self._status.setText(text)
        if text:
            self._status.show()
            if self._buttons_widget is not None:
                self._buttons_widget.hide()
        else:
            self._status.hide()
            if self._buttons_widget is not None:
                self._buttons_widget.show()
        self.adjustSize()

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

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._debug_overlay:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#ff4d4d"), 1.2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        if self._buttons_widget is not None:
            rect = self._buttons_widget.geometry()
            painter.drawRect(rect.adjusted(1, 1, -2, -2))


class WrapGridWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._items: list[QWidget] = []
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._items.clear()

    def add_widget(self, widget: QWidget) -> None:
        self._items.append(widget)
        self._layout.addWidget(widget, 0, max(0, self._layout.count()))
        self._relayout()

    def set_spacing(self, value: int) -> None:
        self._layout.setSpacing(int(value))
        self._relayout()

    def _relayout(self) -> None:
        if not self._items:
            return
        for idx in reversed(range(self._layout.count())):
            item = self._layout.itemAt(idx)
            if item is not None:
                self._layout.removeItem(item)
        spacing = max(0, int(self._layout.spacing()))
        max_width = max(1, max(widget.sizeHint().width() for widget in self._items))
        available = max(1, int(self.width()))
        columns = max(1, (available + spacing) // (max_width + spacing))
        row = 0
        col = 0
        for widget in self._items:
            self._layout.addWidget(widget, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()


class HelpChipButton(QPushButton):
    def __init__(self, text: str, on_insert, on_send) -> None:
        super().__init__(text)
        self._on_insert = on_insert
        self._on_send = on_send
        self.setObjectName("HelpChip")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: self._on_insert(text))

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._on_send(self.text())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class SuggestionChipButton(QPushButton):
    def __init__(self, text: str, on_insert, on_send, on_log) -> None:
        super().__init__(text)
        self._on_insert = on_insert
        self._on_send = on_send
        self._on_log = on_log
        self._send_on_click = False
        self._tip_insert = ""
        self._tip_send = ""
        self.setObjectName("SuggestionChip")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._handle_click)

    def set_send_on_click(self, value: bool) -> None:
        self._send_on_click = bool(value)
        self._update_tooltip()

    def set_tooltips(self, insert_tip: str, send_tip: str) -> None:
        self._tip_insert = insert_tip or ""
        self._tip_send = send_tip or ""
        self._update_tooltip()

    def _update_tooltip(self) -> None:
        tip = self._tip_send if self._send_on_click else self._tip_insert
        self.setToolTip(tip)

    def _handle_click(self) -> None:
        mode = "send" if self._send_on_click else "insert"
        if self._on_log is not None:
            self._on_log(self.text(), mode)
        if self._send_on_click:
            self._on_send(self.text())
        else:
            self._on_insert(self.text())

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            if self._on_log is not None:
                self._on_log(self.text(), "send")
            self._on_send(self.text())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class SuggestionChipsWidget(QFrame):
    def __init__(self, on_insert, on_send, on_log) -> None:
        super().__init__()
        self.setObjectName("SuggestionsBar")
        self._on_insert = on_insert
        self._on_send = on_send
        self._on_log = on_log
        self._chips: list[SuggestionChipButton] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        self._wrap = WrapGridWidget()
        self._wrap.setObjectName("SuggestionWrap")
        self._wrap.set_spacing(8)
        layout.addWidget(self._wrap)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        fm = self.fontMetrics()
        row_h = fm.height() + 14
        self.setMinimumHeight(row_h + 10)
        self.setMaximumHeight(row_h * 2 + 20)

    def set_suggestions(
        self,
        items: list[str],
        send_on_click: bool,
        tip_insert: str,
        tip_send: str,
    ) -> None:
        self._wrap.clear()
        self._chips.clear()
        for text in items[:5]:
            btn = SuggestionChipButton(text, self._on_insert, self._on_send, self._on_log)
            btn.set_send_on_click(send_on_click)
            btn.set_tooltips(tip_insert, tip_send)
            self._chips.append(btn)
            self._wrap.add_widget(btn)
        self._wrap.updateGeometry()
        self.adjustSize()


class HelpSectionWidget(QFrame):
    def __init__(self, title: str, desc: str, icon: str, examples: list[str], on_insert, on_send) -> None:
        super().__init__()
        self.setObjectName("HelpSection")
        self._title = title
        self._desc = desc
        self._examples = examples
        self._chips: list[HelpChipButton] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        icon_lbl = QLabel(icon or "")
        icon_lbl.setObjectName("HelpSectionIcon")
        title_lbl = QLabel(title)
        title_lbl.setObjectName("HelpSectionTitle")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch(1)
        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("HelpSectionDesc")
        desc_lbl.setWordWrap(True)
        layout.addLayout(title_row)
        layout.addWidget(desc_lbl)
        chips = WrapGridWidget()
        chips.setObjectName("HelpChips")
        chips.set_spacing(6)
        for ex in examples:
            btn = HelpChipButton(ex, on_insert, on_send)
            self._chips.append(btn)
            chips.add_widget(btn)
        layout.addWidget(chips)

    def apply_filter(self, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            for chip in self._chips:
                chip.show()
            self.show()
            return True
        hay = f"{self._title} {self._desc}".lower()
        title_match = q in hay
        any_chip = False
        for chip in self._chips:
            match = q in chip.text().lower()
            chip.setVisible(title_match or match)
            if title_match or match:
                any_chip = True
        self.setVisible(any_chip or title_match)
        return any_chip or title_match


class HelpWidget(QWidget):
    def __init__(self, sections: list[dict], lang: str, on_insert, on_send) -> None:
        super().__init__()
        self.setObjectName("HelpCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName("HelpSearch")
        self.search.setPlaceholderText(tr("help_search", lang))
        self.execute_btn = QPushButton(tr("help_execute", lang))
        self.execute_btn.setObjectName("HelpExecute")
        search_row.addWidget(self.search, stretch=1)
        search_row.addWidget(self.execute_btn)
        layout.addLayout(search_row)
        self.sections_box = QVBoxLayout()
        self.sections_box.setSpacing(10)
        self._sections: list[HelpSectionWidget] = []
        for sec in sections:
            widget = HelpSectionWidget(
                str(sec.get("title", "")),
                str(sec.get("desc", "")),
                str(sec.get("icon", "")),
                list(sec.get("examples", [])),
                on_insert,
                on_send,
            )
            self._sections.append(widget)
            layout.addWidget(widget)
        layout.addStretch(1)
        self.search.textChanged.connect(self._on_search)
        self.search.returnPressed.connect(lambda: on_send(self.search.text().strip()))
        self.execute_btn.clicked.connect(lambda: on_send(self.search.text().strip()))

    def set_language(self, lang: str) -> None:
        self.search.setPlaceholderText(tr("help_search", lang))

    def _on_search(self, text: str) -> None:
        for sec in self._sections:
            sec.apply_filter(text)


class HelpCommandCard(QFrame):
    def __init__(self, item: dict, lang: str, on_insert, on_send) -> None:
        super().__init__()
        self.setObjectName("HelpCommandCard")
        self._lang = lang
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel(str(item.get("title", "")))
        title.setObjectName("HelpCommandTitle")
        layout.addWidget(title)

        desc = QLabel(str(item.get("desc", "")))
        desc.setObjectName("HelpCommandDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        examples = list(item.get("examples", []))[:2]
        for ex in examples:
            row = QHBoxLayout()
            row.setSpacing(8)
            label = QLabel(str(ex))
            label.setObjectName("HelpExampleText")
            label.setWordWrap(True)
            row.addWidget(label, stretch=1)

            insert_btn = QPushButton(tr("help_insert", lang))
            insert_btn.setObjectName("HelpExampleInsert")
            insert_btn.clicked.connect(lambda _, text=ex: on_insert(text))
            row.addWidget(insert_btn)

            run_btn = QPushButton(tr("help_execute", lang))
            run_btn.setObjectName("HelpExampleRun")
            run_btn.clicked.connect(lambda _, text=ex: on_send(text))
            row.addWidget(run_btn)

            layout.addLayout(row)


class HelpOverlay(QDialog):
    def __init__(self, parent: QWidget, items: list[dict], lang: str, on_insert, on_send) -> None:
        super().__init__(parent)
        self.setObjectName("HelpOverlay")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._items = list(items)
        self._lang = lang
        self._on_insert = on_insert
        self._on_send = on_send
        self._active_category = "all"
        self._cards: list[HelpCommandCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.backdrop = QFrame(self)
        self.backdrop.setObjectName("HelpBackdrop")
        root.addWidget(self.backdrop)

        backdrop_layout = QVBoxLayout(self.backdrop)
        backdrop_layout.setContentsMargins(24, 24, 24, 24)
        backdrop_layout.setAlignment(Qt.AlignCenter)

        self.panel = QFrame(self.backdrop)
        self.panel.setObjectName("HelpPanel")
        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.panel.setGraphicsEffect(shadow)
        backdrop_layout.addWidget(self.panel, alignment=Qt.AlignCenter)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 18, 20, 18)
        panel_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.title_lbl = QLabel(tr("help_title", lang))
        self.title_lbl.setObjectName("HelpTitle")
        header.addWidget(self.title_lbl)
        header.addStretch(1)
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("HelpClose")
        self.close_btn.clicked.connect(self.close)
        header.addWidget(self.close_btn)
        panel_layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setObjectName("HelpSearch")
        self.search.setPlaceholderText(tr("help_search", lang))
        self.search.textChanged.connect(self._apply_filters)
        panel_layout.addWidget(self.search)

        self.category_row = QHBoxLayout()
        self.category_row.setSpacing(8)
        panel_layout.addLayout(self.category_row)
        self._category_buttons: dict[str, QPushButton] = {}
        self._build_categories()

        self.scroll = QScrollArea()
        self.scroll.setObjectName("HelpScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        panel_layout.addWidget(self.scroll, stretch=1)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.scroll.setWidget(self.grid_host)

        self._apply_filters()

    def set_language(self, lang: str, items: list[dict]) -> None:
        self._lang = lang
        self._items = list(items)
        self.title_lbl.setText(tr("help_title", lang))
        self.search.setPlaceholderText(tr("help_search", lang))
        for cid, btn in self._category_buttons.items():
            btn.setText(self._category_label(cid, lang))
        self._apply_filters()

    def _category_label(self, cid: str, lang: str) -> str:
        key = {
            "all": "help_category_all",
            "time": "help_category_time",
            "timer": "help_category_timer",
            "alarm": "help_category_alarm",
            "reminder": "help_category_reminder",
            "notes": "help_category_notes",
            "sites": "help_category_sites",
            "system": "help_category_system",
            "ai": "help_category_ai",
        }.get(cid, "help_category_all")
        return tr(key, lang)

    def _build_categories(self) -> None:
        for cid in ("all", "time", "timer", "alarm", "reminder", "notes", "sites", "system", "ai"):
            btn = QPushButton(self._category_label(cid, self._lang))
            btn.setObjectName("HelpCategoryChip")
            btn.setCheckable(True)
            btn.setChecked(cid == "all")
            btn.clicked.connect(lambda _, c=cid: self._select_category(c))
            self._category_buttons[cid] = btn
            self.category_row.addWidget(btn)
        self.category_row.addStretch(1)

    def _select_category(self, cid: str) -> None:
        self._active_category = cid
        for key, btn in self._category_buttons.items():
            btn.setChecked(key == cid)
        self._apply_filters()

    def _apply_filters(self) -> None:
        query = (self.search.text() or "").strip().lower()
        filtered = []
        for item in self._items:
            if self._active_category != "all" and item.get("category") != self._active_category:
                continue
            if query:
                hay = " ".join(
                    [
                        str(item.get("title", "")),
                        str(item.get("desc", "")),
                        " ".join(item.get("examples", [])),
                    ]
                ).lower()
                if query not in hay:
                    continue
            filtered.append(item)
        self._rebuild_cards(filtered)

    def _rebuild_cards(self, items: list[dict]) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._cards = [HelpCommandCard(item, self._lang, self._on_insert, self._on_send) for item in items]
        self._layout_cards()

    def _layout_cards(self) -> None:
        width = self.scroll.viewport().width() or self.panel.width()
        columns = 2 if width < 900 else 3
        for idx, card in enumerate(self._cards):
            row = idx // columns
            col = idx % columns
            self.grid.addWidget(card, row, col)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._layout_cards()

    def showEvent(self, event) -> None:  # noqa: N802
        parent = self.parentWidget()
        if parent is not None:
            self.resize(parent.size())
            self.move(parent.mapToGlobal(QPoint(0, 0)))
        super().showEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self.panel.geometry().contains(event.pos()):
            self.close()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

class InAppToast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("InAppToast")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._fade_anim: QPropertyAnimation | None = None

        layout = QVBoxLayout(self)
        margin = max(8, int(self.fontMetrics().height() * 0.6))
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(max(4, int(self.fontMetrics().height() * 0.25)))

        self.title = QLabel("")
        self.title.setObjectName("InAppToastTitle")
        self.body = QLabel("")
        self.body.setObjectName("InAppToastBody")
        self.body.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        self.hide()

    def show_message(self, title: str, body: str, duration_ms: int = 4200) -> None:
        self.title.setText(title)
        self.body.setText(body)
        self.adjustSize()
        self.show()
        self.raise_()
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        if self._fade_anim is not None:
            self._fade_anim.stop()
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._fade_anim = anim
        self._hide_timer.start(max(1200, int(duration_ms)))


class AlertPopup(QDialog):
    def __init__(self, parent: QWidget | None, title: str, body: str, actions: list[QPushButton]) -> None:
        super().__init__(parent)
        self.setObjectName("AlertPopup")
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setModal(False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_pos: QPoint | None = None
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.timeout.connect(self.close)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("AlertPopupTitle")
        body_lbl = QLabel(body)
        body_lbl.setObjectName("AlertPopupBody")
        body_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        layout.addWidget(body_lbl)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        for btn in actions:
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)
        self.setStyleSheet(
            """
            #AlertPopup { background: #0B1220; border: 2px solid #4CC9FF; border-radius: 12px; }
            #AlertPopupTitle { color: #EAF1FF; font-weight: 800; font-size: 13px; }
            #AlertPopupBody { color: #BBD0F5; font-size: 12px; }
            """
        )


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, lang: str, tech_info: dict[str, str]) -> None:
        super().__init__(parent)
        self.setObjectName("AboutDialog")
        self.setWindowTitle(tr("btn_about", lang))
        self.setMinimumSize(640, 520)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(tr("about_title", lang))
        title.setObjectName("AboutTitle")
        subtitle = QLabel(tr("about_subtitle", lang))
        subtitle.setObjectName("AboutSubtitle")
        subtitle.setWordWrap(True)
        version = QLabel(f"v{__version__}")
        version.setObjectName("AboutVersion")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll, stretch=1)

        container = QWidget()
        scroll.setWidget(container)
        body = QVBoxLayout(container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        idea_card = self._card(tr("about_section_idea", lang))
        idea_text = QLabel(self._idea_text(lang))
        idea_text.setWordWrap(True)
        idea_text.setObjectName("AboutText")
        idea_card.layout().addWidget(idea_text)
        body.addWidget(idea_card)

        caps_card = self._card(tr("about_section_features", lang))
        for sec in about_capabilities(lang):
            block = QFrame()
            block.setObjectName("AboutBlock")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(8, 6, 8, 6)
            block_layout.setSpacing(4)
            title_row = QHBoxLayout()
            title_row.setSpacing(6)
            icon_lbl = QLabel(str(sec.get("icon", "")))
            icon_lbl.setObjectName("AboutIcon")
            ttl = QLabel(str(sec.get("title", "")))
            ttl.setObjectName("AboutBlockTitle")
            title_row.addWidget(icon_lbl)
            title_row.addWidget(ttl)
            title_row.addStretch(1)
            block_layout.addLayout(title_row)
            for feat in sec.get("features", []):
                line = QLabel(f"• {feat}")
                line.setObjectName("AboutBullet")
                block_layout.addWidget(line)
            caps_card.layout().addWidget(block)
        body.addWidget(caps_card)

        ex_card = self._card(tr("about_section_examples", lang))
        chips = WrapGridWidget()
        chips.setObjectName("AboutChips")
        chips.set_spacing(6)
        for ex in about_examples(lang):
            chip = QLabel(ex)
            chip.setObjectName("AboutChip")
            chips.add_widget(chip)
        ex_card.layout().addWidget(chips)
        body.addWidget(ex_card)

        tech_card = self._card(tr("about_section_tech", lang))
        for key, value in tech_info.items():
            row = QLabel(f"{key}: {value}")
            row.setObjectName("AboutTechRow")
            tech_card.layout().addWidget(row)
        body.addWidget(tech_card)
        body.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.copy_btn = QPushButton(tr("about_copy", lang))
        self.copy_btn.setObjectName("AboutCopy")
        self.close_btn = QPushButton(tr("about_close", lang))
        self.close_btn.setObjectName("AboutClose")
        self._copy_reset = QTimer(self)
        self._copy_reset.setSingleShot(True)
        self._copy_reset.timeout.connect(lambda: self.copy_btn.setText(tr("about_copy", lang)))
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.copy_btn.clicked.connect(lambda: self._copy_to_clipboard(lang, tech_info))
        self.close_btn.clicked.connect(self.accept)

    def _card(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("AboutCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        ttl = QLabel(title)
        ttl.setObjectName("AboutCardTitle")
        layout.addWidget(ttl)
        return frame

    def _idea_text(self, lang: str) -> str:
        if (lang or "ru").lower() == "en":
            return (
                "Antoshka is a focused assistant for everyday commands and short dialogue. "
                "It combines voice control with a clear desktop UI, keeping actions fast and explicit."
            )
        return (
            "Антошка — практичный помощник для ежедневных команд и короткого диалога. "
            "Он сочетает голосовое управление и понятный интерфейс, чтобы действия были быстрыми и ясными."
        )

    def _copy_to_clipboard(self, lang: str, tech_info: dict[str, str]) -> None:
        parts = [
            tr("about_title", lang),
            tr("about_subtitle", lang),
            f"v{__version__}",
            "",
            tr("about_section_idea", lang),
            self._idea_text(lang),
            "",
            tr("about_section_features", lang),
        ]
        for sec in about_capabilities(lang):
            parts.append(f"- {sec.get('title', '')}: {', '.join(sec.get('features', []))}")
        parts.append("")
        parts.append(tr("about_section_examples", lang))
        parts.extend([f"- {ex}" for ex in about_examples(lang)])
        parts.append("")
        parts.append(tr("about_section_tech", lang))
        parts.extend([f"- {k}: {v}" for k, v in tech_info.items()])
        QApplication.clipboard().setText("\n".join(parts))
        self.copy_btn.setText(tr("about_copied", lang))
        self._copy_reset.start(1500)


class AlertInlineWidget(QFrame):
    def __init__(self, title: str, body: str, actions: list[QPushButton]) -> None:
        super().__init__()
        self.setObjectName("AlertInline")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(0)
        self._layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("AlertInlineTitle")
        self._title_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._title_lbl.setMinimumHeight(0)
        self._body_lbl = QLabel(body)
        self._body_lbl.setObjectName("AlertInlineBody")
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._body_lbl.setMinimumHeight(0)
        self._layout.addWidget(self._title_lbl)
        self._layout.addWidget(self._body_lbl)
        self._btn_row = WrapGridWidget()
        self._btn_row.setObjectName("AlertInlineButtons")
        self._btn_row.set_spacing(8)
        self._btn_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        for btn in actions:
            self._btn_row.add_widget(btn)
        self._layout.addWidget(self._btn_row)
        self._status = AlertStatusBanner("")
        self._status.hide()
        self._layout.addWidget(self._status)
        self._layout.setSpacing(0)
        self._layout.setStretchFactor(self._btn_row, 0)
        self._layout.setStretchFactor(self._status, 0)

    def set_status(self, text: str) -> None:
        if self._btn_row is not None:
            self._layout.removeWidget(self._btn_row)
            self._btn_row.setParent(None)
            self._btn_row = None
        self._status.set_text(text)
        self._status.show()
        self._layout.setSpacing(0)
        self._layout.invalidate()
        self._layout.activate()
        self.adjustSize()


class AlertStatusBanner(QFrame):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.setObjectName("AlertStatusBanner")
        self._text = text
        self._wave_phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(44)
        self.setMaximumHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        self.icon = QLabel("✓")
        self.icon.setObjectName("AlertStatusIcon")
        self.label = QLabel(text)
        self.label.setObjectName("AlertStatusText")
        self.label.setWordWrap(True)
        layout.addWidget(self.icon)
        layout.addWidget(self.label, stretch=1)

    def set_text(self, text: str) -> None:
        self._text = text
        self.label.setText(text)
        self.update()

    def _tick(self) -> None:
        self._wave_phase += 0.08
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.setClipPath(path)
        base_y = rect.center().y()
        wave_amp = 3.0
        spacing = 5.0
        for idx in range(3):
            points = []
            for x in range(int(rect.left()) + 4, int(rect.right()) - 4, 6):
                phase = self._wave_phase + idx * 1.1
                y = base_y + (idx - 1) * spacing + wave_amp * math.sin((x - rect.left()) * 0.04 + phase)
                points.append(QPoint(x, int(y)))
            color = QColor(76, 201, 255, max(40, 80 - idx * 10))
            painter.setPen(QPen(color, 1.0))
            for i in range(1, len(points)):
                painter.drawLine(points[i - 1], points[i])

    def show_centered(self) -> None:
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            center = parent.frameGeometry().center()
            rect = self.frameGeometry()
            rect.moveCenter(center)
            self.move(rect.topLeft())
        else:
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                rect = self.frameGeometry()
                rect.moveCenter(screen.availableGeometry().center())
                self.move(rect.topLeft())
        self.show()

    def set_auto_close(self, seconds: int) -> None:
        seconds = max(0, int(seconds))
        if seconds <= 0:
            self._auto_close_timer.stop()
            return
        self._auto_close_timer.start(seconds * 1000)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_pos = None
        super().mouseReleaseEvent(event)

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
        check_i18n_integrity()
        self.debug_mode = bool((self.settings.get("app", {}) or {}).get("debug", False))
        self.icons = IconSet()
        self._first_message = True
        self._tts_warned = False
        self.listening = False
        self.ai_mode = bool(self.settings.get("ui", {}).get("ai_mode", False))
        self._ai_inflight = False
        self._llm_queue: list[tuple[str, str]] = []
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
        self._maybe_enable_ai_mode()
        self.alert_player = AudioAlerts(self)
        self._active_alert_meta: dict | None = None
        self._event_cards: dict[str, tuple[EventCardWidget, ChatBubble]] = {}
        self._alert_popups: dict[str, AlertPopup] = {}
        self._alert_inlines: dict[str, AlertInlineWidget] = {}
        self._event_anchors: dict[str, QWidget] = {}
        self._help_overlay: HelpOverlay | None = None
        self._last_user_container: QWidget | None = None
        self._suggestion_context = "start"
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

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_toast()

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
            if "OPENAI_API_KEY is missing" in self.llm_error:
                self.log.warning("OpenAI disabled: missing OPENAI_API_KEY")
                self._enqueue_notice(tr("msg_ai_missing_key", self.language))

    def _maybe_enable_ai_mode(self) -> None:
        if self.llm_client is None:
            return
        ui = self.settings.get("ui", {}) or {}
        if not ui.get("ai_mode_autostart", True):
            return
        if ui.get("ai_mode", False):
            return
        ui["ai_mode"] = True
        self.settings["ui"] = ui
        save_settings(self.settings)
        self.ai_mode = True
        self._sync_ai_button()
        self._enqueue_notice(tr("msg_ai_enabled", self.language))

    def _ai_check_message(self, ok: bool, reason: str) -> str:
        if ok:
            return tr("msg_ai_check_ok", self.language)
        if reason == "missing_api_key":
            return tr("msg_ai_missing_key", self.language)
        if reason == "http_401":
            return tr("msg_ai_check_401", self.language)
        if reason == "http_403":
            return tr("msg_ai_check_403", self.language)
        if reason == "http_402":
            return tr("msg_ai_check_no_credits", self.language)
        if reason == "quota":
            return tr("msg_ai_check_no_credits", self.language)
        if reason.startswith("rate_limit:"):
            try:
                seconds = int(float(reason.split(":", 1)[1]))
            except Exception:
                seconds = 0
            if seconds > 0:
                return tr("msg_ai_rate_limit_wait", self.language).format(seconds=seconds)
            return tr("msg_ai_rate_limit", self.language)
        if reason == "rate_limit":
            return tr("msg_ai_rate_limit", self.language)
        if reason == "http_429":
            return tr("msg_ai_check_429", self.language)
        if reason == "network":
            return tr("msg_ai_check_network", self.language)
        return tr("msg_ai_check_error", self.language)

    def _set_ai_busy(self, active: bool) -> None:
        self._ai_inflight = bool(active)
        if active:
            self.ai_busy.setText(tr("msg_ai_inflight", self.language))
            self.ai_busy.show()
        else:
            self.ai_busy.hide()

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
            data_dir=data_dir(),
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
        self.toast = InAppToast(self.root)
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
        self._position_toast()

    def _position_toast(self) -> None:
        toast = getattr(self, "toast", None)
        if toast is None or self.root is None:
            return
        toast.adjustSize()
        margin = max(12, int(self.fontMetrics().height() * 0.9))
        x = max(margin, self.root.width() - toast.width() - margin)
        y = margin
        toast.move(x, y)

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
        self.ai_busy = QLabel("")
        self.ai_busy.setObjectName("AIBusy")
        self.ai_busy.hide()
        top.addWidget(self.ai_busy)
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
        self.chat_container_layout.setSpacing(6)
        self.chat_scroll.setWidget(self.chat_container)
        root_layout.addWidget(self.chat_scroll, stretch=1)

    def _build_input(self, root_layout: QVBoxLayout) -> None:
        suggest_row = QHBoxLayout()
        self.suggestions_bar = SuggestionChipsWidget(
            on_insert=self._insert_command,
            on_send=self._send_command,
            on_log=self._log_suggestion_click,
        )
        suggest_row.addWidget(self.suggestions_bar, stretch=1)
        self.suggestions_refresh = QPushButton("↻")
        self.suggestions_refresh.setObjectName("SuggestionsRefresh")
        self.suggestions_refresh.setCursor(Qt.PointingHandCursor)
        self.suggestions_refresh.clicked.connect(lambda: self._update_suggestions(force_reload=True))
        self.suggestions_refresh.setFixedSize(18, 18)
        suggest_row.addWidget(self.suggestions_refresh)
        root_layout.addLayout(suggest_row)
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
                QFrame#ChatBubble[highlight="true"] {{
                    background: rgba(76, 201, 255, 0.12);
                    border: 1px solid {theme.accent.name()};
                    border-radius: 14px;
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
                #HelpCard {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                }}
                #HelpSearch {{
                    background: {theme.input_bg.name()};
                    border: 1px solid {theme.input_border.name()};
                    border-radius: 10px;
                    padding: 8px 10px;
                }}
                #HelpSection {{
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 10px;
                }}
                #HelpSectionTitle {{ font-size: 13px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #HelpSectionIcon {{ font-size: 14px; }}
                #HelpSectionDesc {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #HelpChip {{
                    background: {theme.button_bg.name()};
                    border: 1px solid {theme.button_border.name()};
                    border-radius: 10px;
                    padding: 6px 10px;
                    font-family: Consolas, "Courier New", monospace;
                }}
                #HelpChip:hover {{
                    border-color: {theme.accent.name()};
                    background: rgba(255, 255, 255, 0.06);
                }}
                #HelpOverlay {{
                    background: transparent;
                }}
                #HelpBackdrop {{
                    background: rgba(10, 12, 18, 0.55);
                }}
                #HelpPanel {{
                    background: #0F1626;
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 20px;
                }}
                #HelpTitle {{
                    font-size: 18px;
                    font-weight: 700;
                    color: #F1F5FF;
                }}
                #HelpClose {{
                    background: transparent;
                    border: none;
                    color: #B9C6E3;
                    font-size: 18px;
                    padding: 4px 6px;
                }}
                #HelpClose:hover {{
                    color: #FFFFFF;
                }}
                #HelpSearch {{
                    background: {theme.input_bg.name()};
                    border: 1px solid {theme.input_border.name()};
                    border-radius: 12px;
                    padding: 10px 12px;
                    font-size: 12px;
                    color: {theme.text_primary.name()};
                }}
                #HelpCategoryChip {{
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 14px;
                    padding: 6px 10px;
                    font-size: 11px;
                    color: #C9D6EE;
                }}
                #HelpCategoryChip:checked {{
                    background: rgba(76, 201, 255, 0.18);
                    border-color: #4CC9FF;
                    color: #EAF6FF;
                }}
                #HelpCommandCard {{
                    background: #111B30;
                    border: 1px solid #233457;
                    border-radius: 16px;
                }}
                #HelpCommandTitle {{
                    font-size: 13px;
                    font-weight: 700;
                    color: #F0F5FF;
                }}
                #HelpCommandDesc {{
                    font-size: 11px;
                    color: #9FB2D6;
                }}
                #HelpExampleText {{
                    font-size: 11px;
                    color: #D6E2F8;
                }}
                #HelpExampleInsert {{
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid #2B3A5E;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 10px;
                    color: #DCE7FF;
                }}
                #HelpExampleRun {{
                    background: {theme.accent.name()};
                    border: none;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 10px;
                    color: #0B1020;
                    font-weight: 700;
                }}
                #SuggestionsBar {{
                    background: transparent;
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                    padding: 8px 10px;
                    min-height: 36px;
                }}
                #SuggestionsBar QPushButton {{
                    color: #EAF1FF;
                }}
                #SuggestionChip {{
                    background: #0F1A2E;
                    border: 1px solid #4CC9FF;
                    border-radius: 7px;
                    padding: 2px 6px;
                    font-family: "Segoe UI", "Arial", sans-serif;
                    color: #EAF1FF;
                    min-height: 16px;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 0.2px;
                }}
                #SuggestionChip:hover {{
                    border-color: #7CD7FF;
                    background: #13233A;
                }}
                #SuggestionChip:pressed {{
                    background: #0B1220;
                }}
                #SuggestionChip:disabled {{
                    color: #8AA0C8;
                    border-color: #2A3A5A;
                }}
                #SuggestionsRefresh {{
                    background: {theme.button_bg.name()};
                    border: 1px solid {theme.button_border.name()};
                    border-radius: 7px;
                    color: {theme.text_primary.name()};
                    font-size: 11px;
                }}
                #SuggestionsRefresh:hover {{
                    border-color: {theme.accent.name()};
                    background: rgba(255, 255, 255, 0.06);
                }}
                #HelpExecute {{
                    background: {theme.accent.name()};
                    color: #0b1020;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-weight: 700;
                }}
                #AboutDialog {{
                    background: {theme.card_bg.name()};
                }}
                #AboutTitle {{ font-size: 18px; font-weight: 800; color: {theme.text_primary.name()}; }}
                #AboutSubtitle {{ font-size: 12px; color: {theme.text_muted.name()}; }}
                #AboutVersion {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #AboutCard {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                }}
                #AboutCardTitle {{ font-size: 13px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #AboutText {{ font-size: 12px; color: {theme.text_primary.name()}; }}
                #AboutBlock {{
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 10px;
                }}
                #AboutBlockTitle {{ font-size: 12px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #AboutBullet {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #AboutIcon {{ font-size: 14px; }}
                #AboutChip {{
                    background: {theme.button_bg.name()};
                    border: 1px solid {theme.button_border.name()};
                    border-radius: 10px;
                    padding: 6px 10px;
                    font-family: Consolas, "Courier New", monospace;
                }}
                #AboutTechRow {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #AlertInline {{
                    background: #0B1220;
                    border: 2px solid #4CC9FF;
                    border-radius: 12px;
                }}
                #AlertInlineTitle {{ font-size: 13px; font-weight: 800; color: #EAF1FF; margin: 0px; padding: 0px; }}
                #AlertInlineBody {{ font-size: 11px; color: #BBD0F5; margin: 0px; padding: 0px; }}
                #AlertStatusBanner {{
                    background: rgba(15, 26, 46, 0.9);
                    border: 1px solid #4CC9FF;
                    border-radius: 8px;
                    min-height: 44px;
                }}
                #AlertStatusIcon {{ font-size: 12px; color: #7CD7FF; }}
                #AlertStatusText {{ font-size: 11px; color: #EAF1FF; }}
                #EventCard {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                }}
                #EventTitle {{ font-size: 13px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #EventSubtitle {{ font-size: 12px; color: {theme.text_primary.name()}; }}
                #EventWhen {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #EventStatus {{ font-size: 11px; color: {theme.accent.name()}; }}
                #InAppToast {{
                    background: {theme.card_bg.name()};
                    border: 1px solid {theme.card_border.name()};
                    border-radius: 12px;
                }}
                #InAppToastTitle {{ font-size: 12px; font-weight: 700; color: {theme.text_primary.name()}; }}
                #InAppToastBody {{ font-size: 11px; color: {theme.text_muted.name()}; }}
                #AIBadge {{
                    background: {theme.accent.name()};
                    color: #0b1020;
                    padding: 4px 10px;
                    border-radius: 10px;
                    font-weight: 700;
                }}
                #AIBusy {{
                    background: {theme.accent_2.name()};
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
        if self._ai_inflight:
            self.ai_busy.setText(tr("msg_ai_inflight", self.language))
        self._update_suggestions(force_reload=True)
        if self._help_overlay is not None:
            self._help_overlay.set_language(self.language, self._build_help_items(self.language))

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
            self._last_user_container = container
        else:
            container = bubble
            self._last_bot_bubble = bubble
        self.chat_container_layout.addWidget(container)
        QTimer.singleShot(0, self, lambda: self._scroll_to_bottom())
        return bubble

    def _help_category_for(self, cmd_name: str) -> str:
        if cmd_name in {"time", "date", "event_add", "event_list"}:
            return "time"
        if cmd_name == "timer_set":
            return "timer"
        if cmd_name == "alarm_set":
            return "alarm"
        if cmd_name == "reminder_set":
            return "reminder"
        if cmd_name.startswith("note_"):
            return "notes"
        if cmd_name in {"open_url", "search_web", "open_mail", "open_calendar", "open_map", "weather"}:
            return "sites"
        if cmd_name == "chat":
            return "ai"
        return "system"

    def _build_help_items(self, lang: str) -> list[dict]:
        registry = self.dialogue.router.registry
        items: list[dict] = []
        for cmd in registry.all():
            title = command_name(cmd.name, lang)
            desc = command_desc(cmd.name, lang)
            if (lang or "ru").lower() == "ru":
                examples = list(cmd.examples_ru or [])
            else:
                examples = list(cmd.examples_en or [])
            examples = [ex for ex in examples if isinstance(ex, str) and ex.strip()]
            items.append(
                {
                    "id": cmd.name,
                    "title": title,
                    "desc": desc,
                    "examples": examples,
                    "category": self._help_category_for(cmd.name),
                }
            )
        items.sort(key=lambda item: (item.get("category", ""), item.get("title", "")))
        return items

    def _open_help_overlay(self) -> None:
        items = self._build_help_items(self.language)
        if not hasattr(self, "_help_overlay") or self._help_overlay is None:
            self._help_overlay = HelpOverlay(
                parent=self,
                items=items,
                lang=self.language,
                on_insert=self._insert_command,
                on_send=self._send_command,
            )
        else:
            self._help_overlay.set_language(self.language, items)
        self._help_overlay.show()
        self._help_overlay.raise_()

    def _append_action(self, result: ActionResult) -> None:
        if result.action == "help":
            self._open_help_overlay()
            msg = result.text or tr("msg_help_opened", self.language)
            self._append_message(msg, is_user=False)
            self._set_suggestion_context("default")
            return

        status_key = "status_ok" if (result.status or "").lower() == "ok" else "status_error"
        status_text = tr(status_key, self.language)
        card = ActionCard(result.title, result.details, status_text, result.url)
        bubble = ChatBubble(result.text, is_user=False, theme=self.theme, action_widget=card)
        self.chat_container_layout.addWidget(bubble)
        self._last_bot_bubble = bubble
        if result.action in {"timer_set", "alarm_set", "reminder_set"}:
            event_id = str(result.meta.get("event_id") or "")
            if event_id:
                self._event_anchors[event_id] = bubble
        self._update_suggestion_context_from_action(result.action)
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
        self._set_suggestion_context("start")

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
            clear_history(data_dir())
            clear_chat_history(data_dir())
            self.log.info("Chat history cleared")

    def _clear_chat_clicked(self) -> None:
        self._clear_chat_flow()

    def _notify(self, message: str | Event) -> None:
        def _update() -> None:
            if isinstance(message, Event):
                self.log.info("ALERT notify received type=%s id=%s", message.type, message.id)
                self._handle_alert_notify(message)
                return
            self._append_message(message, is_user=False)
            self._set_status("speaking")
            self._say_tts_async(message, self.language)
            self._set_status("ready")
        QTimer.singleShot(0, self, _update)

    def _tune_alert_button(self, btn: QPushButton, role: str = "default") -> None:
        fm = btn.fontMetrics()
        margin = btn.style().pixelMetric(QStyle.PM_ButtonMargin, None, btn)
        min_h = fm.height() + margin * 2 + max(6, int(fm.height() * 0.2))
        btn.setMinimumHeight(max(40, int(min_h)))
        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn.setStyleSheet(
            "QPushButton {"
            "font-weight: 800; "
            "background: #1B1F2B; border: 2px solid #EAF1FF; border-radius: 8px; "
            "padding: 8px 12px; color: #EAF1FF; }"
            "QPushButton:hover { background: #2A3347; border-color: #FFFFFF; }"
            "QPushButton:pressed { background: #131924; }"
            "QPushButton:disabled { background: #2A2A2A; border-color: #555555; color: #999999; }"
        )
        if role == "stop":
            btn.setStyleSheet(
                "QPushButton {"
                "font-weight: 800; "
                "background: #FF4D4D; border: 2px solid #FFFFFF; border-radius: 8px; "
                "padding: 8px 12px; color: #1A0202; }"
                "QPushButton:hover { background: #FF6B6B; border-color: #7A1E1E; }"
                "QPushButton:pressed { background: #E63B3B; }"
                "QPushButton:disabled { background: #2A2A2A; border-color: #555555; color: #999999; }"
            )
        elif role == "snooze":
            btn.setStyleSheet(
                "QPushButton {"
                "font-weight: 800; "
                "background: #FFD24D; border: 2px solid #FFFFFF; border-radius: 8px; "
                "padding: 8px 12px; color: #1A1200; }"
                "QPushButton:hover { background: #FFDB66; border-color: #8A6A00; }"
                "QPushButton:pressed { background: #F0C23C; }"
                "QPushButton:disabled { background: #2A2A2A; border-color: #555555; color: #999999; }"
            )
        elif role == "restart":
            btn.setStyleSheet(
                "QPushButton {"
                "font-weight: 700; "
                "background: #8B5CF6; border: 2px solid #FFFFFF; border-radius: 8px; "
                "padding: 8px 12px; color: #0C0620; }"
                "QPushButton:hover { background: #A37BFF; border-color: #4C2B8A; }"
                "QPushButton:pressed { background: #7A49E6; }"
                "QPushButton:disabled { background: #2A2A2A; border-color: #555555; color: #999999; }"
            )

    def _tune_alert_combo(self, combo: QComboBox) -> None:
        fm = combo.fontMetrics()
        margin = combo.style().pixelMetric(QStyle.PM_FocusFrameHMargin, None, combo)
        min_h = fm.height() + margin * 2 + max(8, int(fm.height() * 0.3))
        combo.setMinimumHeight(max(28, int(min_h)))
        combo.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def _show_in_app_toast(self, title: str, body: str) -> None:
        toast = getattr(self, "toast", None)
        if toast is None:
            return
        toast.show_message(title, body)
        self._position_toast()

    def _handle_alert_notify(self, event: Event) -> None:
        kind = str(event.type or "").lower()
        if kind not in {"timer", "alarm", "reminder"}:
            kind = "reminder"
        if kind == "timer":
            duration = str(event.payload.get("duration_text") or event.duration_sec or "")
            msg = tr("msg_timer_done", self.language).format(duration=duration)
        elif kind == "reminder":
            msg = tr("msg_reminder_prefix", self.language).format(text=str(event.payload.get("text", "")))
        elif kind == "alarm":
            msg = tr("msg_alarm_fired", self.language)
        else:
            msg = str(event.payload.get("message", ""))
        debug_overlay = bool(self.debug_mode or (self.settings.get("ui", {}) or {}).get("debug_ui", False))
        actions = self._build_alert_actions(event, debug_ui=debug_overlay)
        subtitle = ""
        if kind == "timer":
            subtitle = f"{tr('label_duration', self.language)}: {duration}"
        elif kind == "reminder":
            subtitle = str(event.payload.get("text", ""))
        when_text = event.due_time.strftime("%H:%M:%S")
        if kind == "timer":
            title = tr("label_fired_timer", self.language)
        elif kind == "reminder":
            title = tr("label_fired_reminder", self.language)
        elif kind == "note":
            title = tr("label_fired_reminder", self.language)
        else:
            title = tr("label_fired_alarm", self.language)

        card = EventCardWidget(
            title=title,
            subtitle=subtitle,
            when_text=when_text,
            buttons_row=actions,
            debug_overlay=debug_overlay,
        )
        card.raise_()
        bubble = self._append_message(msg, is_user=False, action_widget=card)
        self._event_cards[event.id] = (card, bubble)
        self.log.info("ALERT card added type=%s id=%s buttons=%s", kind, event.id, len(card.findChildren(QPushButton)))
        QTimer.singleShot(0, self, lambda c=card: self._log_alert_card_layout(c))
        self._animate_widget_in(bubble)
        card.set_alerting(True)
        bubble.set_emphasis(1.0)
        QTimer.singleShot(0, self, self._scroll_to_bottom)
        QTimer.singleShot(0, self, lambda c=card: c.adjustSize())
        QTimer.singleShot(0, self, lambda: self.chat_container.updateGeometry())
        self._play_alert_sound_from_settings()
        self._active_alert_meta = event.payload
        self.log.info("ALERT start type=%s id=%s sound=%s", kind, event.id, self.settings.get("ui", {}).get("alerts_sound"))
        self._show_in_app_toast(title, msg)
        self._notify_system_event(event, msg)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self.stack.currentWidget() != self.chat_page:
            self.stack.setCurrentWidget(self.chat_page)
        try:
            self.chat_scroll.ensureWidgetVisible(card)
            self.chat_scroll.ensureWidgetVisible(bubble)
        except Exception:  # noqa: BLE001
            pass
        self._show_alert_inline(event, title, msg)
        self._show_alert_popup(event, title, msg)
        self._restore_window()
        try:
            self.chat_scroll.ensureWidgetVisible(card)
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
        except Exception:  # noqa: BLE001
            pass

    def _build_alert_actions(self, event: Event, debug_ui: bool = False) -> QWidget:
        settings = get_alert_settings(self.settings)
        box = QWidget()
        box.setObjectName("EventButtons")
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if debug_ui:
            box.setProperty("debug", True)
        wrapper = QVBoxLayout(box)
        wrapper.setContentsMargins(10, 8, 10, 8)
        wrapper.setSpacing(8)

        primary = WrapGridWidget()
        primary.setObjectName("EventButtonsPrimary")
        primary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        primary.set_spacing(6)
        wrapper.addWidget(primary)

        default_minutes = int(settings.get("snooze_default_minutes", 5))
        snooze_btn = QPushButton(tr("btn_alert_snooze", self.language))
        snooze_btn.setObjectName("AlertBtnSnooze")
        self._tune_alert_button(snooze_btn, role="snooze")
        snooze_btn.clicked.connect(
            lambda: self._alert_button_click(event_id=event.id, action="snooze", minutes=default_minutes)
        )
        primary.add_widget(snooze_btn)

        stop_btn = QPushButton(tr("btn_alert_stop", self.language))
        stop_btn.setObjectName("AlertBtnStop")
        self._tune_alert_button(stop_btn, role="stop")
        stop_btn.clicked.connect(lambda: self._alert_button_click(event_id=event.id, action="stop"))
        primary.add_widget(stop_btn)

        if settings.get("timer_restart_enabled", True):
            restart_btn = QPushButton(tr("btn_alert_repeat", self.language))
            restart_btn.setObjectName("AlertBtnRestart")
            self._tune_alert_button(restart_btn, role="restart")
            restart_btn.clicked.connect(lambda: self._alert_button_click(event_id=event.id, action="restart", event=event))
            primary.add_widget(restart_btn)

        secondary = WrapGridWidget()
        secondary.setObjectName("EventButtonsSecondary")
        secondary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        secondary.set_spacing(6)

        if settings.get("snooze_quick_enabled", True):
            for minutes in settings.get("snooze_quick_buttons", []):
                btn = QPushButton(f"+{int(minutes)}")
                btn.setObjectName("AlertBtnQuick")
                self._tune_alert_button(btn, role="default")
                btn.clicked.connect(
                    lambda _, m=int(minutes): self._alert_button_click(event_id=event.id, action="snooze", minutes=m)
                )
                secondary.add_widget(btn)

        if settings.get("snooze_dropdown_enabled", True):
            dropdown = QComboBox()
            self._tune_alert_combo(dropdown)
            for minutes in settings.get("snooze_dropdown_options", []):
                dropdown.addItem(f"{int(minutes)}", int(minutes))
            dropdown.activated.connect(
                lambda _, dd=dropdown: self._alert_button_click(
                    event_id=event.id,
                    action="snooze",
                    minutes=int(dd.currentData() or settings.get("snooze_default_minutes", 5)),
                )
            )
            secondary.add_widget(dropdown)

        if secondary.layout().count() > 0:
            wrapper.addWidget(secondary)

        fm = box.fontMetrics()
        row_height = max(56, int(fm.height() * 2.4))
        min_rows = 1 + (1 if secondary.layout().count() > 0 else 0)
        box.setMinimumHeight(row_height * min_rows + (wrapper.spacing() * max(0, min_rows - 1)) + 8)
        return box

    def _log_alert_card_layout(self, card: EventCardWidget) -> None:
        try:
            size = card.size()
            min_size = card.minimumSize()
            layout = card.layout()
            layout_type = type(layout).__name__ if layout is not None else "None"
            layout_count = layout.count() if layout is not None else 0
            parent = card.parentWidget()
            parent_name = parent.objectName() if parent is not None else "None"
            self.log.info(
                "ALERT card layout class=%s name=%s parent=%s layout=%s count=%s size=%sx%s min=%sx%s hint=%s geom=%s",
                type(card).__name__,
                card.objectName(),
                parent_name,
                layout_type,
                layout_count,
                size.width(),
                size.height(),
                min_size.width(),
                min_size.height(),
                card.sizeHint(),
                card.geometry(),
            )
            if layout_count > 0 and card.geometry().height() <= 0:
                self.log.warning("ALERT card layout bug: layout has items but height=0")
            for btn in card.findChildren(QPushButton):
                top_left = btn.mapTo(card, QPoint(0, 0))
                rect = QRect(top_left, btn.size())
                visible = btn.isVisible()
                style_len = len(btn.styleSheet() or "")
                reasons = []
                if not visible:
                    reasons.append("isVisible=False")
                if rect.width() <= 0:
                    reasons.append("width<=0")
                if rect.height() <= 0:
                    reasons.append("height<=0")
                if btn.minimumHeight() > btn.height():
                    reasons.append("height too small")
                self.log.info(
                    "ALERT card btn text=%s visible=%s enabled=%s geom=%s size=%sx%s min=%sx%s style_len=%s",
                    btn.text(),
                    visible,
                    btn.isEnabled(),
                    rect,
                    btn.width(),
                    btn.height(),
                    btn.minimumWidth(),
                    btn.minimumHeight(),
                    style_len,
                )
                if reasons:
                    self.log.warning(
                        "ALERT card btn hidden text=%s reasons=%s",
                        btn.text(),
                        ",".join(reasons),
                    )
            buttons_box = card.findChild(QWidget, "EventButtons")
            if buttons_box is not None:
                self.log.info(
                    "ALERT buttons box visible=%s geom=%s size=%sx%s min=%sx%s hint=%s",
                    buttons_box.isVisible(),
                    buttons_box.geometry(),
                    buttons_box.width(),
                    buttons_box.height(),
                    buttons_box.minimumWidth(),
                    buttons_box.minimumHeight(),
                    buttons_box.sizeHint(),
                )
            if layout_count > 0 and size.height() > 0:
                self.log.info("ALERT_UI_RENDER_OK id=%s", id(card))
            else:
                self.log.warning("ALERT_UI_RENDER_BROKEN reason=layout_or_size")
        except Exception as e:  # noqa: BLE001
            self.log.warning("ALERT card layout log failed: %s", e)

    def _alert_button_click(
        self,
        event_id: str,
        action: str,
        minutes: int | None = None,
        event: Event | None = None,
    ) -> None:
        self.log.info("ALERT_BTN_CLICK id=%s action=%s minutes=%s", event_id, action, minutes)
        if action == "snooze" and minutes is not None:
            QTimer.singleShot(0, self, lambda: self._alert_snooze(event_id, minutes))
            return
        if action == "stop":
            QTimer.singleShot(0, self, lambda: self._alert_stop(event_id, "user"))
            return
        if action == "restart" and event is not None:
            QTimer.singleShot(0, self, lambda: self._alert_restart(event))

    def _show_alert_popup(self, event: Event, title: str, body: str) -> bool:
        ui = self.settings.get("ui", {}) or {}
        existing = self._alert_popups.get(event.id)
        if existing is not None:
            try:
                existing.close()
            except Exception:
                pass
        actions: list[QPushButton] = []
        settings = get_alert_settings(self.settings)
        default_minutes = int(settings.get("snooze_default_minutes", 5))
        snooze_btn = QPushButton(tr("btn_alert_snooze", self.language))
        self._tune_alert_button(snooze_btn, role="snooze")
        snooze_btn.clicked.connect(lambda: self._alert_button_click(event.id, "snooze", default_minutes))
        actions.append(snooze_btn)
        stop_btn = QPushButton(tr("btn_alert_stop", self.language))
        self._tune_alert_button(stop_btn, role="stop")
        stop_btn.clicked.connect(lambda: self._alert_button_click(event.id, "stop"))
        actions.append(stop_btn)
        if settings.get("timer_restart_enabled", True):
            restart_btn = QPushButton(tr("btn_alert_repeat", self.language))
            self._tune_alert_button(restart_btn, role="restart")
            restart_btn.clicked.connect(lambda: self._alert_button_click(event.id, "restart", event=event))
            actions.append(restart_btn)
        popup = AlertPopup(None, title, body, actions)
        popup.setMinimumWidth(420)
        popup.set_auto_close(int(ui.get("alert_popup_auto_close_sec", 20)))
        popup.destroyed.connect(lambda: self._alert_popups.pop(event.id, None))
        popup.show_centered()
        popup.raise_()
        popup.activateWindow()
        self._alert_popups[event.id] = popup
        self.log.info("ALERT_UI_POPUP_SHOWN id=%s", event.id)
        return True

    def _show_alert_inline(self, event: Event, title: str, body: str) -> None:
        existing = self._alert_inlines.get(event.id)
        if existing is not None:
            try:
                existing.setParent(None)
            except Exception:
                pass
        actions: list[QPushButton] = []
        settings = get_alert_settings(self.settings)
        default_minutes = int(settings.get("snooze_default_minutes", 5))
        snooze_btn = QPushButton(tr("btn_alert_snooze", self.language))
        self._tune_alert_button(snooze_btn, role="snooze")
        snooze_btn.clicked.connect(lambda: self._alert_button_click(event.id, "snooze", default_minutes))
        actions.append(snooze_btn)
        stop_btn = QPushButton(tr("btn_alert_stop", self.language))
        self._tune_alert_button(stop_btn, role="stop")
        stop_btn.clicked.connect(lambda: self._alert_button_click(event.id, "stop"))
        actions.append(stop_btn)
        if settings.get("timer_restart_enabled", True):
            restart_btn = QPushButton(tr("btn_alert_repeat", self.language))
            self._tune_alert_button(restart_btn, role="restart")
            restart_btn.clicked.connect(lambda: self._alert_button_click(event.id, "restart", event=event))
            actions.append(restart_btn)
        inline = AlertInlineWidget(title, body, actions)
        anchor = self._event_anchors.get(event.id)
        if anchor is not None:
            idx = self.chat_container_layout.indexOf(anchor)
            if idx >= 0:
                self.chat_container_layout.insertWidget(idx + 1, inline)
                self._highlight_anchor(anchor)
            else:
                self.chat_container_layout.insertWidget(0, inline)
        else:
            self.chat_container_layout.insertWidget(0, inline)
        self._alert_inlines[event.id] = inline
        self.log.info("ALERT_UI_INLINE_SHOWN id=%s", event.id)

    def _update_alert_inline_status(self, event_id: str, text: str) -> None:
        inline = self._alert_inlines.get(event_id)
        if inline is None:
            return
        inline.set_status(text)

    def _alert_snooze(self, event_id: str, minutes: int) -> None:
        minutes = max(1, int(minutes))
        event = self.app_context.scheduler.get_event(event_id)
        if not event:
            self._append_message(tr("msg_event_not_found", self.language), is_user=False)
            return
        event.snooze_count += 1
        new_due = datetime.now() + timedelta(minutes=minutes)
        ok = self.app_context.scheduler.reschedule_event(event_id, new_due)
        if ok:
            self._alert_stop(event_id, "snooze", emit_msg=False)
            self._update_event_card(event_id, tr("msg_snoozed", self.language).format(minutes=minutes))
            time_text = new_due.strftime("%H:%M")
            msg_key = {
                "timer": "msg_timer_snoozed",
                "alarm": "msg_alarm_snoozed",
                "reminder": "msg_reminder_snoozed",
            }.get(str(event.type), "msg_reminder_snoozed")
            status_text = tr(msg_key, self.language).format(minutes=minutes, time=time_text)
            self._update_alert_inline_status(event_id, status_text)
            self._append_message(status_text, is_user=False)
            self.log.info("ALERT_ACTION_DONE action=snooze id=%s", event_id)
            self.log.info("ALERT snooze id=%s minutes=%s", event_id, minutes)

    def _alert_restart(self, event: Event) -> None:
        kind = str(event.type)
        new_id = None
        if kind == "timer":
            new_id = self.app_context.scheduler.restart_timer(event.id)
        elif kind == "reminder":
            delay = int(event.payload.get("delay_sec") or event.payload.get("duration_sec") or 0)
            text = str(event.payload.get("text", ""))
            if delay > 0:
                new_id = self.app_context.scheduler.schedule_in(
                    delay,
                    tr("msg_reminder_prefix", self.language).format(text=text),
                    meta={"type": "reminder", "text": text, "delay_sec": delay},
                )
        elif kind == "alarm":
            time_text = str(event.payload.get("time") or "")
            when = parse_time_of_day(time_text) if time_text else None
            if when is not None:
                seconds = max(0, int((when - datetime.now()).total_seconds()))
                new_id = self.app_context.scheduler.schedule_in(
                    seconds,
                    tr("msg_alarm_fired", self.language),
                    meta={"type": "alarm", "time": time_text},
                )

        if not new_id:
            self.log.warning("ALERT restart failed: id=%s type=%s", event.id, kind)
            type_label = self._event_type_label(kind)
            self._append_message(tr("msg_action_unavailable_type", self.language).format(type=type_label), is_user=False)
            return
        self._alert_stop(event.id, "restart", emit_msg=False)
        self._update_event_card(event.id, tr("msg_timer_restarted", self.language))
        duration = self._format_duration(event.duration_sec or 0)
        status_text = tr("msg_timer_restarted_detail", self.language).format(duration=duration)
        self._update_alert_inline_status(event.id, status_text)
        self._append_message(status_text, is_user=False)
        self.log.info("ALERT_ACTION_DONE action=restart id=%s", event.id)
        self.log.info("ALERT restart id=%s type=%s new_id=%s", event.id, kind, new_id)

    def _alert_stop(self, event_id: str, reason: str, emit_msg: bool = True) -> None:
        self._stop_alert_sound()
        event = self.app_context.scheduler.get_event(event_id)
        ok = self.app_context.scheduler.dismiss_event(event_id)
        self._update_event_card(event_id, tr("msg_alert_stopped", self.language))
        self._active_alert_meta = None
        self._close_alert_popup(event_id)
        if emit_msg and ok and event is not None:
            msg_key = {
                "timer": "msg_timer_stopped",
                "alarm": "msg_alarm_stopped",
                "reminder": "msg_reminder_cancelled",
            }.get(str(event.type), "msg_reminder_cancelled")
            status_text = tr(msg_key, self.language)
            self._update_alert_inline_status(event_id, status_text)
            self._append_message(status_text, is_user=False)
            self.log.info("ALERT_ACTION_DONE action=stop id=%s", event_id)
        elif emit_msg and not ok:
            self._append_message(tr("msg_event_not_found", self.language), is_user=False)
        self.log.info("ALERT stop id=%s reason=%s", event_id, reason)

    def _alert_stop_all(self) -> None:
        self._stop_alert_sound()
        count = self.app_context.scheduler.dismiss_all()
        for event_id in list(self._alert_popups.keys()):
            self._close_alert_popup(event_id)
        for event_id in list(self._alert_inlines.keys()):
            self._close_alert_inline(event_id)
        for event_id in list(self._event_cards.keys()):
            self._update_event_card(event_id, tr("msg_alert_stopped", self.language))
        if count:
            msg = "Все оповещения отключены."
            if (self.language or "ru").lower() == "en":
                msg = "All alerts disabled."
            self._notify(msg)
        self.log.info("ALERT stop_all count=%s", count)

    def _close_alert_popup(self, event_id: str) -> None:
        popup = self._alert_popups.pop(event_id, None)
        if popup is None:
            return
        try:
            popup.close()
        except Exception:
            pass

    def _close_alert_inline(self, event_id: str) -> None:
        inline = self._alert_inlines.pop(event_id, None)
        if inline is None:
            return
        try:
            inline.setVisible(False)
            QTimer.singleShot(800, self, lambda w=inline: w.setParent(None))
        except Exception:
            pass

    def _highlight_anchor(self, widget: QWidget) -> None:
        try:
            widget.setProperty("highlight", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            QTimer.singleShot(1500, self, lambda w=widget: self._clear_highlight(w))
        except Exception:
            pass

    def _clear_highlight(self, widget: QWidget) -> None:
        try:
            widget.setProperty("highlight", False)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        except Exception:
            pass

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
            self.log.info("NOTIFY_SKIP reason=disabled type=%s id=%s", event.type, event.id)
            return
        show_text = bool(ui.get("notify_show_text", True))
        show_icon = bool(ui.get("notify_show_icon", True))
        dup_tray = bool(ui.get("notify_tray_fallback_dup", True))
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
        ok = self.notifier.notify(payload, dup_tray=dup_tray)
        if ok:
            self.log.info("NOTIFY_OK type=%s id=%s", kind, event.id)
        else:
            self.log.warning("NOTIFY_FAIL type=%s id=%s", kind, event.id)
            if self.debug_mode:
                self._append_message(tr("msg_notify_failed", self.language), is_user=False)

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
                msg = tr("msg_alert_handled", self.language)
                self._notify(msg)
            else:
                msg = tr("msg_event_not_found", self.language)
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
        custom_path = str(settings.get("alerts_sound_path", ""))
        volume = int(settings.get("alerts_volume", 80))
        loop = bool(settings.get("alerts_loop", True))
        path = custom_path or rel
        if custom_path and not Path(custom_path).exists():
            self.log.warning("Custom alert sound missing: %s", custom_path)
            path = rel
        self._play_alert_sound(path, volume, loop=loop, test=False)

    def _play_alert_sound(self, rel_path: str, volume: int, loop: bool, test: bool = False) -> None:
        raw = (rel_path or "").strip()
        if not raw:
            return
        path = Path(raw)
        if not path.is_absolute():
            path = resource_path(Path(raw))
        if not path.exists():
            self.log.warning("Alert sound not found: %s", raw)
            if test:
                self._notify(tr("msg_alert_sound_missing", self.language))
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

    def _insert_command(self, text: str) -> None:
        self.input.setText(text)
        self.input.setFocus()
        self.input.setCursorPosition(len(text))

    def _send_command(self, text: str) -> None:
        self._process_text(text, from_voice=False)

    def _log_suggestion_click(self, text: str, mode: str) -> None:
        self.log.info("SUGGESTION_CLICK text=%s mode=%s", text, mode)

    def _set_suggestion_context(self, context: str) -> None:
        self._suggestion_context = context or "default"
        self._update_suggestions()

    def _update_suggestion_context_from_action(self, action: str) -> None:
        action = str(action or "").lower()
        if action in {"timer_set", "alarm_set", "reminder_set"}:
            self._set_suggestion_context("timers")
            return
        if action.startswith("note_"):
            self._set_suggestion_context("notes")
            return
        if action.startswith("settings_"):
            self._set_suggestion_context("settings")
            return
        if action in {"help"}:
            self._set_suggestion_context("default")
            return
        if action in {"open_url", "open_map", "open_mail", "open_calendar", "search_web"}:
            self._set_suggestion_context("default")
            return
        if action in {"open_app", "open_path", "screenshot", "volume_set"}:
            self._set_suggestion_context("default")
            return
        self._set_suggestion_context("default")

    def _update_suggestions(self, force_reload: bool = False) -> None:
        if not hasattr(self, "suggestions_bar"):
            return
        enabled = bool(self.settings.get("ui", {}).get("suggestions_enabled", True))
        if not enabled:
            self.suggestions_bar.hide()
            if hasattr(self, "suggestions_refresh"):
                self.suggestions_refresh.hide()
            return
        self.suggestions_bar.show()
        if hasattr(self, "suggestions_refresh"):
            self.suggestions_refresh.show()
        ctx = self._suggestion_context or "default"
        registry = getattr(self.dialogue, "router", None).registry if self.dialogue else None
        items = []
        if registry is not None:
            items = pick_suggestions(registry, self.language, ctx, k=5)
        send_on_click = bool(self.settings.get("ui", {}).get("suggestions_send_on_click", False))
        tip_insert = tr("suggestion_tip_insert", self.language)
        tip_send = tr("suggestion_tip_send", self.language)
        self.suggestions_bar.set_suggestions(items, send_on_click, tip_insert, tip_send)
        if hasattr(self, "suggestions_refresh"):
            self.suggestions_refresh.setToolTip(tr("suggestion_refresh", self.language))

    def _format_duration(self, seconds: int) -> str:
        seconds = max(0, int(seconds))
        if seconds >= 60:
            minutes = max(1, int(round(seconds / 60)))
            if (self.language or "ru").lower() == "en":
                return f"{minutes} min"
            return f"{minutes} мин"
        if (self.language or "ru").lower() == "en":
            return f"{seconds} sec"
        return f"{seconds} сек"

    def _event_type_label(self, event_type: str) -> str:
        if (self.language or "ru").lower() == "en":
            return {"timer": "Timer", "alarm": "Alarm", "reminder": "Reminder"}.get(event_type, "Event")
        return {"timer": "таймер", "alarm": "будильник", "reminder": "напоминание"}.get(event_type, "событие")

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

        allow_llm = bool(self.ai_mode and self.llm_client is not None)
        route = self.dialogue.router.route(text, lang=lang)
        needs_llm = allow_llm and route is None
        if needs_llm and self.llm_client is not None:
            if self.llm_client.is_busy() or self._llm_queue:
                self._llm_queue.append((text, lang))
                msg = tr("msg_ai_queued", self.language).format(position=len(self._llm_queue))
                self._append_message(msg, is_user=False)
                self._set_status("ready")
                return

        def _worker() -> None:
            try:
                if needs_llm:
                    QTimer.singleShot(0, self, lambda: self._set_ai_busy(True))
                answer = self.dialogue.handle_text(
                    text,
                    language=lang,
                    allow_llm=allow_llm,
                )
            except Exception as e:  # noqa: BLE001
                self.log.exception("UI worker failed: %s", e)
                answer = tr("msg_error_generic", lang)

            if isinstance(answer, ActionResult):
                answer_text = answer.to_text()
            else:
                answer_text = str(answer)
            unknown_reply = answer_text.strip() == tr("msg_unknown_command", lang).strip()
            if allow_llm:
                append_chat(data_dir(), "user", text)
                append_chat(data_dir(), "assistant", answer_text)

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
                if needs_llm:
                    self._set_ai_busy(False)
                if isinstance(answer, ActionResult):
                    self.log.info("UI update: action=%s status=%s", answer.action, answer.status)
                else:
                    self.log.info("UI update: message_len=%s", len(answer_text))
                if isinstance(answer, ActionResult) and answer.action == "clear_chat":
                    self._clear_chat_flow()
                    self._set_status("ready")
                    return
                if isinstance(answer, ActionResult):
                    self._append_action(answer)
                else:
                    self._append_message(answer_text, is_user=False)
                if unknown_reply:
                    self._set_suggestion_context("unknown_fallback")
                self._set_status("speaking")
                self.log.info("TTS start: len=%s lang=%s", len(answer_text), lang)
                self._say_tts_async(answer_text, lang)
                self._set_status("ready")
                if needs_llm and self._llm_queue:
                    next_text, next_lang = self._llm_queue.pop(0)
                    QTimer.singleShot(0, self, lambda: self._process_text(next_text, from_voice=False))

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

    def _open_about(self, parent: QWidget | None = None) -> None:
        lang = self.language
        tech = self._about_tech_info(lang)
        host = parent if parent is not None else self
        dlg = AboutDialog(host, lang, tech)
        dlg.exec()

    def _about_tech_info(self, lang: str) -> dict[str, str]:
        tts_raw = self.settings.get("tts", {}) or {}
        llm_raw = self.settings.get("llm", {}) or {}
        stt_mode = (self.settings.get("stt", {}) or {}).get("mode", "")
        stt_name = type(self.stt).__name__ if getattr(self, "stt", None) is not None else "unknown"
        tts_provider = str(tts_raw.get("provider", "auto"))
        llm_provider = str(llm_raw.get("provider", "none"))
        llm_model = str(llm_raw.get("model", ""))
        ai_enabled = self.llm_client is not None
        if (lang or "ru").lower() == "en":
            ai_status = "AI enabled" if ai_enabled else "AI unavailable"
            info = {
                "STT": f"{stt_name} ({stt_mode})" if stt_mode else stt_name,
                "TTS": tts_provider,
                "LLM": f"{llm_provider} {llm_model}".strip(),
                "AI": ai_status,
                "Logs": str(logs_dir()),
            }
        else:
            ai_status = "ИИ включён" if ai_enabled else "ИИ недоступен"
            info = {
                "Распознавание речи": f"{stt_name} ({stt_mode})" if stt_mode else stt_name,
                "Озвучка": tts_provider,
                "Модель ИИ": f"{llm_provider} {llm_model}".strip(),
                "Статус ИИ": ai_status,
                "Логи": str(logs_dir()),
            }
        return info

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

        # Information
        info_card, info_grid = card(tr("section_info", self.language))
        info_row = 0
        about_btn = QPushButton(tr("btn_about", self.language))
        about_btn.clicked.connect(lambda: self._open_about(dlg))
        info_row = add_row(info_grid, info_row, tr("btn_about", self.language), about_btn)

        # Chat
        chat_card, chat_grid = card(tr("section_chat", self.language))
        chat_row = 0
        suggest_enabled = QCheckBox("")
        suggest_enabled.setChecked(bool(self.settings.get("ui", {}).get("suggestions_enabled", True)))
        suggest_send = QCheckBox("")
        suggest_send.setChecked(bool(self.settings.get("ui", {}).get("suggestions_send_on_click", False)))
        chat_row = add_row(chat_grid, chat_row, tr("label_show_suggestions", self.language), suggest_enabled)
        chat_row = add_row(chat_grid, chat_row, tr("label_suggest_send_on_click", self.language), suggest_send)

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
            except Exception as e:  # noqa: BLE001
                self.log.exception("Wake word stop failed: %s", e)
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

        # AI
        ai_card, ai_grid = card(tr("section_ai", self.language))
        ai_row = 0
        ai_check_btn = QPushButton(tr("btn_ai_check", self.language))
        ai_status = QLabel("")
        ai_status.setObjectName("HelperText")

        def _ai_check() -> None:
            if self.llm_client is None:
                msg = tr("msg_ai_missing_key", self.language)
                ai_status.setText(msg)
                self._append_message(msg, is_user=False)
                self.log.warning("AI check failed: missing key")
                return

            def _worker() -> None:
                ok, reason = self.llm_client.test_connection()
                msg = self._ai_check_message(ok, reason)
                if ok:
                    self.log.info("AI check ok")
                else:
                    self.log.warning("AI check failed: %s", reason)

                def _update() -> None:
                    ai_status.setText(msg)
                    self._append_message(msg, is_user=False)

                QTimer.singleShot(0, dlg, _update)

            threading.Thread(target=_worker, daemon=True).start()

        ai_check_btn.clicked.connect(_ai_check)
        ai_row = add_row(ai_grid, ai_row, tr("btn_ai_check", self.language), ai_check_btn)
        ai_card.addWidget(ai_status)

        # Alerts
        alerts_card, alerts_grid = card(tr("section_alerts", self.language))
        alerts_row = 0
        alert_settings = get_alert_settings(self.settings)
        alerts_enabled = QCheckBox("")
        alerts_enabled.setChecked(bool(alert_settings.get("alerts_enabled", True)))
        alerts_loop = QCheckBox("")
        alerts_loop.setChecked(bool(alert_settings.get("alerts_loop", True)))
        alerts_sound = QComboBox()
        custom_list = QListWidget()
        custom_list.setMinimumHeight(90)

        def _normalize_custom(items: list) -> list[dict]:
            out: list[dict] = []
            for item in items:
                if isinstance(item, str):
                    path = item
                    name = Path(path).stem
                elif isinstance(item, dict):
                    path = str(item.get("path") or "")
                    name = str(item.get("name") or Path(path).stem)
                else:
                    continue
                if path:
                    out.append({"name": name or Path(path).stem, "path": path})
            return out

        custom_sounds = _normalize_custom(alert_settings.get("alerts_custom_sounds", []))

        def _refresh_sounds(select_path: str | None = None) -> None:
            alerts_sound.clear()
            custom_list.clear()
            sounds = list_alert_sounds()
            if not sounds:
                alerts_sound.addItem("default", "")
            else:
                for s in sounds:
                    rel = str(s.rel)
                    path = resource_path(Path(rel))
                    label = s.label
                    if not path.exists():
                        label = f"{label} (missing)"
                    alerts_sound.addItem(label, rel)
            for item in custom_sounds:
                path = Path(item.get("path", ""))
                if not str(path):
                    continue
                label = str(item.get("name") or path.stem)
                display = label if path.exists() else f"{label} (missing)"
                alerts_sound.addItem(display, str(path))
            for item in custom_sounds:
                name = item.get("name") or Path(item.get("path", "")).stem
                path = Path(item.get("path", ""))
                suffix = "" if path.exists() else " (missing)"
                custom_list.addItem(f"{name}{suffix}")
            target = select_path or str(alert_settings.get("alerts_sound_path") or "") or str(alert_settings.get("alerts_sound") or "")
            idx = alerts_sound.findData(target)
            if idx >= 0:
                alerts_sound.setCurrentIndex(idx)

        _refresh_sounds()
        alerts_volume = QSlider(Qt.Horizontal)
        alerts_volume.setRange(0, 100)
        alerts_volume.setValue(int(alert_settings.get("alerts_volume", 80)))
        alerts_test = QPushButton(tr("btn_test_alert", self.language))
        alerts_add = QPushButton(tr("btn_add_sound", self.language))
        alerts_delete = QPushButton(tr("btn_delete_sound", self.language))

        def _test_alert() -> None:
            self._play_alert_sound(
                str(alerts_sound.currentData() or ""),
                alerts_volume.value(),
                loop=alerts_loop.isChecked(),
                test=True,
            )

        def _add_alert_sound() -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                dlg,
                tr("btn_add_sound", self.language),
                str(Path.home()),
                "Audio Files (*.mp3 *.wav *.ogg)",
            )
            if not file_path:
                return
            path = str(Path(file_path))
            if any(item.get("path") == path for item in custom_sounds):
                _refresh_sounds(path)
                return
            custom_sounds.append({"name": Path(path).stem, "path": path})
            _refresh_sounds(path)

        def _delete_alert_sound() -> None:
            row = custom_list.currentRow()
            if row < 0 or row >= len(custom_sounds):
                return
            removed = custom_sounds.pop(row)
            current = str(alerts_sound.currentData() or "")
            if current == removed.get("path"):
                _refresh_sounds()
            else:
                _refresh_sounds(current)

        alerts_test.clicked.connect(_test_alert)
        alerts_add.clicked.connect(_add_alert_sound)
        alerts_delete.clicked.connect(_delete_alert_sound)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_enabled", self.language), alerts_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_sound", self.language), alerts_sound)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_custom", self.language), custom_list)
        alerts_row = add_row(alerts_grid, alerts_row, tr("btn_add_sound", self.language), alerts_add)
        alerts_row = add_row(alerts_grid, alerts_row, tr("btn_delete_sound", self.language), alerts_delete)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_volume", self.language), alerts_volume)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alerts_loop", self.language), alerts_loop)
        alerts_row = add_row(alerts_grid, alerts_row, tr("btn_test_alert", self.language), alerts_test)

        notify_enabled = QCheckBox("")
        notify_enabled.setChecked(bool(alert_settings.get("system_notifications", True)))
        notify_show_text = QCheckBox("")
        notify_show_text.setChecked(bool(alert_settings.get("notify_show_text", True)))
        notify_show_icon = QCheckBox("")
        notify_show_icon.setChecked(bool(alert_settings.get("notify_show_icon", True)))
        notify_tray_dup = QCheckBox("")
        notify_tray_dup.setChecked(bool(alert_settings.get("notify_tray_fallback_dup", True)))
        notify_test = QPushButton(tr("btn_test_notify", self.language))
        alert_popup_enabled = QCheckBox("")
        alert_popup_enabled.setChecked(bool(alert_settings.get("alert_popup_enabled", True)))
        alert_popup_timeout = QSpinBox()
        alert_popup_timeout.setRange(0, 120)
        alert_popup_timeout.setValue(int(alert_settings.get("alert_popup_auto_close_sec", 20)))

        def _test_notify() -> None:
            event = Event(type="timer", due_time=datetime.now(), payload={"message": "test"})
            msg = tr("msg_timer_done", self.language).format(duration="5 минут")
            self._notify_system_event(event, msg)

        notify_test.clicked.connect(_test_notify)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_system_notifications", self.language), notify_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_notify_text", self.language), notify_show_text)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_notify_icon", self.language), notify_show_icon)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_notify_tray_dup", self.language), notify_tray_dup)
        alerts_row = add_row(alerts_grid, alerts_row, tr("btn_test_notify", self.language), notify_test)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alert_popup", self.language), alert_popup_enabled)
        alerts_row = add_row(alerts_grid, alerts_row, tr("label_alert_popup_timeout", self.language), alert_popup_timeout)

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
                str(alerts_sound.currentText() or ""),
                [item for item in custom_sounds],
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
                notify_tray_dup.isChecked(),
                alert_popup_enabled.isChecked(),
                alert_popup_timeout.value(),
                theme_preset.currentText(),
                accent_input.text().strip(),
                intensity_slider.value(),
                show_start.isChecked(),
                suggest_enabled.isChecked(),
                suggest_send.isChecked(),
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
        alerts_sound_path: str,
        alerts_sound_name: str,
        alerts_custom_sounds: list[dict],
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
        notify_tray_dup: bool,
        alert_popup_enabled: bool,
        alert_popup_timeout: int,
        theme_preset: str,
        accent_color: str,
        intensity_value: int,
        show_start: bool,
        suggestions_enabled: bool,
        suggestions_send_on_click: bool,
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
        raw_path = str(alerts_sound_path or "")
        if raw_path and Path(raw_path).is_absolute():
            self.settings.setdefault("ui", {})["alerts_sound_path"] = raw_path
            self.settings.setdefault("ui", {})["alerts_sound"] = ""
        else:
            self.settings.setdefault("ui", {})["alerts_sound"] = raw_path
            self.settings.setdefault("ui", {})["alerts_sound_path"] = ""
        self.settings.setdefault("ui", {})["alerts_sound_name"] = str(alerts_sound_name or "")
        self.settings.setdefault("ui", {})["alerts_custom_sounds"] = list(alerts_custom_sounds or [])
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
        self.settings.setdefault("ui", {})["notify_tray_fallback_dup"] = bool(notify_tray_dup)
        self.settings.setdefault("ui", {})["alert_popup_enabled"] = bool(alert_popup_enabled)
        self.settings.setdefault("ui", {})["alert_popup_auto_close_sec"] = int(alert_popup_timeout)
        self.settings.setdefault("ui", {})["theme_preset"] = theme_preset.lower()
        self.settings.setdefault("ui", {})["accent_color"] = accent_color
        self.settings.setdefault("ui", {})["background_intensity"] = float(intensity_value) / 100.0
        self.settings.setdefault("ui", {})["show_start_screen"] = bool(show_start)
        self.settings.setdefault("ui", {})["suggestions_enabled"] = bool(suggestions_enabled)
        self.settings.setdefault("ui", {})["suggestions_send_on_click"] = bool(suggestions_send_on_click)
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
        history = read_json(data_dir() / "history.json", default=[])
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
            if self.llm_error and "OPENAI_API_KEY is missing" in self.llm_error:
                self._notify(tr("msg_ai_missing_key", self.language))
            else:
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
                msg = tr("msg_stt_model_missing", self.language)
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
