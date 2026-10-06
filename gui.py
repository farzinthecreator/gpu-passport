"""GPU Passport window app.

Run:       python gui.py
Demo:      python gui.py --mock        (simulated RTX 3070, for PCs without an NVIDIA card)
Self-test: python gui.py --mock --selftest
Options:   --theme=light|dark  --screen=create|verify  (for screenshots)
"""
import ctypes
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser

import gpupassport as gp

VERSION = "0.4.0"
MOCK = "--mock" in sys.argv
REPO = "https://github.com/farzinthecreator/gpu-passport"

LIGHT = dict(bg="#F6F6F4", surface="#FFFFFF", subtle="#EFEFEC", border="#E2E2DE", text="#18191B", muted="#6A6E75",
             accent="#1F5FD1", accent_hover="#1A50B3", on_accent="#FFFFFF", focus="#1F5FD1",
             ok="#1E7A4C", ok_bg="#E8F4ED", bad="#B42318", bad_bg="#FCECEA", warn="#9A5B00", warn_bg="#FCF3E2")
DARK = dict(bg="#141516", surface="#1D1E20", subtle="#26282B", border="#303236", text="#ECEDEF", muted="#9AA0A8",
            accent="#6E9BFF", accent_hover="#88ADFF", on_accent="#0E1116", focus="#6E9BFF",
            ok="#4CC38A", ok_bg="#14281D", bad="#FF7B70", bad_bg="#301B19", warn="#F0B35B", warn_bg="#2D2414")
LEVELS = {"ok": ("✓", "ok", "ok_bg"), "fail": ("✕", "bad", "bad_bg"), "warn": ("!", "warn", "warn_bg")}


def enable_sharp_text():
    """Without this, Windows stretches the window on high-DPI screens and everything looks blurry."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def windows_dark_mode():
    if "--theme=dark" in sys.argv or "--theme=light" in sys.argv:
        return "--theme=dark" in sys.argv
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except (ImportError, OSError):
        return False


def load_gpus():
    """read_gpus() exits with a message meant for the terminal; turn that into (None, message) for the window."""
    try:
        return gp.read_gpus(mock=MOCK), None
    except SystemExit as e:
        return None, str(e.code)


class Button(tk.Label):
    """Flat button that works with mouse (hover, click) and keyboard (Tab, Enter, Space)."""

    def __init__(self, parent, app, text, command, primary=False):
        c = app.c
        self.normal, self.hover = (c["accent"], c["accent_hover"]) if primary else (c["surface"], c["subtle"])
        super().__init__(parent, text=text, bg=self.normal, fg=c["on_accent"] if primary else c["text"],
                         font=app.f_button, padx=app.s(16), pady=app.s(7), cursor="hand2", takefocus=1,
                         highlightthickness=1, highlightcolor=c["focus"],
                         highlightbackground=c["accent"] if primary else c["border"])
        for event in ("<Button-1>", "<Return>", "<space>"):
            self.bind(event, lambda _: command())
        self.bind("<Enter>", lambda _: self.configure(bg=self.hover))
        self.bind("<Leave>", lambda _: self.configure(bg=self.normal))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.dark = windows_dark_mode()
        self.c = DARK if self.dark else LIGHT
        self.scale = self.winfo_fpixels("1i") / 96
        self.title("GPU Passport")
        # Fit small screens and laptops at 150-200% scaling; leave room for the taskbar.
        width = min(self.s(720), self.winfo_screenwidth() - self.s(40))
        height = min(self.s(700), self.winfo_screenheight() - self.s(100))
        x, y = (self.winfo_screenwidth() - width) // 2, max(0, (self.winfo_screenheight() - height) // 2 - self.s(20))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(width, self.s(600)), min(height, self.s(520)))
        try:
            self.icon = tk.PhotoImage(file=str(gp.APP_DIR / "icon.png"))  # made by tools/make_icon.py
            self.iconphoto(True, self.icon)
        except tk.TclError:
            pass  # missing icon file: keep the default icon rather than fail to start
        self.configure(bg=self.c["bg"])
        self.setup_fonts()
        self.last_link = None     # read by the self-test
        self.last_verdict = None  # read by the self-test
        self.body = tk.Frame(self, bg=self.c["bg"])
        self.body.pack(fill="both", expand=True, padx=self.s(36), pady=self.s(28))
        self.update_idletasks()
        self.dark_title_bar()
        self.home()

    # ---- setup ---------------------------------------------------------
    def s(self, px):
        """Logical pixels -> screen pixels, so spacing matches the sharper, DPI-aware text."""
        return round(px * self.scale)

    def setup_fonts(self):
        families = set(tkfont.families(self))
        display = "Segoe UI Variable Display" if "Segoe UI Variable Display" in families else "Segoe UI"
        body = "Segoe UI Variable Text" if "Segoe UI Variable Text" in families else "Segoe UI"
        mono = "Cascadia Mono" if "Cascadia Mono" in families else "Consolas"
        self.f_h1, self.f_h2, self.f_verdict = (display, 22, "bold"), (display, 16, "bold"), (display, 26, "bold")
        self.f_h3, self.f_body, self.f_body_bold = (body, 12, "bold"), (body, 10), (body, 10, "bold")
        self.f_small, self.f_small_bold, self.f_button, self.f_mono = (body, 9), (body, 9, "bold"), (body, 10, "bold"), (mono, 9)

    def dark_title_bar(self):
        if not self.dark:
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            on = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))  # 20 = immersive dark mode
        except (AttributeError, OSError):
            pass

    # ---- building blocks -----------------------------------------------
    def clear(self):
        for widget in self.body.winfo_children():
            widget.destroy()

    def label(self, parent, text, font=None, color="text", bg="bg", pady=(0, 0), wrap=620, **pack):
        widget = tk.Label(parent, text=text, font=font or self.f_body, fg=self.c[color], bg=self.c[bg],
                          wraplength=self.s(wrap), justify="left", anchor="w")
        widget.pack(fill="x", pady=(self.s(pady[0]), self.s(pady[1])), **pack)
        return widget

    def top_bar(self, back=True):
        bar = tk.Frame(self.body, bg=self.c["bg"])
        bar.pack(fill="x", pady=(0, self.s(22)))
        if back:
            link = tk.Label(bar, text="← Back", font=self.f_body_bold, fg=self.c["accent"], bg=self.c["bg"],
                            cursor="hand2", takefocus=1)
            link.pack(side="left")
            for event in ("<Button-1>", "<Return>", "<space>"):
                link.bind(event, lambda _: self.home())
        tk.Label(bar, text=f"v{VERSION}" + ("  ·  demo mode" if MOCK else ""), font=self.f_small,
                 fg=self.c["muted"], bg=self.c["bg"]).pack(side="right")

    def panel(self, parent=None, pady=(0, 16)):
        box = tk.Frame(parent or self.body, bg=self.c["surface"], highlightthickness=1,
                       highlightbackground=self.c["border"])
        box.pack(fill="x", pady=(self.s(pady[0]), self.s(pady[1])))
        return box

    def badge(self, parent, level, text, bg="bg"):
        icon, fg, tint = LEVELS[level]
        row = tk.Frame(parent, bg=self.c[bg])
        row.pack(fill="x", anchor="w")
        tk.Label(row, text=f"{icon}  {text}", font=self.f_small_bold, fg=self.c[fg], bg=self.c[tint],
                 padx=self.s(10), pady=self.s(4), wraplength=self.s(600), justify="left").pack(side="left")

    def details(self, rows):
        box = self.panel()
        for i, (name, value, mono) in enumerate(rows):
            if i:
                tk.Frame(box, bg=self.c["border"], height=1).pack(fill="x")
            row = tk.Frame(box, bg=self.c["surface"])
            row.pack(fill="x", padx=self.s(16), pady=self.s(9))
            tk.Label(row, text=name, font=self.f_body, fg=self.c["muted"], bg=self.c["surface"]).pack(side="left")
            tk.Label(row, text=value, font=self.f_mono if mono else self.f_body, fg=self.c["text"],
                     bg=self.c["surface"]).pack(side="right")

    def tile(self, title, description, command):
        c = self.c
        tile = tk.Frame(self.body, bg=c["surface"], highlightthickness=1, highlightbackground=c["border"],
                        cursor="hand2", takefocus=1, highlightcolor=c["focus"])
        tile.pack(fill="x", pady=(0, self.s(12)))
        inner = tk.Frame(tile, bg=c["surface"])
        inner.pack(fill="x", padx=self.s(22), pady=self.s(18))
        arrow = tk.Label(inner, text="→", font=self.f_h2, fg=c["muted"], bg=c["surface"])
        arrow.pack(side="right")
        name = tk.Label(inner, text=title, font=self.f_h3, fg=c["text"], bg=c["surface"], anchor="w")
        name.pack(fill="x")
        desc = tk.Label(inner, text=description, font=self.f_body, fg=c["muted"], bg=c["surface"], anchor="w")
        desc.pack(fill="x", pady=(self.s(2), 0))
        parts = (tile, inner, arrow, name, desc)

        def hover(on):
            for widget in parts:
                widget.configure(bg=c["subtle"] if on else c["surface"])
            tile.configure(highlightbackground=c["accent"] if on else c["border"])
            arrow.configure(fg=c["accent"] if on else c["muted"])

        for widget in parts:
            widget.bind("<Enter>", lambda _: hover(True))
            widget.bind("<Leave>", lambda _: hover(False))
            widget.bind("<Button-1>", lambda _: command())
        tile.bind("<Return>", lambda _: command())
        tile.bind("<space>", lambda _: command())

    def entry(self, text="", readonly=False, mono=False):
        c = self.c
        box = tk.Entry(self.body, font=self.f_mono if mono else self.f_body, relief="flat", bg=c["surface"],
                       fg=c["text"], insertbackground=c["text"], highlightthickness=1,
                       highlightbackground=c["border"], highlightcolor=c["focus"],
                       readonlybackground=c["subtle"])
        box.insert(0, text)
        if readonly:
            box.configure(state="readonly")
        box.pack(fill="x", ipady=self.s(8), pady=(0, self.s(10)))
        return box

    # ---- screens -------------------------------------------------------
    def home(self):
        self.clear()
        self.top_bar(back=False)
        self.label(self.body, "GPU Passport", self.f_h1)
        self.label(self.body, "Prove a used graphics card is genuine, and is the exact card you were sold.",
                   color="muted", pady=(4, 26))
        self.tile("I'm selling a card", "Create a passport link to put in your listing.", self.create)
        self.tile("I bought a card", "Check the card in this PC against the seller's passport link.", self.verify_screen)

        self.label(self.body, "How it works", self.f_small_bold, color="muted", pady=(18, 8))
        for number, step in enumerate(("The seller creates a passport. It records the card's unique hardware ID.",
                                       "The buyer opens the passport link before paying.",
                                       "When the card arrives, the buyer checks it here: PASS or FAIL."), 1):
            row = tk.Frame(self.body, bg=self.c["bg"])
            row.pack(fill="x", pady=(0, self.s(6)))
            tk.Label(row, text=str(number), font=self.f_small_bold, fg=self.c["accent"], bg=self.c["bg"],
                     width=2, anchor="w").pack(side="left")
            tk.Label(row, text=step, font=self.f_body, fg=self.c["text"], bg=self.c["bg"], anchor="w").pack(side="left")

        footer = tk.Label(self.body, text="NVIDIA cards  ·  Free and open source  ·  github.com/farzinthecreator/gpu-passport",
                          font=self.f_small, fg=self.c["muted"], bg=self.c["bg"], cursor="hand2", anchor="w")
        footer.pack(side="bottom", fill="x")
        footer.bind("<Button-1>", lambda _: webbrowser.open(REPO))

    def create(self):
        self.clear()
        self.top_bar()
        gpus, error = load_gpus()
        if error:
            self.label(self.body, "No NVIDIA card found", self.f_h2, pady=(0, 10))
            self.badge(self.body, "fail", error)
            return
        gpu = gpus[0]  # ponytail: first GPU only; add a picker if sellers with several cards show up
        status, detail = gp.spec_check(gpu)
        passport = gp.make_passport(gpu)
        self.last_link = gp.SITE + "#" + gp.encode(passport)

        self.label(self.body, "Your card", self.f_small_bold, color="muted")
        self.label(self.body, gpu["name"], self.f_h2, pady=(2, 10))
        self.badge(self.body, {"ok": "ok", "mismatch": "fail"}.get(status, "warn"), detail)
        tk.Frame(self.body, bg=self.c["bg"], height=self.s(16)).pack()
        self.details([
            ("Memory", f"{gpu['vram_mib'] / 1024:.0f} GB  ({gpu['vram_mib']} MiB)", False),
            ("Device ID", f"10DE:{gpu['device_id'].upper()}", True),
            ("BIOS", gpu["vbios"], True),
            ("Driver", gpu["driver"], True),
            ("Hardware ID (hashed)", passport["uuid_hash"][:16] + "…", True),
            ("Passport date", passport["created"], False),
        ])

        self.label(self.body, "Passport link", self.f_small_bold, color="muted", pady=(6, 6))
        self.entry(self.last_link, readonly=True, mono=True)
        row = tk.Frame(self.body, bg=self.c["bg"])
        row.pack(fill="x")
        copied = tk.Label(row, text="", font=self.f_small_bold, fg=self.c["ok"], bg=self.c["bg"])

        def copy():
            self.clipboard_clear()
            self.clipboard_append(self.last_link)
            copied.configure(text="✓ Copied to clipboard")

        Button(row, self, "Copy link", copy, primary=True).pack(side="left")
        Button(row, self, "Open passport page", lambda: webbrowser.open(self.last_link)).pack(side="left", padx=self.s(8))
        copied.pack(side="left", padx=self.s(4))
        self.label(self.body, "Paste this link in your listing. When the card arrives, the buyer opens GPU Passport, "
                              "clicks “I bought a card” and pastes it.", color="muted", pady=(16, 0))

    def verify_screen(self):
        self.clear()
        self.top_bar()
        self.label(self.body, "Check a card you bought", self.f_h2)
        self.label(self.body, "Install the card in this PC, then paste the passport link from the seller's listing.",
                   color="muted", pady=(4, 18))
        link_box = self.entry(mono=True)
        link_box.focus_set()
        row = tk.Frame(self.body, bg=self.c["bg"])
        row.pack(fill="x", pady=(0, self.s(20)))
        self.result = tk.Frame(self.body, bg=self.c["bg"])
        self.result.pack(fill="both", expand=True)

        def paste():
            try:
                link_box.delete(0, "end")
                link_box.insert(0, self.clipboard_get().strip())
            except tk.TclError:  # clipboard empty or not text
                pass

        Button(row, self, "Check card", lambda: self.run_verify(link_box.get()), primary=True).pack(side="left")
        Button(row, self, "Paste link", paste).pack(side="left", padx=self.s(8))
        link_box.bind("<Return>", lambda _: self.run_verify(link_box.get()))

    def verdict(self, ok, title, subtitle):
        tint, color = ("ok_bg", "ok") if ok else ("bad_bg", "bad")
        banner = tk.Frame(self.result, bg=self.c[tint])
        banner.pack(fill="x", pady=(0, self.s(14)))
        tk.Frame(banner, bg=self.c[color], width=self.s(5)).pack(side="left", fill="y")
        text = tk.Frame(banner, bg=self.c[tint])
        text.pack(side="left", fill="x", padx=self.s(18), pady=self.s(14))
        tk.Label(text, text=title, font=self.f_verdict, fg=self.c[color], bg=self.c[tint], anchor="w").pack(fill="x")
        tk.Label(text, text=subtitle, font=self.f_body_bold, fg=self.c[color], bg=self.c[tint], anchor="w",
                 wraplength=self.s(560), justify="left").pack(fill="x")

    def run_verify(self, link):
        for widget in self.result.winfo_children():
            widget.destroy()
        self.last_verdict = None
        try:
            passport = gp.decode(link)
        except ValueError as e:
            self.verdict(False, "Invalid link", str(e))
            return
        gpus, error = load_gpus()
        if error:
            self.verdict(False, "No NVIDIA card found", error)
            return
        ok, checks = gp.verify(passport, gpus)
        self.last_verdict = "PASS" if ok else "FAIL"
        self.verdict(ok, self.last_verdict,
                     "Same physical card, genuine model." if ok else "Don't accept this card. See the details below.")
        box = self.panel(self.result, pady=(0, 0))
        for i, (level, text) in enumerate(checks):
            if i:
                tk.Frame(box, bg=self.c["border"], height=1).pack(fill="x")
            icon, color, _ = LEVELS[level]
            row = tk.Frame(box, bg=self.c["surface"])
            row.pack(fill="x", padx=self.s(16), pady=self.s(10))
            tk.Label(row, text=icon, font=self.f_body_bold, fg=self.c[color], bg=self.c["surface"], width=2,
                     anchor="nw").pack(side="left", anchor="n")
            tk.Label(row, text=text, font=self.f_body, fg=self.c["text"], bg=self.c["surface"], anchor="w",
                     justify="left", wraplength=self.s(560)).pack(side="left", fill="x")


def selftest():
    """Drives the real window through create -> verify and checks the verdict. Needs --mock."""
    app = App()
    app.create()
    link = app.last_link
    app.verify_screen()
    app.run_verify(link)
    assert app.last_verdict == "PASS", app.last_verdict
    app.run_verify(link.replace("#", "#x"))  # damaged link must be rejected, not crash
    assert app.last_verdict is None
    app.home()
    app.destroy()
    print("GUI self-test OK")


if __name__ == "__main__":
    enable_sharp_text()
    if "--selftest" in sys.argv:
        selftest()
    else:
        app = App()
        if "--screen=create" in sys.argv:  # open a screen directly, for README screenshots
            app.create()
        elif "--screen=verify" in sys.argv:
            app.create()
            link = app.last_link
            app.verify_screen()
            app.run_verify(link)
        app.mainloop()
