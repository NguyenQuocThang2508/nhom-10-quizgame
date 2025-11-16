"""Log panel: simple wrapper around a ScrolledText used by the GUI.

Responsibilities:
- Create the scrolling log widget
- Provide a thread-safe append() method used by other modules
"""

import tkinter as tk
from tkinter import scrolledtext


class LogPanel:
    """Encapsulate a scrolled text log area.

    Methods:
    - append(text): append a line (thread-safe via .after on master)
    """

    def __init__(self, master, font=('Consolas', 11), bg='#fbfdff'):
        self.master = master
        self.widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, font=font, bg=bg, state=tk.DISABLED, width=40)
        self.widget.pack(fill='both', expand=True, padx=8, pady=8)

    def append(self, text: str):
        """Append text to the log from any thread."""
        def _append():
            self.widget.configure(state=tk.NORMAL)
            self.widget.insert(tk.END, text + '\n')
            self.widget.see(tk.END)
            self.widget.configure(state=tk.DISABLED)

        # schedule on main thread
        try:
            self.master.after(0, _append)
        except Exception:
            # if master is gone or scheduling fails, try direct (best-effort)
            _append()
