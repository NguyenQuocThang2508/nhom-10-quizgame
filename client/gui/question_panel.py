"""Question panel: displays the current question, answers and countdown.

Provides a callback when the user selects an option.
"""

import tkinter as tk
from typing import Callable, Iterable


class QuestionPanel:
    """Panel that shows a question, 4 option buttons and a countdown label.

    Public API:
    - display_question(qidx, text, options)
    - set_on_answer(callback)  # callback(answer_letter)
    - start_countdown(seconds), stop_countdown()
    """

    def __init__(self, master, font_question=('Helvetica', 18, 'bold'), font_option=('Helvetica', 16, 'bold')):
        self.master = master
        self.frame = tk.Frame(master, bg='#ffffff')
        self.frame.pack(side='right', fill='both', expand=True)
        # question label: wider wraplength so long text centers nicely
        self.question_label = tk.Label(self.frame, text='(Waiting for question...)', font=font_question, bg='#ffffff', wraplength=700, justify='center')
        self.question_label.pack(padx=12, pady=(18, 6))

        self.countdown_var = tk.StringVar(value='')
        self.countdown_label = tk.Label(self.frame, textvariable=self.countdown_var, font=('Helvetica', 12), bg='#ffffff')
        self.countdown_label.pack()

        self.opts_frame = tk.Frame(self.frame, bg='#ffffff')
        # add vertical spacing so options breathe
        self.opts_frame.pack(pady=(18, 24))

        self.option_buttons = {}
        self._on_answer = None
        # option button visuals: more padding and subtle color styling
        self._option_colors = ['#ffffff', '#f0f9ff', '#fef3c7', '#f0fdf4']
        for i, letter in enumerate(('A', 'B', 'C', 'D')):
            btn = tk.Button(
                self.opts_frame,
                text=letter,
                font=font_option,
                width=22,
                height=2,
                relief='flat',
                bd=2,
                bg='#ffffff',
                activebackground='#e6f0ff',
                command=lambda l=letter: self._on_click(l)
            )
            btn.grid(row=i // 2, column=i % 2, padx=28, pady=18)
            btn.config(state=tk.DISABLED)
            # subtle hover effect (raise) and color preview
            btn.bind('<Enter>', lambda e, b=btn: b.config(relief='raised'))
            btn.bind('<Leave>', lambda e, b=btn: b.config(relief='flat'))
            self.option_buttons[letter] = btn

        # Countdown internals
        self._countdown_after_id = None
        self._countdown_remaining = 0
        # animation internals for lively option highlights
        self._anim_after_id = None
        self._anim_index = 0
        self._anim_running = False
        # steady highlight and color palette
        self._steady_highlight = '#e6f7ff'  # light blue (steady)
        self._selected_color = '#ffd166'    # stronger yellow for immediate selection
        self._right_color = '#34d399'       # green for correct
        self._wrong_color = '#f87171'       # red for wrong
        self._dim_color = '#f3f4f6'         # gray-ish for timeout

    def set_on_answer(self, cb: Callable[[str], None]):
        """Register callback invoked with the chosen letter (A/B/C/D)."""
        self._on_answer = cb

    def _on_click(self, letter: str):
        # disable buttons immediately and notify
        for btn in self.option_buttons.values():
            btn.config(state=tk.DISABLED)
        # stop any running animation when user answers
        self._stop_animation()
        # highlight selected option immediately (stronger yellow)
        try:
            btn = self.option_buttons.get(letter)
            if btn:
                btn.config(bg=self._selected_color)
        except Exception:
            pass
        if self._on_answer:
            try:
                self._on_answer(letter)
            except Exception:
                pass
        # stop countdown when user answers
        self.stop_countdown()

    def show_eval(self, tag: str, given: str):
        """Display evaluation feedback: tag is 'RIGHT' or 'WRONG', given is the letter chosen (or 'SKIP')."""
        # stop animation and countdown
        try:
            self._stop_animation()
        except Exception:
            pass
        try:
            self.stop_countdown()
        except Exception:
            pass

        # normalize given
        g = (given or '').strip().upper()
        if not g:
            # timed out — dim all
            for b in self.option_buttons.values():
                try:
                    b.config(bg=self._dim_color)
                except Exception:
                    pass
            return

        # show right/wrong on chosen button
        btn = self.option_buttons.get(g)
        if not btn:
            return
        try:
            if tag.upper() == 'RIGHT':
                btn.config(bg=self._right_color)
            else:
                btn.config(bg=self._wrong_color)
        except Exception:
            pass

    def display_question(self, qidx, text: str, options: Iterable[str]):
        """Populate UI with question text and option strings."""
        self.question_label.config(text=text)
        for letter, opt_text in zip(('A', 'B', 'C', 'D'), options):
            btn = self.option_buttons[letter]
            btn.config(text=f"{letter}. {opt_text}", state=tk.NORMAL, bg='#ffffff')
        # start a gentle animation to draw attention to options
        try:
            self._start_animation()
        except Exception:
            pass

    def start_countdown(self, seconds: int):
        self.stop_countdown()
        self._countdown_remaining = int(seconds)
        self._update_countdown()

    def _start_animation(self):
        # set a steady, stronger background on options (no blinking)
        try:
            self._stop_animation()
            for b in self.option_buttons.values():
                try:
                    b.config(bg=self._steady_highlight)
                except Exception:
                    pass
            self._anim_running = True
        except Exception:
            pass

    def _stop_animation(self):
        self._anim_running = False
        if self._anim_after_id:
            try:
                self.master.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        # reset colors
        for b in self.option_buttons.values():
            try:
                b.config(bg='#ffffff')
            except Exception:
                pass

    def _update_countdown(self):
        if self._countdown_remaining <= 0:
            self.countdown_var.set('')
            # disable options when time is up
            for b in self.option_buttons.values():
                b.config(state=tk.DISABLED)
            self._countdown_after_id = None
            # notify UI that time expired (treat as missed turn)
            if self._on_answer:
                try:
                    # empty string signals timeout; main window will convert to SKIP
                    self._on_answer('')
                except Exception:
                    pass
            return
        self.countdown_var.set(f'Time left: {self._countdown_remaining}s')
        self._countdown_remaining -= 1
        self._countdown_after_id = self.master.after(1000, self._update_countdown)

    def stop_countdown(self):
        if self._countdown_after_id:
            try:
                self.master.after_cancel(self._countdown_after_id)
            except Exception:
                pass
            self._countdown_after_id = None
        self.countdown_var.set('')
