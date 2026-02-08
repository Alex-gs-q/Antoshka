from __future__ import annotations

import threading
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    E,
    N,
    S,
    W,
    BooleanVar,
    Canvas,
    StringVar,
    Text,
    Tk,
    Toplevel,
    ttk,
    PhotoImage,
)
from tkinter import font as tkfont

from core.app_context import AppContext
from core.config import load_settings, save_settings
from core.dialogue import Dialogue, DialogueConfig
from core.logger import setup_logger
from core.stt import TextSTT, create_stt
from core.tts import TTS, TTSConfig
from llm.client import LLMClient, LLMConfig
from services.scheduler import Scheduler
from services.storage import read_json
from services.volume import VolumeController


class AntoshkaUI:
    def __init__(self) -> None:
        self.logger = setup_logger()
        self.settings = load_settings()

        self.root = Tk()
        self.root.title("Антошка")
        self.root.geometry("960x640")
        self.root.minsize(860, 560)
        self.root.configure(bg="#0f1117")
        self._set_window_icon()

        self.status_var = StringVar(value="")
        self.input_var = StringVar()
        self.listening = False
        self._listen_token = 0

        self._init_fonts()
        self._init_styles()
        self._load_images()
        self._build_ui()
        self._set_status("готов")

        self.tts = self._init_tts()
        self.llm_client = self._init_llm()
        self.stt = create_stt(self.settings)

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
        )

        self.dialogue = Dialogue(
            DialogueConfig(
                dangerous_mode=bool(
                    self.settings.get("safety", {}).get("dangerous_mode", False)
                ),
                llm_client=self.llm_client,
                app_context=self.app_context,
            )
        )

        self._show_startup_diagnostics()

        if isinstance(self.stt, TextSTT):
            self.listen_button.configure(state="disabled")
            self._set_status("текстовый режим: вводи команду ниже")

    def run(self) -> None:
        self.root.mainloop()

    def _init_fonts(self) -> None:
        self.font_title = tkfont.Font(family="Bahnschrift", size=18, weight="bold")
        self.font_sub = tkfont.Font(family="Bahnschrift", size=11)
        self.font_body = tkfont.Font(family="Bahnschrift", size=12)

    def _init_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#141824")
        style.configure("TLabel", background="#141824", foreground="#e6e8ff")
        style.configure("Sub.TLabel", background="#141824", foreground="#9aa4c8")
        style.configure(
            "TButton",
            background="#1f2536",
            foreground="#e6e8ff",
            padding=(12, 6),
            relief="flat",
        )
        style.map("TButton", background=[("active", "#27304a")])
        style.configure(
            "TEntry",
            fieldbackground="#0f1424",
            foreground="#e6e8ff",
            insertcolor="#e6e8ff",
        )
        style.configure("Icon.TButton", background="#1b2030", padding=(8, 6))

    def _set_window_icon(self) -> None:
        ico = Path("img") / "app_icon_antoshka.ico"
        if ico.exists():
            try:
                self.root.iconbitmap(default=str(ico))
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Icon set failed: %s", e)

    def _load_images(self) -> None:
        self.images = {}
        for name in [
            "ui_mic_32.png",
            "ui_stop_32.png",
            "ui_sparkles_32.png",
            "ui_volume_32.png",
            "ui_history_32.png",
            "ui_gear_32.png",
            "app_icon_default_256.png",
        ]:
            p = Path("img") / name
            if p.exists():
                try:
                    self.images[name] = PhotoImage(file=str(p))
                except Exception as e:  # noqa: BLE001
                    self.logger.warning("Image load failed: %s err=%s", p, e)
        if "app_icon_default_256.png" in self.images:
            self.images["app_icon_64"] = self.images[
                "app_icon_default_256.png"
            ].subsample(4, 4)

    def _build_ui(self) -> None:
        self.bg = Canvas(self.root, highlightthickness=0)
        self.bg.pack(fill=BOTH, expand=True)
        self.bg.bind("<Configure>", self._draw_gradient)

        self.container = ttk.Frame(self.bg)
        self.bg_window = self.bg.create_window(0, 0, anchor="nw", window=self.container)

        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(3, weight=1)

        self._build_topbar()
        self._build_center()
        self._build_input()
        self._build_history()
        self._build_actions()

    def _draw_gradient(self, event) -> None:
        self.bg.delete("grad")
        width = max(1, event.width)
        height = max(1, event.height)
        self.bg.itemconfig(self.bg_window, width=width, height=height)
        r1, g1, b1 = (15, 17, 23)
        r2, g2, b2 = (20, 24, 34)
        steps = 50
        for i in range(steps):
            ratio = i / steps
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            y1 = int(i * height / steps)
            y2 = int((i + 1) * height / steps)
            self.bg.create_rectangle(
                0, y1, width, y2, fill=color, outline="", tags="grad"
            )

    def _build_topbar(self) -> None:
        top = ttk.Frame(self.container, padding=(16, 16, 16, 8))
        top.grid(row=0, column=0, sticky=(E, W))
        top.columnconfigure(1, weight=1)

        icon = self.images.get("app_icon_64")
        if icon:
            ico_label = ttk.Label(top, image=icon)
            ico_label.grid(row=0, column=0, rowspan=2, sticky=W)
        else:
            ttk.Label(top, text="◎").grid(row=0, column=0, rowspan=2, sticky=W)

        ttk.Label(top, text="Антошка", font=self.font_title).grid(
            row=0, column=1, sticky=W, padx=12
        )
        ttk.Label(
            top,
            textvariable=self.status_var,
            font=self.font_sub,
            style="Sub.TLabel",
        ).grid(row=1, column=1, sticky=W, padx=12)

        gear = self.images.get("ui_gear_32.png")
        ttk.Button(
            top, image=gear, command=self._open_settings, style="Icon.TButton"
        ).grid(row=0, column=2, rowspan=2, sticky=E)

    def _build_center(self) -> None:
        center = ttk.Frame(self.container, padding=(16, 8, 16, 8))
        center.grid(row=1, column=0, sticky=(E, W))
        center.columnconfigure(0, weight=1)

        big_icon = self.images.get("app_icon_default_256.png")
        if big_icon:
            ttk.Label(center, image=big_icon).grid(row=0, column=0, pady=(4, 6))

        self.recognized = ttk.Label(
            center,
            text="Распознанно: —",
            font=self.font_body,
        )
        self.recognized.grid(row=1, column=0, sticky=W, pady=(8, 2))

        self.hint = ttk.Label(
            center,
            text="Подсказка: скажи «Антошка, что ты умеешь?»",
            font=self.font_sub,
            style="Sub.TLabel",
        )
        self.hint.grid(row=2, column=0, sticky=W)

    def _build_input(self) -> None:
        panel = ttk.Frame(self.container, padding=(16, 6, 16, 6))
        panel.grid(row=2, column=0, sticky=(E, W))
        panel.columnconfigure(0, weight=1)

        entry = ttk.Entry(panel, textvariable=self.input_var, font=self.font_body)
        entry.grid(row=0, column=0, sticky=(E, W))
        entry.bind("<Return>", lambda _: self._send_text())

        ttk.Button(panel, text="Отправить", command=self._send_text).grid(
            row=0, column=1, padx=8
        )

    def _build_history(self) -> None:
        frame = ttk.Frame(self.container, padding=(16, 6, 16, 6))
        frame.grid(row=3, column=0, sticky=(N, S, E, W))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.history = Text(
            frame,
            height=10,
            wrap="word",
            bg="#121726",
            fg="#d9e1ff",
            insertbackground="#d9e1ff",
            relief="flat",
            borderwidth=0,
        )
        self.history.grid(row=0, column=0, sticky=(N, S, E, W))
        self.history.configure(state="disabled")

    def _build_actions(self) -> None:
        row = ttk.Frame(self.container, padding=(16, 8, 16, 16))
        row.grid(row=4, column=0, sticky=(E, W))
        row.columnconfigure(5, weight=1)

        mic = self.images.get("ui_mic_32.png")
        stop = self.images.get("ui_stop_32.png")
        hist = self.images.get("ui_history_32.png")
        vol = self.images.get("ui_volume_32.png")
        spark = self.images.get("ui_sparkles_32.png")

        self.listen_button = ttk.Button(
            row, text="Слушать", image=mic, compound="left", command=self._listen
        )
        self.listen_button.grid(row=0, column=0, padx=4)

        ttk.Button(
            row, text="Стоп", image=stop, compound="left", command=self._stop_listen
        ).grid(row=0, column=1, padx=4)
        ttk.Button(
            row, text="История", image=hist, compound="left", command=self._open_history
        ).grid(row=0, column=2, padx=4)
        ttk.Button(
            row, text="Громкость", image=vol, compound="left", command=self._open_volume
        ).grid(row=0, column=3, padx=4)
        ttk.Button(
            row, text="ИИ режим", image=spark, compound="left", command=self._toggle_llm
        ).grid(row=0, column=4, padx=4)

    def _append_history(self, role: str, text: str) -> None:
        self.history.configure(state="normal")
        self.history.insert(END, f"{role}: {text}\n")
        self.history.configure(state="disabled")
        self.history.see(END)

    def _set_status(self, text: str) -> None:
        self.status_var.set(f"голосовой помощник • статус: {text}")

    def _notify(self, message: str) -> None:
        def _update() -> None:
            self._append_history("Антошка", message)
            self._set_status("говорю")
            self.tts.say(message)
            self._set_status("готов")

        self.root.after(0, _update)

    def _show_startup_diagnostics(self) -> None:
        messages = []

        if not self.settings.get("tts", {}).get("enabled", True):
            messages.append("TTS выключен в настройках.")
        elif self.tts.last_error:
            messages.append(f"TTS ошибка: {self.tts.last_error}")
        elif self.tts.provider != "edge" and self.tts.engine is None:
            messages.append("TTS недоступен: нет pyttsx3.")

        stt_raw = self.settings.get("stt", {}) or {}
        stt_mode = (stt_raw.get("mode") or "text").lower()
        if stt_mode in {"vosk", "auto"}:
            model_path = str(stt_raw.get("vosk_model_path") or "models/vosk")
            if not Path(model_path).exists():
                messages.append("Микрофон недоступен: модель Vosk не найдена.")
            if isinstance(self.stt, TextSTT):
                messages.append(
                    "Голосовой ввод недоступен: используйте текст или установите Vosk."
                )

        for msg in messages:
            self._append_history("Антошка", msg)

    def _init_tts(self) -> TTS:
        tts_raw = self.settings.get("tts", {}) or {}
        return TTS(
            TTSConfig(
                enabled=bool(tts_raw.get("enabled", True)),
                rate=int(tts_raw.get("rate", 180)),
                volume=float(tts_raw.get("volume", 1.0)),
                voice_name_contains=tts_raw.get("voice_name_contains"),
            )
        )

    def _init_llm(self):
        llm_raw = self.settings.get("llm", {}) or {}
        try:
            return LLMClient(
                LLMConfig(
                    provider=str(llm_raw.get("provider", "dummy")),
                    model=str(llm_raw.get("model", "gpt-4o-mini")),
                    history_max_messages=int(llm_raw.get("history_max_messages", 10)),
                )
            )
        except Exception as e:  # noqa: BLE001
            self.logger.warning("LLM disabled: %s", e)
            return None

    def _listen(self) -> None:
        if self.listening:
            return
        self.listening = True
        self._listen_token += 1
        token = self._listen_token
        self._set_status("слушаю")

        def _worker() -> None:
            text = self.stt.listen()
            self.root.after(0, lambda: self._on_listen_result(token, text))

        threading.Thread(target=_worker, daemon=True).start()

    def _stop_listen(self) -> None:
        if not self.listening:
            return
        self._listen_token += 1
        self.listening = False
        try:
            self.stt.stop()
        except Exception:
            pass
        self._set_status("остановлено")

    def _on_listen_result(self, token: int, text: str | None) -> None:
        if token != self._listen_token:
            return
        self.listening = False
        if text is None:
            self._set_status("остановлено")
            return
        self.recognized.configure(
            text=f"Распознанно: «{text}»" if text else "Распознанно: —"
        )
        self.input_var.set(text or "")
        if text and text.strip():
            self._process_text(text)
        else:
            self._set_status("готов")

    def _send_text(self) -> None:
        text = self.input_var.get().strip()
        if not text:
            return
        self._process_text(text)

    def _process_text(self, text: str) -> None:
        self._append_history("Вы", text)
        self.input_var.set("")
        self.recognized.configure(text=f"Распознанно: «{text}»")
        self._set_status("думаю")

        def _worker() -> None:
            answer = self.dialogue.handle_text(text)
            if answer == "__EXIT__":
                self.root.after(0, self.root.destroy)
                return

            def _update() -> None:
                self._append_history("Антошка", answer)
                self._set_status("говорю")
                self.tts.say(answer)
                self._set_status("готов")

            self.root.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()

    def _open_settings(self) -> None:
        win = Toplevel(self.root)
        win.title("Настройки")
        win.geometry("420x240")

        tts_enabled = BooleanVar(
            value=bool(self.settings.get("tts", {}).get("enabled", True))
        )
        stt_mode = StringVar(
            value=str(self.settings.get("stt", {}).get("mode", "text"))
        )
        wake_word = BooleanVar(
            value=bool(self.settings.get("ui", {}).get("wake_word", False))
        )

        ttk.Label(win, text="STT режим").grid(
            row=0, column=0, sticky=W, padx=10, pady=10
        )
        ttk.Combobox(
            win,
            textvariable=stt_mode,
            values=["auto", "text", "vosk"],
            state="readonly",
        ).grid(row=0, column=1, sticky=E, padx=10, pady=10)

        ttk.Checkbutton(win, text="TTS включен", variable=tts_enabled).grid(
            row=1, column=0, columnspan=2, sticky=W, padx=10, pady=6
        )

        ttk.Checkbutton(win, text="Wake word: Антошка", variable=wake_word).grid(
            row=2, column=0, columnspan=2, sticky=W, padx=10, pady=6
        )

        def _save() -> None:
            self.settings.setdefault("stt", {})["mode"] = stt_mode.get()
            self.settings.setdefault("tts", {})["enabled"] = bool(tts_enabled.get())
            self.settings.setdefault("ui", {})["wake_word"] = bool(wake_word.get())
            save_settings(self.settings)
            win.destroy()

        ttk.Button(win, text="Сохранить", command=_save).grid(
            row=3, column=0, columnspan=2, padx=10, pady=16
        )

    def _open_history(self) -> None:
        win = Toplevel(self.root)
        win.title("История")
        win.geometry("520x420")

        history = read_json(Path("data") / "history.json", default=[])
        box = Text(win, wrap="word")
        box.pack(fill=BOTH, expand=True)
        for item in history:
            role = item.get("role", "")
            text = item.get("text", "")
            ts = item.get("ts", "")
            box.insert(END, f"[{ts}] {role}: {text}\n")
        box.configure(state="disabled")

    def _open_volume(self) -> None:
        if self.app_context.volume is None:
            self._notify("Не могу изменить громкость на этом устройстве.")
            return

        win = Toplevel(self.root)
        win.title("Громкость")
        win.geometry("320x140")

        current = self.app_context.volume.get_level()
        current = 1.0 if current is None else current
        volume_var = StringVar(value=str(int(current * 100)))

        ttk.Label(win, text="Громкость (0-100)").pack(pady=8)
        slider = ttk.Scale(
            win,
            from_=0,
            to=100,
            orient="horizontal",
            command=lambda v: volume_var.set(str(int(float(v)))),
        )
        slider.set(current * 100)
        slider.pack(fill=BOTH, padx=16)

        ttk.Label(win, textvariable=volume_var).pack(pady=6)

        def _apply() -> None:
            level = max(0, min(100, int(volume_var.get()))) / 100.0
            self.app_context.volume.set_level(level)
            win.destroy()

        ttk.Button(win, text="Применить", command=_apply).pack(pady=6)

    def _toggle_llm(self) -> None:
        llm_raw = self.settings.get("llm", {}) or {}
        provider = llm_raw.get("provider", "dummy")
        if provider == "dummy":
            if self.llm_client is None:
                self._notify("ИИ недоступен. Проверь ключ и настройки.")
                return
            llm_raw["provider"] = "openai"
            self._notify("ИИ включен.")
        else:
            llm_raw["provider"] = "dummy"
            self._notify("ИИ выключен.")
        self.settings["llm"] = llm_raw
        save_settings(self.settings)

        self.llm_client = self._init_llm()
        self.app_context.llm_client = self.llm_client
        self.dialogue = Dialogue(
            DialogueConfig(
                dangerous_mode=bool(
                    self.settings.get("safety", {}).get("dangerous_mode", False)
                ),
                llm_client=self.llm_client,
                app_context=self.app_context,
            )
        )
