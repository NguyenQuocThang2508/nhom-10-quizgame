"""Main window composition and UI glue code.

This module composes LogPanel, QuestionPanel and ClientNetwork.
It implements the join dialog and wiring between UI and network callbacks.
"""

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from client.gui.event_handler import ClientNetwork
from client.gui.log_panel import LogPanel
from client.gui.question_panel import QuestionPanel


class MainWindow:
    """Main application window that composes the UI and network client."""

    def __init__(self, master, host: str = '127.0.0.1', port: int = 65432):
        self.master = master
        self.host = host
        self.port = port
        self.current_qidx = None
        self._pending_name = None
        self._join_dialog = None
        self._joined_lobby = False
        self._offline_modal = None
        self._waiting_for_start = False

        master.title('Quiz Game Client')
        master.configure(bg='#f3f7fa')

        # Header + player name
        header = tk.Label(master, text='Quiz Game Client', font=('Helvetica', 20, 'bold'), bg='#f3f7fa')
        header.pack(pady=(8, 4))
        self.name_label = tk.Label(master, text='', font=('Helvetica', 10), bg='#f3f7fa')
        self.name_label.pack(anchor='ne', padx=12)

        # Main frame
        main_frame = tk.Frame(master, bg='#f3f7fa')
        main_frame.pack(fill='both', expand=True, padx=12, pady=6)

        # Left: LogPanel
        # create left frame for log but do NOT show it by default (keeps UI clean)
        self.left_frame = tk.Frame(main_frame, bg='#ffffff')
        self.log = LogPanel(self.left_frame)

        # Right: QuestionPanel
        self.question_panel = QuestionPanel(main_frame)
        self.question_panel.set_on_answer(self._on_answer_clicked)

        # Bottom: status and reconnect
        bottom = tk.Frame(master, bg='#f3f7fa')
        bottom.pack(fill='x', padx=12, pady=(4, 12))
        self.status_var = tk.StringVar(value='Disconnected')
        status = tk.Label(bottom, textvariable=self.status_var, bg='#f3f7fa', anchor='w')
        status.pack(side='left')
        # toggle for showing/hiding the log panel (hidden by default)
        self.toggle_log_btn = tk.Button(bottom, text='Show Log', command=self._toggle_log)
        self.toggle_log_btn.pack(side='right', padx=(6, 6))

        # Networking client
        self.net = ClientNetwork(host=self.host, port=self.port)
        self.net.on_question = self._on_network_question
        self.net.on_leaderboard = self._on_network_leaderboard
        self.net.on_eval = getattr(self, '_on_network_eval', None)
        # score callback (will be called when server sends SCORE|...)
        self.net.on_score = getattr(self, '_on_network_score', None)
        self.net.on_log = self._on_network_log
        self.net.on_disconnect = self._on_network_disconnect
        # name handshake callbacks
        self.net.on_name_ok = self._on_network_name_ok
        self.net.on_name_taken = self._on_network_name_taken
        self.net.on_error = self._on_network_error
        self.net.on_wait = self._on_network_wait
        self.net.on_start = self._on_network_start
        self.net.on_server_paused = self._on_network_server_paused
        self.net.on_game_started = self._on_network_game_started
        self.net.on_game_paused = self._on_network_game_paused

        # Start periodic probe; use async connect to keep UI responsive
        self.master.after(100, self._auto_probe_server)
        master.protocol('WM_DELETE_WINDOW', self._on_close)

        # log hidden by default
        self._log_visible = False
        # Note: left_frame is not packed so the question panel fills the space

    def _on_network_log(self, text: str):
        self.log.append(text)

    def _on_network_question(self, qidx, qtext, opts):
        # schedule UI work on main thread
        self.master.after(0, lambda: self._show_question(qidx, qtext, opts))

    def _on_network_leaderboard(self, payload: str):
        self.master.after(0, lambda: self._show_leaderboard(payload))

    def _on_network_name_ok(self):
        def show():
            self._set_status('Đã vào lobby - đang chờ server Start...')
            try:
                self.log.append('SERVER: NAME_OK')
            except Exception:
                pass
            try:
                if getattr(self, '_pending_name', None):
                    self.name_label.config(text=f'Player: {self._pending_name}')
            except Exception:
                pass
            self._waiting_for_start = True
            try:
                if self._join_dialog is not None:
                    self._join_dialog.grab_release()
                    self._join_dialog.destroy()
                    self._join_dialog = None
            except Exception:
                pass
        self.master.after(0, show)

    def _on_network_name_taken(self):
        def show():
            try:
                self.log.append('SERVER: NAME_TAKEN')
            except Exception:
                pass
            try:
                messagebox.showwarning('Tên bị trùng', 'Tên bị trùng, vui lòng nhập lại')
            except Exception:
                pass
            try:
                prev = getattr(self, '_pending_name', None)
                self._pending_name = None
                self.show_join_dialog(prev)
            except Exception:
                pass
        self.master.after(0, show)

    def _on_network_score(self, payload: str):
        # payload example: '3/5' -> points/total
        def show():
            try:
                # show a custom end-of-game panel with score and a Finish button
                # parse payload like '6/10'
                pts = payload.split('/', 1)[0] if '/' in payload else payload
                try:
                    pts_int = int(pts)
                except Exception:
                    pts_int = None

                dlg = tk.Toplevel(self.master)
                dlg.title('Kết thúc trò chơi')
                dlg.transient(self.master)
                dlg.grab_set()
                dlg.geometry('320x180')

                # Congratulatory message
                lbl_title = tk.Label(dlg, text='Chúc mừng!', font=('Helvetica', 16, 'bold'))
                lbl_title.pack(pady=(12, 6))

                score_text = f'Bạn đã đạt được: {pts}/10' if pts_int is not None else f'Điểm: {payload}'
                lbl_score = tk.Label(dlg, text=score_text, font=('Helvetica', 14))
                lbl_score.pack(pady=(6, 12))

                # optional details/log
                try:
                    self.log.append(f'Score received: {payload}')
                except Exception:
                    pass

                def finish():
                    try:
                        dlg.grab_release()
                    except Exception:
                        pass
                    try:
                        dlg.destroy()
                    except Exception:
                        pass
                    # close the main window / exit the quiz
                    try:
                        self._on_close()
                    except Exception:
                        pass

                btn = tk.Button(dlg, text='Hoàn thành', width=12, command=finish)
                btn.pack(pady=(8, 12))
                # center and wait
                try:
                    dlg.update_idletasks()
                    x = self.master.winfo_rootx() + (self.master.winfo_width() - dlg.winfo_width()) // 2
                    y = self.master.winfo_rooty() + (self.master.winfo_height() - dlg.winfo_height()) // 2
                    dlg.geometry(f'+{x}+{y}')
                except Exception:
                    pass
            except Exception:
                pass

        self.master.after(0, show)

    def _on_network_disconnect(self):
        self.master.after(0, self._handle_disconnect)

    def _on_network_error(self, message: str):
        def show():
            try:
                self.log.append(f'SERVER ERROR: {message}')
            except Exception:
                pass
            try:
                messagebox.showerror('Lỗi', message)
            except Exception:
                pass
            if 'Tên đã được sử dụng' in message or 'already' in message.lower():
                prev = getattr(self, '_pending_name', None)
                self._pending_name = None
                self.show_join_dialog(prev)
        self.master.after(0, show)

    def _on_network_wait(self):
        def show():
            self._set_status('Chờ server Start...')
            try:
                self.log.append('SERVER: WAIT (đang chờ Start)')
            except Exception:
                pass
        self.master.after(0, show)

    def _on_network_start(self):
        def show():
            self._set_status('Game bắt đầu!')
            try:
                self.log.append('SERVER: START - Game bắt đầu!')
            except Exception:
                pass
            self._waiting_for_start = False
            self._joined_lobby = True
            self._close_offline_modal()
            try:
                messagebox.showinfo('Bắt đầu!', 'Game đã bắt đầu!\nCâu hỏi sẽ được gửi tới ngay...')
            except Exception:
                pass
        self.master.after(0, show)

    def _on_network_server_paused(self, message: str):
        """Handle SERVER_PAUSED rejection from server."""
        # Chỉ hiển thị 1 lần duy nhất
        if getattr(self, '_server_paused_shown', False):
            return
        self._server_paused_shown = True
        
        def show():
            try:
                self.log.append(f'SERVER: {message}')
            except Exception:
                pass
            self._set_status('Server tạm ngưng')
            
            # Close ALL dialogs and modals
            try:
                if self._join_dialog is not None:
                    self._join_dialog.grab_release()
                    self._join_dialog.destroy()
                    self._join_dialog = None
            except Exception:
                pass
            
            try:
                self._close_offline_modal()
            except Exception:
                pass
            
            # Wait a bit to ensure all dialogs are closed
            def show_error():
                try:
                    messagebox.showinfo(
                        'Game đã đóng',
                        'Game đã bị đóng.\n\nXin vui lòng quay lại sau!'
                    )
                except Exception:
                    pass
                
                # Close the app after showing message
                try:
                    self._on_close()
                except Exception:
                    pass
            
            # Delay slightly to ensure join dialog closes first
            self.master.after(50, show_error)
            
        self.master.after(0, show)

    def _on_network_game_started(self, message: str):
        """Handle GAME_STARTED rejection from server (game đã bắt đầu, không cho join)."""
        # Chỉ hiển thị 1 lần duy nhất
        if getattr(self, '_game_started_shown', False):
            return
        self._game_started_shown = True
        
        def show():
            try:
                self.log.append(f'SERVER: {message}')
            except Exception:
                pass
            self._set_status('Game đã bắt đầu')
            
            # Close ALL dialogs and modals
            try:
                if self._join_dialog is not None:
                    self._join_dialog.grab_release()
                    self._join_dialog.destroy()
                    self._join_dialog = None
            except Exception:
                pass
            
            try:
                self._close_offline_modal()
            except Exception:
                pass
            
            # Wait a bit to ensure all dialogs are closed
            def show_error():
                try:
                    messagebox.showinfo(
                        'Game đã bắt đầu',
                        f'{message}\n\nKhông thể tham gia game đang diễn ra.'
                    )
                except Exception:
                    pass
                
                # Close the app after showing message
                try:
                    self._on_close()
                except Exception:
                    pass
            
            # Delay slightly to ensure join dialog closes first
            self.master.after(50, show_error)
            
        self.master.after(0, show)

    def _on_network_game_paused(self, message: str):
        """Handle GAME_PAUSED notification from server."""
        def show():
            try:
                self.log.append(f'SERVER: {message}')
            except Exception:
                pass
            self._set_status('Game tạm dừng')
            try:
                messagebox.showinfo(
                    'Game tạm dừng',
                    f'{message}\n\nVui lòng chờ server bật lại.'
                )
            except Exception:
                pass
        self.master.after(0, show)

    def _auto_probe_server(self):
        if self._joined_lobby or getattr(self, '_waiting_for_start', False):
            return
        
        if not self.net.running:
            self._set_status('Đang thử kết nối...')
            self._connect_async(1.0,
                                on_success=lambda: self._on_probe_success(),
                                on_failure=lambda: self._on_probe_failure_and_retry())
        else:
            if not self._joined_lobby and not getattr(self, '_waiting_for_start', False):
                self.master.after(1500, self._auto_probe_server)

    def _on_network_eval(self, tag: str, given: str):
        # tag is RIGHT or WRONG, given is the letter the client sent (or SKIP)
        def show():
            try:
                self.log.append(f'SERVER: EVAL|{tag}|{given}')
                try:
                    self.question_panel.show_eval(tag, given)
                except Exception:
                    pass
            except Exception:
                pass

        self.master.after(0, show)

    def _show_question(self, qidx, qtext, opts):
        self.question_panel.display_question(qidx, qtext, opts)
        self.question_panel.start_countdown(15)
        # store current question id so answer messages include it
        try:
            self.current_qidx = int(qidx) if isinstance(qidx, (int, str)) and str(qidx).isdigit() else qidx
        except Exception:
            self.current_qidx = qidx
        self._set_status('Question received')

    def _show_leaderboard(self, payload: str):
        # payload example name1:3;name2:2 or comma separated; show as log
        items = [p for p in payload.replace(';', ',').split(',') if p.strip()]
        lines = ['Leaderboard:'] + [it.replace(':', ' - ') for it in items]
        self.log.append('\n'.join(lines))

    def _handle_disconnect(self):
        self._set_status('Disconnected')
        try:
            if hasattr(self, 'reconnect_btn'):
                self.reconnect_btn.config(state=tk.NORMAL)
        except Exception:
            pass
        self.log.append('Disconnected from server')
        self.question_panel.stop_countdown()
        
        if not getattr(self, '_waiting_for_start', False) and not self._joined_lobby:
            self.master.after(1500, self._auto_probe_server)

    def _set_status(self, text: str):
        try:
            self.status_var.set(text)
        except Exception:
            pass

    def _toggle_log(self):
        if getattr(self, '_log_visible', False):
            self._hide_log()
        else:
            self._show_log()

    def _show_log(self):
        try:
            # pack the left frame so the LogPanel becomes visible
            # show the log as a fixed-width side panel so it doesn't collapse
            try:
                # set a reasonable fixed width for the log column and prevent
                # geometry propagation so the inner widget doesn't shrink the frame
                self.left_frame.config(width=320)
                self.left_frame.pack_propagate(False)
            except Exception:
                pass
            # pack left column vertically only; question panel keeps filling the
            # remaining horizontal space (it is packed on the right with expand=True)
            self.left_frame.pack(side='left', fill='y', padx=(0, 8))
            self._log_visible = True
            try:
                self.toggle_log_btn.config(text='Hide Log')
            except Exception:
                pass
        except Exception:
            pass

    def _hide_log(self):
        try:
            self.left_frame.pack_forget()
            self._log_visible = False
            try:
                self.toggle_log_btn.config(text='Show Log')
            except Exception:
                pass
        except Exception:
            pass

    def _on_answer_clicked(self, letter: str):
        # send answer via network client
        if not self.net.running:
            self.log.append('Not connected; cannot send answer')
            return
        # send ANSWER with qid (numeric qidx when available)
        qid = self.current_qidx if self.current_qidx is not None else self.question_panel.question_label.cget("text")
        # handle timeout case: QuestionPanel passes empty string on timeout
        send_letter = letter if letter else 'SKIP'
        try:
            self.net.send_line(f'ANSWER:{qid}|{send_letter}')
        except Exception:
            self.log.append('Failed to send answer')
            return
        if send_letter == 'SKIP':
            self.log.append('No answer (timed out) — turn skipped')
        else:
            self.log.append(f'You answered: {letter}')
        # ensure countdown is stopped (QuestionPanel also stops it when clicked)
        try:
            self.question_panel.stop_countdown()
        except Exception:
            pass

    def reconnect(self):
        if self.net.running:
            self.log.append('Already connected')
            return
        self._set_status('Connecting...')
        if hasattr(self, 'reconnect_btn'):
            try:
                self.reconnect_btn.config(state=tk.DISABLED)
            except Exception:
                pass
        ok = self.net.connect()
        if ok:
            self._set_status(f'Connected to {self.host}:{self.port}')
            if hasattr(self, 'reconnect_btn'):
                try:
                    self.reconnect_btn.config(state=tk.DISABLED)
                except Exception:
                    pass
        else:
            self._set_status('Disconnected')
            if hasattr(self, 'reconnect_btn'):
                try:
                    self.reconnect_btn.config(state=tk.NORMAL)
                except Exception:
                    pass

    def show_join_dialog(self, initial_name: Optional[str] = None):
        if getattr(self, '_joined_lobby', False):
            return
        if self._join_dialog is not None:
            return
        dlg = tk.Toplevel(self.master)
        dlg.title('Join Quiz')
        dlg.transient(self.master)
        dlg.grab_set()
        dlg.geometry('320x140')
        self._join_dialog = dlg

        tk.Label(dlg, text='Enter your player name:', font=('Helvetica', 11)).pack(pady=(12, 6))
        name_var = tk.StringVar()
        entry = tk.Entry(dlg, textvariable=name_var, font=('Helvetica', 12))
        entry.pack(padx=12, fill='x')
        entry.focus()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=12)
        join_btn = tk.Button(btn_frame, text='Join', state=tk.DISABLED, width=10)
        cancel_btn = tk.Button(btn_frame, text='Cancel', width=10, command=lambda: self._close_join(dlg))
        join_btn.pack(side='left', padx=6)
        cancel_btn.pack(side='right', padx=6)

        def on_change(*_):
            v = name_var.get().strip()
            join_btn.config(state=(tk.NORMAL if v else tk.DISABLED))

        name_var.trace_add('write', on_change)

        if initial_name:
            try:
                name_var.set(initial_name)
                entry.selection_range(0, tk.END)
                entry.icursor(tk.END)
                join_btn.config(state=tk.NORMAL)
            except Exception:
                pass

        def do_join():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('Name required', 'Please enter a player name.')
                return
            self._pending_name = name
            dlg.grab_release()
            dlg.destroy()
            self._join_dialog = None
            if not self.net.running:
                if not self.net.connect():
                    self._set_status('Disconnected')
                    try:
                        messagebox.showerror('Không kết nối được', 'Server chưa bật hoặc đang bận. Thử lại sau.')
                    except Exception:
                        pass
                    return
            self.net.send_line(f'NAME|{name}')
            self._set_status(f'Connected to {self.host}:{self.port}')

        join_btn.config(command=do_join)
        dlg.bind('<Return>', lambda e: do_join())
        dlg.bind('<Escape>', lambda e: (dlg.grab_release(), dlg.destroy()))

    def _close_join(self, dlg):
        dlg.grab_release()
        dlg.destroy()
        if self._join_dialog is dlg:
            self._join_dialog = None

    def _ensure_offline_modal(self):
        if self._offline_modal is not None:
            return
        m = tk.Toplevel(self.master)
        m.title('Server chưa bật')
        m.transient(self.master)
        try:
            m.grab_set()
        except Exception:
            pass
        m.geometry('360x160')
        lbl = tk.Label(m, text='Server chưa bật\nVui lòng mở server rồi thử lại.', font=('Helvetica', 11))
        lbl.pack(pady=(18, 12))

        btns = tk.Frame(m)
        btns.pack(pady=(6, 10))

        def do_retry():
            self._close_offline_modal()
            self._auto_probe_server()

        tk.Button(btns, text='Thử lại ngay', width=12, command=do_retry).pack(side='left', padx=6)
        tk.Button(btns, text='Thoát', width=10, command=self._on_close).pack(side='right', padx=6)

        try:
            m.update_idletasks()
            x = self.master.winfo_rootx() + (self.master.winfo_width() - m.winfo_width()) // 2
            y = self.master.winfo_rooty() + (self.master.winfo_height() - m.winfo_height()) // 2
            m.geometry(f'+{x}+{y}')
        except Exception:
            pass
        self._offline_modal = m

    def _close_offline_modal(self):
        if self._offline_modal is not None:
            try:
                self._offline_modal.grab_release()
            except Exception:
                pass
            try:
                self._offline_modal.destroy()
            except Exception:
                pass
            self._offline_modal = None

    def _connect_async(self, timeout: float, on_success, on_failure):
        if self.net.running:
            try:
                on_success()
            except Exception:
                pass
            return
        def worker():
            ok = False
            try:
                ok = self.net.connect_with_timeout(timeout)
            except Exception:
                ok = False
            def finish():
                if ok:
                    try:
                        on_success()
                    except Exception:
                        pass
                else:
                    try:
                        on_failure()
                    except Exception:
                        pass
            self.master.after(0, finish)
        threading.Thread(target=worker, daemon=True).start()

    def _on_probe_success(self):
        self._set_status('Kết nối thành công - nhập tên để vào')
        self._close_offline_modal()
        # Chỉ mở join dialog nếu chưa bị reject
        if not self._join_dialog and not self._joined_lobby and not getattr(self, '_server_paused_shown', False):
            self.show_join_dialog()

    def _on_probe_failure(self):
        self._set_status('Server chưa khởi động')
        self._ensure_offline_modal()

    def _on_probe_failure_and_retry(self):
        self._set_status('Server chưa khởi động')
        self._ensure_offline_modal()
        if not self._joined_lobby and not getattr(self, '_waiting_for_start', False):
            self.master.after(1500, self._auto_probe_server)

    def _on_close(self):
        """Handle window close: disconnect network and destroy main window."""
        try:
            # attempt graceful disconnect of network client
            try:
                if hasattr(self, 'net') and self.net:
                    try:
                        self.net.disconnect()
                    except Exception:
                        pass
            except Exception:
                pass
        finally:
            try:
                self.master.destroy()
            except Exception:
                pass


def run(host: Optional[str] = None, port: Optional[int] = None):
    root = tk.Tk()
    root.geometry('900x560')
    mw = MainWindow(root, host=host or '127.0.0.1', port=port or 65432)
    root.mainloop()
if __name__ == '__main__':
    run()
