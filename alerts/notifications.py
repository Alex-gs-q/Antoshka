from __future__ import annotations

from dataclasses import dataclass
import html
from pathlib import Path
from typing import Callable, Optional

from core.logger import setup_logger

try:  # optional winrt
    from winrt.windows.ui.notifications import ToastNotificationManager, ToastNotification
    from winrt.windows.data.xml.dom import XmlDocument
except Exception:  # noqa: BLE001
    try:  # fallback to winsdk
        from winsdk.windows.ui.notifications import (  # type: ignore
            ToastNotificationManager,
            ToastNotification,
        )
        from winsdk.windows.data.xml.dom import XmlDocument  # type: ignore
    except Exception:  # noqa: BLE001
        ToastNotificationManager = None
        ToastNotification = None
        XmlDocument = None


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    body: str
    icon_path: Optional[Path] = None
    action_repeat_label: Optional[str] = None
    action_stop_label: Optional[str] = None
    action_repeat_args: Optional[str] = None
    action_stop_args: Optional[str] = None


class NotificationService:
    def __init__(
        self,
        app_id: str,
        on_click: Callable[[], None],
        on_action: Optional[Callable[[str, str, str], None]] = None,
        tray_fallback=None,
    ):
        self.log = setup_logger()
        self.app_id = app_id
        self.on_click = on_click
        self.on_action = on_action
        self.tray = tray_fallback

    def notify(self, payload: NotificationPayload, dup_tray: bool = False, force_tray: bool = False) -> bool:
        ok_winrt = False
        ok_tray = False
        if not force_tray and ToastNotificationManager and XmlDocument and ToastNotification:
            ok_winrt = self._notify_winrt(payload)
        if force_tray or (not ok_winrt) or dup_tray:
            ok_tray = self._notify_tray(payload, reason="dup" if dup_tray and ok_winrt else "fallback")
        return ok_winrt or ok_tray

    def _notify_winrt(self, payload: NotificationPayload) -> bool:
        try:
            title = html.escape(payload.title)
            body = html.escape(payload.body)
            template = (
                "<toast>"
                "<visual>"
                "<binding template='ToastGeneric'>"
                f"<text>{title}</text>"
                f"<text>{body}</text>"
            )
            if payload.icon_path and payload.icon_path.exists():
                template += f"<image placement='appLogoOverride' src='{payload.icon_path.as_uri()}'/>"
            template += "</binding></visual>"
            actions = []
            if payload.action_repeat_label and payload.action_repeat_args:
                actions.append(
                    "<action "
                    f"content='{html.escape(payload.action_repeat_label)}' "
                    f"arguments='{html.escape(payload.action_repeat_args)}' "
                    "activationType='foreground'/>"
                )
            if payload.action_stop_label and payload.action_stop_args:
                actions.append(
                    "<action "
                    f"content='{html.escape(payload.action_stop_label)}' "
                    f"arguments='{html.escape(payload.action_stop_args)}' "
                    "activationType='foreground'/>"
                )
            if actions:
                template += "<actions>" + "".join(actions) + "</actions>"
            template += "</toast>"
            xml = XmlDocument()
            xml.load_xml(template)
            toast = ToastNotification(xml)
            try:
                def _on_activated(sender=None, args=None) -> None:
                    if args is not None and self.on_action is not None:
                        arg_str = getattr(args, "arguments", "")
                        if isinstance(arg_str, str) and arg_str:
                            parts = dict(
                                item.split("=", 1) for item in arg_str.split(";") if "=" in item
                            )
                            action = parts.get("action", "")
                            event_id = parts.get("id", "")
                            event_type = parts.get("type", "")
                            if action and event_id and event_type:
                                self.on_action(action, event_id, event_type)
                                return
                    self.on_click()

                toast.add_activated(_on_activated)
            except Exception as e:  # noqa: BLE001
                self.log.exception("Toast activation handler failed: %s", e)
            notifier = ToastNotificationManager.create_toast_notifier(self.app_id)
            notifier.show(toast)
            self.log.info("NOTIFY_OK provider=winrt")
            return True
        except Exception as e:  # noqa: BLE001
            self.log.warning("NOTIFY_FAIL provider=winrt reason=%s", e)
            return False

    def _notify_tray(self, payload: NotificationPayload, reason: str = "fallback") -> bool:
        if self.tray is None:
            return False
        try:
            self.tray.showMessage(payload.title, payload.body)
            self.log.info("NOTIFY_OK provider=tray reason=%s", reason)
            return True
        except Exception as e:  # noqa: BLE001
            self.log.warning("NOTIFY_FAIL provider=tray reason=%s", e)
            return False
