"""GPU Passport window app.

Run:       python gui.py
Demo:      python gui.py --mock        (simulated RTX 3070, for PCs without an NVIDIA card)
Self-test: python gui.py --mock --selftest
"""
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk

import gpupassport as gp

MOCK = "--mock" in sys.argv
GREEN, RED, AMBER, MUTED = "#1a7f37", "#c62828", "#a15c00", "#5d6470"
WRAP = 540


def load_gpus():
    """read_gpus() exits with a message meant for the terminal; turn that into (None, message) for the window."""
    try:
        return gp.read_gpus(mock=MOCK), None
    except SystemExit as e:
        return None, str(e.code)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPU Passport")
        self.geometry("640x560")
        self.minsize(560, 480)
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Card.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Big.TButton", font=("Segoe UI", 12), padding=14)
        self.last_link = None     # read by the self-test
        self.last_verdict = None  # read by the self-test
        self.body = ttk.Frame(self, padding=24)
        self.body.pack(fill="both", expand=True)
        self.home()

    # ---- helpers -------------------------------------------------------
    def clear(self):
        for widget in self.body.winfo_children():
            widget.destroy()

    def text(self, parent, text, color=None, font=None, pady=(0, 6)):
        label = ttk.Label(parent, text=text, wraplength=WRAP, foreground=color, font=font, justify="left")
        label.pack(anchor="w", pady=pady)
        return label

    def back(self):
        ttk.Button(self.body, text="← Back", command=self.home).pack(anchor="w", pady=(0, 16))

    # ---- screens -------------------------------------------------------
    def home(self):
        self.clear()
        ttk.Label(self.body, text="GPU Passport", style="Title.TLabel").pack(anchor="w")
        self.text(self.body, "Prove a used graphics card is real, and is the card you were sold.", MUTED, pady=(4, 24))
        ttk.Button(self.body, text="I'm selling a card\nCreate a passport link for my listing",
                   style="Big.TButton", command=self.create).pack(fill="x", pady=6)
        ttk.Button(self.body, text="I bought a card\nCheck it against the passport link",
                   style="Big.TButton", command=self.verify_screen).pack(fill="x", pady=6)
        if MOCK:
            self.text(self.body, "Demo mode: using a simulated RTX 3070.", AMBER, pady=(16, 0))
        self.text(self.body, "NVIDIA cards only for now.", MUTED, pady=(16, 0))

    def create(self):
        self.clear()
        self.back()
        gpus, error = load_gpus()
        if error:
            self.text(self.body, error, RED)
            return
        gpu = gpus[0]  # ponytail: first GPU only; add a picker if sellers with several cards show up
        status, detail = gp.spec_check(gpu)
        self.last_link = gp.SITE + "#" + gp.encode(gp.make_passport(gpu))

        ttk.Label(self.body, text=gpu["name"], style="Card.TLabel").pack(anchor="w")
        self.text(self.body, f"{gpu['vram_mib'] // 1024} GB memory · BIOS {gpu['vbios']}", MUTED, pady=(2, 12))
        icon, color = {"ok": ("✓", GREEN), "mismatch": ("✗", RED)}.get(status, ("?", AMBER))
        self.text(self.body, f"{icon}  {detail}", color, pady=(0, 18))

        self.text(self.body, "Your passport link. Put it in your listing:")
        link_box = ttk.Entry(self.body)
        link_box.insert(0, self.last_link)
        link_box.configure(state="readonly")
        link_box.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(self.body)
        row.pack(anchor="w")
        copied = ttk.Label(row, text="", foreground=GREEN)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(self.last_link)
            copied.configure(text="Copied!")

        ttk.Button(row, text="Copy link", command=copy).pack(side="left")
        ttk.Button(row, text="Open passport page", command=lambda: webbrowser.open(self.last_link)).pack(side="left", padx=8)
        copied.pack(side="left")
        self.text(self.body, "When the card arrives, the buyer opens GPU Passport, clicks \"I bought a card\" "
                             "and pastes this link.", MUTED, pady=(18, 0))

    def verify_screen(self):
        self.clear()
        self.back()
        self.text(self.body, "Install the card in this PC, then paste the passport link from the listing:")
        link_box = ttk.Entry(self.body)
        link_box.pack(fill="x", pady=(0, 8))
        link_box.focus_set()
        row = ttk.Frame(self.body)
        row.pack(anchor="w", pady=(0, 16))
        result = ttk.Frame(self.body)
        result.pack(fill="both", expand=True)

        def paste():
            try:
                link_box.delete(0, "end")
                link_box.insert(0, self.clipboard_get().strip())
            except tk.TclError:  # clipboard empty or not text
                pass

        ttk.Button(row, text="Paste", command=paste).pack(side="left")
        ttk.Button(row, text="Check this card", command=lambda: self.run_verify(link_box.get(), result)).pack(side="left", padx=8)
        link_box.bind("<Return>", lambda _: self.run_verify(link_box.get(), result))
        self.result = result

    def run_verify(self, link, result=None):
        result = result or self.result
        for widget in result.winfo_children():
            widget.destroy()
        try:
            passport = gp.decode(link)
        except ValueError as e:
            self.last_verdict = None
            self.text(result, str(e), RED)
            return
        gpus, error = load_gpus()
        if error:
            self.last_verdict = None
            self.text(result, error, RED)
            return
        ok, messages = gp.verify(passport, gpus)
        self.last_verdict = "PASS" if ok else "FAIL"
        self.text(result, self.last_verdict, GREEN if ok else RED, ("Segoe UI", 26, "bold"), pady=(0, 2))
        self.text(result, "Same physical card, genuine model." if ok else "Don't accept this card.",
                  GREEN if ok else RED, ("Segoe UI", 12, "bold"), pady=(0, 12))
        for message in messages:
            self.text(result, "•  " + message)


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
    app.destroy()
    print("GUI self-test OK")


if __name__ == "__main__":
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
