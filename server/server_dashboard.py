import threading
import tkinter as tk
from tkinter import ttk, font
from typing import List, Tuple, Dict, Any

from server.ui_logger import ui_logger


COLORS = {
    'primary': '#2C3E50',      # Dark blue-grey
    'secondary': '#3498DB',     # Bright blue
    'success': '#27AE60',       # Green
    'danger': '#E74C3C',        # Red
    'warning': '#F39C12',       # Orange
    'info': '#5DADE2',          # Light blue
    'light': '#ECF0F1',         # Light grey
    'dark': '#34495E',          # Dark grey
    'background': '#FFFFFF',    # White
    'text': '#2C3E50',          # Dark text
    'muted': '#95A5A6',         # Grey text
}

STATUS_COLORS = {
    'waiting': COLORS['warning'],
    'in_quiz': COLORS['info'],
    'done': COLORS['success'],
}


class Dashboard(tk.Frame):
    def __init__(self, master: tk.Tk, name_registry=None):
        super().__init__(master, bg=COLORS['background'])
        self.master = master
        self.name_registry = name_registry
        self.pack(fill='both', expand=True)

        # logging visibility state
        self._show_all_logs: bool = False
        self._log_visible: bool = False
        self._suppressed_buffer: list[str] = []

        # Setup fonts
        self._setup_fonts()
        self._setup_styles()
        self._build_layout()
        self._schedule_update()
        
        # Hook window close to request server shutdown
        try:
            self.master.protocol('WM_DELETE_WINDOW', self._on_close)
        except Exception:
            pass

    def _setup_fonts(self) -> None:
        """Setup custom fonts for better typography."""
        try:
            self.font_title = font.Font(family='Segoe UI', size=12, weight='bold')
            self.font_heading = font.Font(family='Segoe UI', size=10, weight='bold')
            self.font_body = font.Font(family='Segoe UI', size=9)
            self.font_mono = font.Font(family='Consolas', size=9)
            self.font_stats = font.Font(family='Segoe UI', size=11, weight='bold')
        except Exception:
            pass

    def _setup_styles(self) -> None:
        """Configure ttk styles for modern look."""
        try:
            style = ttk.Style()
            
            # Try to use a modern theme
            if 'clam' in style.theme_names():
                style.theme_use('clam')
            elif 'vista' in style.theme_names():
                style.theme_use('vista')
            
            # Configure button styles
            style.configure('Primary.TButton',
                          font=('Segoe UI', 10, 'bold'),
                          borderwidth=0,
                          relief='flat')
            
            style.configure('Success.TButton',
                          font=('Segoe UI', 10, 'bold'),
                          foreground=COLORS['success'])
            
            style.configure('Danger.TButton',
                          font=('Segoe UI', 10, 'bold'),
                          foreground=COLORS['danger'])
            
            # Configure treeview
            style.configure('Treeview',
                          background=COLORS['background'],
                          foreground=COLORS['text'],
                          rowheight=22,
                          fieldbackground=COLORS['background'],
                          borderwidth=0)
            
            style.configure('Treeview.Heading',
                          font=('Segoe UI', 10, 'bold'),
                          background=COLORS['light'],
                          foreground=COLORS['primary'])
            
            style.map('Treeview',
                     background=[('selected', COLORS['secondary'])])
            
            # Configure frames
            style.configure('Card.TFrame',
                          background=COLORS['background'],
                          relief='flat',
                          borderwidth=1)
            
        except Exception as e:
            print(f"Style setup error: {e}")

    def _build_layout(self) -> None:
        self.master.title('🎮 Quiz Server Dashboard')
        self.master.geometry('950x600')
        self.master.minsize(800, 500)
        self.master.configure(bg=COLORS['light'])

        # Create main canvas with scrollbar for entire dashboard
        self.main_canvas = tk.Canvas(self, bg=COLORS['light'], highlightthickness=0)
        self.main_scrollbar = tk.Scrollbar(self, orient='vertical', command=self.main_canvas.yview)
        
        # Create scrollable frame inside canvas
        self.scrollable_frame = tk.Frame(self.main_canvas, bg=COLORS['light'])
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox('all'))
        )
        
        # Create window in canvas
        self.canvas_frame = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # Pack canvas and scrollbar
        self.main_canvas.pack(side='left', fill='both', expand=True)
        self.main_scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel for smooth scrolling
        self.main_canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        
        # Bind canvas resize to adjust frame width
        self.main_canvas.bind('<Configure>', self._on_canvas_configure)
        
        main_container = tk.Frame(self.scrollable_frame, bg=COLORS['light'])
        main_container.pack(fill='both', expand=True, padx=4, pady=4)
        
        # Grid configuration
        main_container.columnconfigure(0, weight=3)
        main_container.columnconfigure(1, weight=2)
        main_container.rowconfigure(1, weight=1)

        header = tk.Frame(main_container, bg=COLORS['primary'], height=45)
        header.grid(row=0, column=0, columnspan=2, sticky='ew', padx=3, pady=(3, 6))
        header.grid_propagate(False)
        
        # Title
        title_label = tk.Label(header, 
                              text='Quiz Server Dashboard',
                              font=('Segoe UI', 12, 'bold'),
                              bg=COLORS['primary'],
                              fg='white')
        title_label.pack(side='left', padx=12, pady=10)
        
        # Control buttons in header
        controls = tk.Frame(header, bg=COLORS['primary'])
        controls.pack(side='right', padx=12, pady=6)
        
        # Start/Stop button with visual state
        self.btn_start = tk.Button(controls,
                                   text='▶ Start',
                                   command=self._on_start_toggle,
                                   font=('Segoe UI', 9, 'bold'),
                                   bg=COLORS['success'],
                                   fg='white',
                                   activebackground='#229954',
                                   activeforeground='white',
                                   relief='flat',
                                   padx=12,
                                   pady=5,
                                   cursor='hand2',
                                   borderwidth=0)
        self.btn_start.pack(side='left', padx=4)
        
        # Status indicator
        status_frame = tk.Frame(controls, bg=COLORS['primary'])
        status_frame.pack(side='left', padx=(10, 4))
        
        self.status_indicator = tk.Canvas(status_frame, 
                                         width=10, height=10,
                                         bg=COLORS['primary'],
                                         highlightthickness=0)
        self.status_indicator.pack(side='left', padx=4)
        self.status_indicator.create_oval(1, 1, 9, 9, fill=COLORS['danger'], tags='indicator')
        
        self.var_status = tk.StringVar(value='Not Started')
        self.lbl_status = tk.Label(status_frame,
                                   textvariable=self.var_status,
                                   font=('Segoe UI', 8, 'bold'),
                                   bg=COLORS['primary'],
                                   fg='white')
        self.lbl_status.pack(side='left')
        
        # Show/Hide log button
        self.btn_showlog = tk.Button(controls,
                                    text='📋 Logs',
                                    command=self._on_toggle_log,
                                    font=('Segoe UI', 8),
                                    bg=COLORS['dark'],
                                    fg='white',
                                    activebackground=COLORS['secondary'],
                                    activeforeground='white',
                                    relief='flat',
                                    padx=10,
                                    pady=5,
                                    cursor='hand2',
                                    borderwidth=0)
        self.btn_showlog.pack(side='left', padx=4)

        self.left = tk.Frame(main_container, bg=COLORS['light'])
        self.left.grid(row=1, column=0, sticky='nsew', padx=(4, 6), pady=(0, 4))
        self.left.rowconfigure(0, weight=1)
        self.left.columnconfigure(0, weight=1)

        log_card = tk.Frame(self.left, bg='white', relief='flat', borderwidth=1)
        log_card.pack(fill='both', expand=True)
        
        log_header = tk.Frame(log_card, bg=COLORS['light'], height=28)
        log_header.pack(fill='x', padx=0, pady=0)
        log_header.pack_propagate(False)
        
        tk.Label(log_header,
                text='📝 Console',
                font=('Segoe UI', 9, 'bold'),
                bg=COLORS['light'],
                fg=COLORS['primary']).pack(side='left', padx=10, pady=6)

        self.txt_logs = tk.Text(log_card,
                               wrap='word',
                               state='disabled',
                               font=('Consolas', 8),
                               bg='#1E1E1E',
                               fg='#D4D4D4',
                               insertbackground='white',
                               selectbackground=COLORS['secondary'],
                               relief='flat',
                               padx=6,
                               pady=6)
        
        yscroll = tk.Scrollbar(log_card, orient='vertical', command=self.txt_logs.yview)
        self.txt_logs.configure(yscrollcommand=yscroll.set)
        self.txt_logs.pack(side='left', fill='both', expand=True)
        yscroll.pack(side='right', fill='y')

        self.right = tk.Frame(main_container, bg=COLORS['light'])
        self.right.grid(row=1, column=1, sticky='nsew', padx=(6, 4), pady=(0, 4))
        self.right.rowconfigure(2, weight=1)
        self.right.columnconfigure(0, weight=1)

        stats_card = tk.Frame(self.right, bg='white', relief='flat', borderwidth=1)
        stats_card.grid(row=0, column=0, sticky='ew', padx=0, pady=(0, 8))

        stats_header = tk.Frame(stats_card, bg=COLORS['secondary'], height=30)
        stats_header.pack(fill='x')
        stats_header.pack_propagate(False)
        
        tk.Label(stats_header,
                text='📊 Stats',
                font=('Segoe UI', 9, 'bold'),
                bg=COLORS['secondary'],
                fg='white').pack(side='left', padx=10, pady=6)

        stats_body = tk.Frame(stats_card, bg='white')
        stats_body.pack(fill='both', expand=True, padx=10, pady=8)

        # Create stat cards in grid
        self.var_online = tk.StringVar(value='0')
        self.var_total = tk.StringVar(value='0')
        self.var_high = tk.StringVar(value='-')
        self.var_low = tk.StringVar(value='-')
        self.var_completion = tk.StringVar(value='0%')
        self.var_top_player = tk.StringVar(value='-')

        stats_grid = tk.Frame(stats_body, bg='white')
        stats_grid.pack(fill='x', pady=(0, 10))

        # Row 1: Online and Total
        self._create_stat_box(stats_grid, '👥 Online', self.var_online, COLORS['success'], 0, 0)
        self._create_stat_box(stats_grid, '🎯 Started', self.var_total, COLORS['info'], 0, 1)
        
        # Row 2: High and Low scores
        self._create_stat_box(stats_grid, '⭐ High Score', self.var_high, COLORS['warning'], 1, 0)
        self._create_stat_box(stats_grid, '📉 Low Score', self.var_low, COLORS['muted'], 1, 1)
        
        # Row 3: Completion and Top Player
        self._create_stat_box(stats_grid, '✅ Completion', self.var_completion, COLORS['secondary'], 2, 0)
        self._create_stat_box(stats_grid, '🏆 Top Player', self.var_top_player, COLORS['primary'], 2, 1)

        # Chart area
        chart_frame = tk.Frame(stats_card, bg='white')
        chart_frame.pack(fill='x', padx=10, pady=(4, 10))
        
        tk.Label(chart_frame,
                text='Top 5 Players',
                font=('Segoe UI', 8, 'bold'),
                bg='white',
                fg=COLORS['muted']).pack(anchor='w', pady=(0, 4))
        
        self.chart = tk.Canvas(chart_frame, height=85, bg='white', highlightthickness=0)
        self.chart.pack(fill='x')

        players_card = tk.Frame(self.right, bg='white', relief='flat', borderwidth=1)
        players_card.grid(row=1, column=0, sticky='ew', padx=0, pady=(0, 8))

        players_header = tk.Frame(players_card, bg=COLORS['info'], height=28)
        players_header.pack(fill='x')
        players_header.pack_propagate(False)
        
        tk.Label(players_header,
                text='🎮 Players',
                font=('Segoe UI', 9, 'bold'),
                bg=COLORS['info'],
                fg='white').pack(side='left', padx=10, pady=6)

        self.tree_players = ttk.Treeview(players_card,
                                        columns=('name', 'status'),
                                        show='headings',
                                        height=4)
        self.tree_players.heading('name', text='Player')
        self.tree_players.heading('status', text='Status')
        self.tree_players.column('name', width=150, anchor='w')
        self.tree_players.column('status', width=100, anchor='center')
        
        players_scroll = ttk.Scrollbar(players_card, orient='vertical', command=self.tree_players.yview)
        self.tree_players.configure(yscroll=players_scroll.set)
        self.tree_players.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        players_scroll.pack(side='right', fill='y', padx=(0, 8), pady=6)

        scores_card = tk.Frame(self.right, bg='white', relief='flat', borderwidth=1)
        scores_card.grid(row=2, column=0, sticky='nsew', padx=0, pady=0)

        scores_header = tk.Frame(scores_card, bg=COLORS['warning'], height=28)
        scores_header.pack(fill='x')
        scores_header.pack_propagate(False)
        
        tk.Label(scores_header,
                text='🏆 Scores',
                font=('Segoe UI', 9, 'bold'),
                bg=COLORS['warning'],
                fg='white').pack(side='left', padx=10, pady=6)
        
        self.btn_reset_scores = tk.Button(scores_header,
                                         text='🔄 Reset',
                                         command=self._on_reset_scores,
                                         font=('Segoe UI', 8, 'bold'),
                                         bg=COLORS['danger'],
                                         fg='white',
                                         activebackground='#C0392B',
                                         activeforeground='white',
                                         relief='flat',
                                         padx=10,
                                         pady=3,
                                         cursor='hand2',
                                         borderwidth=0)
        self.btn_reset_scores.pack(side='right', padx=10, pady=5)

        self.tree_scores = ttk.Treeview(scores_card,
                                       columns=('rank', 'name', 'score', 'total', 'status'),
                                       show='headings')
        self.tree_scores.heading('rank', text='#')
        self.tree_scores.heading('name', text='Player')
        self.tree_scores.heading('score', text='Score')
        self.tree_scores.heading('total', text='Total')
        self.tree_scores.heading('status', text='Status')
        
        self.tree_scores.column('rank', width=35, anchor='center')
        self.tree_scores.column('name', width=130, anchor='w')
        self.tree_scores.column('score', width=55, anchor='center')
        self.tree_scores.column('total', width=55, anchor='center')
        self.tree_scores.column('status', width=80, anchor='center')

        scores_scroll = ttk.Scrollbar(scores_card, orient='vertical', command=self.tree_scores.yview)
        self.tree_scores.configure(yscroll=scores_scroll.set)
        self.tree_scores.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        scores_scroll.pack(side='right', fill='y', padx=(0, 8), pady=6)
        
        self._apply_log_visibility(False)

    def _create_stat_box(self, parent, label: str, var: tk.StringVar, color: str, row: int, col: int) -> None:
        """Create a styled statistics box."""
        box = tk.Frame(parent, bg=COLORS['light'], relief='flat', borderwidth=1)
        box.grid(row=row, column=col, sticky='ew', padx=4, pady=4)
        parent.columnconfigure(col, weight=1)
        
        tk.Label(box,
                text=label,
                font=('Segoe UI', 7),
                bg=COLORS['light'],
                fg=COLORS['muted']).pack(anchor='w', padx=8, pady=(6, 2))
        
        tk.Label(box,
                textvariable=var,
                font=('Segoe UI', 11, 'bold'),
                bg=COLORS['light'],
                fg=color).pack(anchor='w', padx=8, pady=(0, 6))

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling."""
        try:
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        except Exception:
            pass
    
    def _on_canvas_configure(self, event) -> None:
        try:
            canvas_width = event.width
            self.main_canvas.itemconfig(self.canvas_frame, width=canvas_width)
        except Exception:
            pass

    def _schedule_update(self) -> None:
        self.after(300, self._update)

    def _update(self) -> None:
        # Logs
        logs = ui_logger.drain_logs(500)
        if logs:
            self._process_logs(logs)

        # Players
        players = ui_logger.get_active_players_with_status()
        self._refresh_players(players)

        # Scoreboard
        rows = ui_logger.get_scoreboard_rows()
        self._refresh_scores(rows)

        # Statistics
        stats = ui_logger.get_statistics()
        self._refresh_stats(stats)
        self._draw_chart(rows)

        # Update server status and button state
        is_running = bool(stats.get('server_running'))
        if is_running:
            self.var_status.set('Running')
            try:
                self.btn_start.config(text='⏸ Stop', bg=COLORS['danger'])
                # Update status indicator to green
                self.status_indicator.delete('indicator')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=COLORS['success'], tags='indicator')
            except Exception:
                pass
        else:
            self.var_status.set('Not Started')
            try:
                self.btn_start.config(text='▶ Start', bg=COLORS['success'])
                # Update status indicator to red
                self.status_indicator.delete('indicator')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=COLORS['danger'], tags='indicator')
            except Exception:
                pass

        self._schedule_update()

    def _append_logs(self, lines: List[str]) -> None:
        self.txt_logs.configure(state='normal')
        for ln in lines:
            try:
                self.txt_logs.insert('end', ln + '\n')
            except Exception:
                pass
        self.txt_logs.see('end')
        self.txt_logs.configure(state='disabled')

    def _on_toggle_log(self) -> None:
        # Toggle visibility and flush suppressed backlog if showing
        self._apply_log_visibility(not self._log_visible)

    def _apply_log_visibility(self, visible: bool) -> None:
        self._log_visible = visible
        self._show_all_logs = visible
        try:
            self.btn_showlog.config(text='📋 Hide' if visible else '📋 Logs')
        except Exception:
            pass
        if visible:
            try:
                self.left.grid()
                self.right.grid(column=1)
                self.right.grid_configure(columnspan=1)
            except Exception:
                pass
            if self._suppressed_buffer:
                self._append_logs(self._suppressed_buffer)
                self._suppressed_buffer.clear()
        else:
            try:
                self.left.grid_remove()
                self.right.grid(column=0)
                self.right.grid_configure(columnspan=2)
            except Exception:
                pass

    def _process_logs(self, lines: List[str]) -> None:
        # When hidden, buffer everything without showing any line
        if not self._show_all_logs:
            self._suppressed_buffer.extend(lines)
            return
        # When visible, append new lines directly
        if lines:
            self._append_logs(lines)

    def _refresh_players(self, players: List[Tuple[str, str]]) -> None:
        # Rebuild list with color coding
        for iid in self.tree_players.get_children(''):
            self.tree_players.delete(iid)
        for i, (name, status) in enumerate(players):
            # Add status emoji
            status_display = {
                'waiting': '⏳ Waiting',
                'in_quiz': '✏️ In Quiz',
                'done': '✅ Done',
                'timeout': '⏱️ Timeout',
                'incomplete': '⚠️ Incomplete',
                'error': '❌ Error'
            }.get(status, status)
            
            iid = self.tree_players.insert('', 'end', values=(name, status_display))
            
            # Alternate row colors for better readability
            if i % 2 == 0:
                self.tree_players.item(iid, tags=('evenrow',))
        
        # Configure row colors
        try:
            self.tree_players.tag_configure('evenrow', background='#F8F9FA')
        except Exception:
            pass

    def _refresh_scores(self, rows: List[Dict[str, Any]]) -> None:
        # Rebuild scoreboard with ranking
        for iid in self.tree_scores.get_children(''):
            self.tree_scores.delete(iid)
        
        # Sort by score desc
        rows_sorted = sorted(rows, key=lambda r: r.get('score', 0), reverse=True)
        
        for i, r in enumerate(rows_sorted, 1):
            # Add rank medals for top 3
            rank = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else str(i)
            
            # Add status emoji
            status = r.get('status', '')
            status_display = {
                'waiting': '⏳ Waiting',
                'in_quiz': '✏️ Quiz',
                'done': '✅ Done',
                'timeout': '⏱️ Timeout',
                'incomplete': '⚠️ Incomplete',
                'error': '❌ Error'
            }.get(status, status)
            
            iid = self.tree_scores.insert('', 'end', values=(
                rank,
                r.get('name', ''),
                r.get('score', 0),
                r.get('total', 0),
                status_display
            ))
            
            # Alternate row colors
            if i % 2 == 0:
                self.tree_scores.item(iid, tags=('evenrow',))
            
            # Highlight top 3
            if i <= 3:
                self.tree_scores.item(iid, tags=(f'top{i}',))
        
        # Configure row colors
        try:
            self.tree_scores.tag_configure('evenrow', background='#F8F9FA')
            self.tree_scores.tag_configure('top1', background='#FFF9E6')  # Gold tint
            self.tree_scores.tag_configure('top2', background='#F0F0F0')  # Silver tint
            self.tree_scores.tag_configure('top3', background='#FFF4E6')  # Bronze tint
        except Exception:
            pass

    def _refresh_stats(self, stats: Dict[str, Any]) -> None:
        self.var_online.set(str(stats.get('online', 0)))
        self.var_total.set(str(stats.get('total_started', 0)))
        high = stats.get('high_score', None)
        low = stats.get('low_score', None)
        self.var_high.set('-' if high is None else str(high))
        self.var_low.set('-' if low is None else str(low))
        self.var_completion.set(f"{stats.get('completion_rate', 0.0)}%")
        top_name = stats.get('top_player', None)
        top_score = stats.get('top_score', None)
        self.var_top_player.set('-' if not top_name else f"{top_name} ({'-' if top_score is None else top_score})")

    def _draw_chart(self, rows: List[Dict[str, Any]]) -> None:
        # Enhanced bar chart with gradients and labels
        self.chart.delete('all')
        if not rows:
            # Show "No data" message
            width = max(self.chart.winfo_width(), 10)
            height = int(self.chart['height'])
            self.chart.create_text(width//2, height//2,
                                  text='No scores yet',
                                  font=('Segoe UI', 10),
                                  fill=COLORS['muted'])
            return
        
        rows_sorted = sorted(rows, key=lambda r: r.get('score', 0), reverse=True)[:5]
        width = max(self.chart.winfo_width(), 10)
        height = int(self.chart['height'])
        margin = 20
        bar_space = width - margin * 2
        n = len(rows_sorted)
        bar_w = max(int(bar_space / n) - 12, 20)
        max_score = max(r.get('score', 0) for r in rows_sorted) or 1
        
        # Define gradient colors for bars
        bar_colors = [
            '#3498DB',  # Blue
            '#2ECC71',  # Green
            '#F39C12',  # Orange
            '#9B59B6',  # Purple
            '#E74C3C',  # Red
        ]
        
        for i, r in enumerate(rows_sorted):
            name = str(r.get('name', ''))[:10]  # Truncate long names
            score = int(r.get('score', 0))
            total = int(r.get('total', 0))
            
            # Calculate bar height
            h = int((score / max_score) * (height - 40)) if max_score > 0 else 5
            h = max(h, 5)  # Minimum height
            
            # Position
            x0 = margin + i * (bar_w + 12)
            y0 = height - 25 - h
            x1 = x0 + bar_w
            y1 = height - 25
            
            # Draw bar with shadow effect
            self.chart.create_rectangle(x0+2, y0+2, x1+2, y1+2,
                                       fill='#D5D8DC',
                                       outline='')
            
            # Draw main bar
            bar_color = bar_colors[i % len(bar_colors)]
            self.chart.create_rectangle(x0, y0, x1, y1,
                                       fill=bar_color,
                                       outline='white',
                                       width=2)
            
            # Draw score on top of bar
            self.chart.create_text((x0 + x1)//2, y0 - 6,
                                 text=f'{score}/{total}',
                                 font=('Segoe UI', 7, 'bold'),
                                 fill=COLORS['primary'])
            
            # Draw player name at bottom
            self.chart.create_text((x0 + x1)//2, height - 8,
                                 text=name,
                                 font=('Segoe UI', 7),
                                 fill=COLORS['text'])

    def _on_reset_scores(self) -> None:
        try:
            # Use new method that also clears names
            ui_logger.reset_scores_and_names(self.name_registry)
        except Exception as e:
            ui_logger.send_log(f'Error resetting scores: {e}')
        # immediate UI refresh
        self._refresh_scores([])
        self._refresh_stats(ui_logger.get_statistics())
        self._draw_chart([])
        # Refresh player list to reflect cleared names
        self._refresh_players([])

    def _on_start_toggle(self) -> None:
        try:
            if ui_logger.is_server_running():
                ui_logger.set_server_running(False)
            else:
                ui_logger.set_server_running(True)
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            self.main_canvas.unbind_all('<MouseWheel>')
        except Exception:
            pass
        # Request shutdown and then destroy GUI
        try:
            ui_logger.request_shutdown()
        except Exception:
            pass
        try:
            self.master.destroy()
        except Exception:
            pass


def start_dashboard(name_registry=None) -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if 'vista' in style.theme_names():
            style.theme_use('vista')
    except Exception:
        pass
    Dashboard(root, name_registry=name_registry)
    root.mainloop()


if __name__ == '__main__':
    from server.server import main as server_main
    t = threading.Thread(target=server_main, daemon=True)
    t.start()
    start_dashboard()
