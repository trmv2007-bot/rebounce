from __future__ import annotations

import argparse
import os
import webbrowser
import tkinter as tk
from tkinter import ttk

STATES = {
    "idle": "Ready", "listening": "Listening", "thinking": "Thinking",
    "speaking": "Speaking", "curious": "Curious", "working": "Working",
    "away": "Away", "error": "Needs attention",
}

class DesktopPresence:
    """Small cross-platform Tkinter presence client for ReBounce."""

    def __init__(self, *, api_url: str, name: str = "ReBounce", mode: str = "compact") -> None:
        self.api_url = api_url.rstrip("/")
        self.name = name
        self.mode = mode
        self.root = tk.Tk()
        self.root.title(name)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b1622")
        self._drag_x = 0
        self._drag_y = 0
        frame = tk.Frame(self.root, bg="#0b1622", padx=12, pady=10)
        frame.pack(fill="both", expand=True)
        self.orb = tk.Canvas(frame, width=52, height=52, highlightthickness=0, bg="#0b1622")
        self.orb.pack(side="left")
        self.orb.create_oval(7, 7, 45, 45, fill="#78d5ff", outline="")
        right = tk.Frame(frame, bg="#0b1622")
        right.pack(side="left", padx=(8, 0))
        self.title = tk.Label(right, text=name, fg="#eef5fb", bg="#0b1622", font=("Segoe UI", 11, "bold"))
        self.title.pack(anchor="w")
        self.status = tk.Label(right, text="Ready", fg="#8fa4b8", bg="#0b1622", font=("Segoe UI", 9))
        self.status.pack(anchor="w")
        buttons = tk.Frame(right, bg="#0b1622")
        buttons.pack(anchor="w", pady=(6, 0))
        ttk.Button(buttons, text="Open", command=self.open_dashboard).pack(side="left")
        ttk.Button(buttons, text="Hide", command=self.hide).pack(side="left", padx=5)
        ttk.Button(buttons, text="Quit", command=self.root.destroy).pack(side="left")
        for widget in (frame, self.orb, right, self.title, self.status):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
        self.root.geometry("240x92+40+40")

    def _start_drag(self, event) -> None:
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag(self, event) -> None:
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def set_state(self, state: str) -> None:
        self.status.config(text=STATES.get(state, state))

    def open_dashboard(self) -> None:
        webbrowser.open(self.api_url + "/")

    def hide(self) -> None:
        self.root.withdraw()
        self.root.after(1200, self.root.deiconify)

    def run(self) -> None:
        self.root.mainloop()

def main() -> None:
    parser = argparse.ArgumentParser(description="ReBounce desktop presence")
    parser.add_argument("--api-url", default=os.getenv("REBOUNCE_API_URL", "http://127.0.0.1:4100"))
    parser.add_argument("--name", default=os.getenv("REBOUNCE_COMPANION_NAME", "ReBounce"))
    parser.add_argument("--mode", choices=("compact", "pet", "overlay"), default="compact")
    args = parser.parse_args()
    DesktopPresence(api_url=args.api_url, name=args.name, mode=args.mode).run()

if __name__ == "__main__":
    main()
