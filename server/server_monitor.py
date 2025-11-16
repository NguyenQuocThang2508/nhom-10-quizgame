import threading
import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from server.ui_logger import ui_logger
from server.server import main as server_main


class ServerMonitorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Quiz Server Monitor')
        self.root.geometry('900x600')

        # Layout: left (logs) | right (stats)
        container = tk.Frame(root)
        container.pack(fill='both', expand=True)

        left = tk.Frame(container)
        left.pack(side='left', fill='both', expand=True)

        right = tk.Frame(container, width=320)
        right.pack(side='right', fill='y')
        right.pack_propagate(False)

        # Left: scrollable Text for logs
        lbl_logs = tk.Label(left, text='Server Logs', font=('Segoe UI', 11, 'bold'))
        lbl_logs.pack(anchor='w', padx=8, pady=(8, 4))

        txt_frame = tk.Frame(left)
        txt_frame.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        self.txt_logs = tk.Text(txt_frame, wrap='word', state='disabled', font=('Consolas', 10))
        yscroll = ttk.Scrollbar(txt_frame, orient='vertical', command=self.txt_logs.yview)
        self.txt_logs.configure(yscrollcommand=yscroll.set)

        self.txt_logs.pack(side='left', fill='both', expand=True)
        yscroll.pack(side='right', fill='y')

        lbl_right = tk.Label(right, text='Status', font=('Segoe UI', 11, 'bold'))
        lbl_right.pack(anchor='w', padx=8, pady=(8, 4))

        # Active players list
        tk.Label(right, text='Online Players:').pack(anchor='w', padx=8)
        self.list_players = tk.Listbox(right, height=12)
        self.list_players.pack(fill='x', padx=8, pady=(0, 12))

        # Score extremes
        frm_scores = tk.Frame(right)
        frm_scores.pack(fill='x', padx=8)
        tk.Label(frm_scores, text='Highest score:').grid(row=0, column=0, sticky='w')
        self.lbl_high = tk.Label(frm_scores, text='-')
        self.lbl_high.grid(row=0, column=1, sticky='w', padx=(6, 0))

        tk.Label(frm_scores, text='Lowest score:').grid(row=1, column=0, sticky='w', pady=(6, 0))
        self.lbl_low = tk.Label(frm_scores, text='-')
        self.lbl_low.grid(row=1, column=1, sticky='w', padx=(6, 0), pady=(6, 0))

        self._tick()

    def _append_logs(self, lines: List[str]) -> None:
        if not lines:
            return
        self.txt_logs.configure(state='normal')
        for ln in lines:
            try:
                self.txt_logs.insert('end', ln + '\n')
            except Exception:
                pass
        self.txt_logs.see('end')
        self.txt_logs.configure(state='disabled')

    def _refresh_players(self, names: List[str]) -> None:
        self.list_players.delete(0, 'end')
        for n in names:
            self.list_players.insert('end', n)

    def _refresh_scores(self, high: Optional[int], low: Optional[int]) -> None:
        self.lbl_high.config(text='-' if high is None else str(high))
        self.lbl_low.config(text='-' if low is None else str(low))

    def _tick(self) -> None:
        # pull new logs
        try:
            logs = ui_logger.drain_logs(500)
        except Exception:
            logs = []
        self._append_logs(logs)

        # refresh state
        try:
            names = ui_logger.get_active_names()
        except Exception:
            names = []
        self._refresh_players(names)

        try:
            high, low = ui_logger.get_score_extremes()
        except Exception:
            high, low = None, None
        self._refresh_scores(high, low)

        self.root.after(500, self._tick)


def _start_server_in_thread() -> threading.Thread:
    t = threading.Thread(target=server_main, daemon=True)
    t.start()
    return t


def run() -> None:
    # start server first so logs appear
    _start_server_in_thread()

    root = tk.Tk()
    app = ServerMonitorApp(root)
    root.mainloop()


if __name__ == '__main__':
    run()
