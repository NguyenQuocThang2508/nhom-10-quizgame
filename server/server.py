import errno
import random
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

from config.server_config import server_config
from core.network_utils import close_socket_safely, send_line
from core.shared_logic import load_questions
from server.name_registry import NameRegistry
from server.ui_logger import ui_logger

HOST = server_config.HOST
PORT = server_config.PORT
QUESTIONS_PATH = server_config.QUESTIONS_PATH
MAX_QUESTIONS = server_config.MAX_QUESTIONS

# Protocol timing
WAIT_SIGNAL_INTERVAL = server_config.WAIT_SIGNAL_INTERVAL
ACCEPT_TIMEOUT = server_config.ACCEPT_TIMEOUT
QUESTION_TIMEOUT = server_config.QUESTION_TIMEOUT

# Protocol messages
MSG_NAME_OK = server_config.MSG_NAME_OK
MSG_NAME_TAKEN = server_config.MSG_NAME_TAKEN
MSG_WAIT = server_config.MSG_WAIT
MSG_START = server_config.MSG_START
MSG_STOP = server_config.MSG_STOP
MSG_ERROR_NAME_TAKEN = server_config.MSG_ERROR_NAME_TAKEN
MSG_SERVER_PAUSED = server_config.MSG_SERVER_PAUSED
MSG_SERVER_READY = server_config.MSG_SERVER_READY

REGISTRY = NameRegistry()

server_running = False
server_running_lock = threading.Lock()


def is_port_in_use(host: str, port: int) -> bool:
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        test_socket.bind((host, port))
        test_socket.close()
        return False
    except OSError as e:
        if e.errno == errno.EADDRINUSE or e.errno == 10048:
            return True
        raise
    finally:
        try:
            test_socket.close()
        except:
            pass


def check_server_status() -> bool:
    return ui_logger.is_server_running()


def broadcast_stop_to_clients() -> None:
    """Broadcast message tạm ngưng đến tất cả client đang kết nối."""
    connections = REGISTRY.get_all_connections()
    ui_logger.send_log(f'Broadcasting SERVER_PAUSED to {len(connections)} clients')
    
    for conn in connections:
        try:
            send_line(conn, MSG_SERVER_PAUSED)
        except Exception as e:
            ui_logger.send_log(f'Failed to send STOP to a client: {e}')


def is_client_connected(conn: socket.socket) -> bool:
    """Check if client is still connected without blocking."""
    try:
        conn.setblocking(False)
        data = conn.recv(1, socket.MSG_PEEK)
        conn.setblocking(True)
        return len(data) > 0
    except BlockingIOError:
        conn.setblocking(True)
        return True  # No data available, but still connected
    except Exception:
        return False


def perform_name_handshake(conn: socket.socket, addr: Tuple, f) -> Optional[str]:
    """Perform name registration handshake.
    
    Returns:
        player_name if successful, None if rejected or disconnected.
    """
    if not check_server_status():
        ui_logger.send_log(f'[LOBBY] Client {addr} rejected: server paused')
        try:
            send_line(conn, MSG_SERVER_PAUSED)
            time.sleep(0.5)
        except Exception:
            pass
        return None
    
    while True:
        line = f.readline()
        if not line:
            ui_logger.send_log(f"Client {addr} disconnected before naming")
            return None
            
        line = line.strip()
        if not line.upper().startswith('NAME|'):
            continue
        
        if not check_server_status():
            ui_logger.send_log(f'[LOBBY] Name rejected for {addr}: server paused during handshake')
            try:
                send_line(conn, MSG_SERVER_PAUSED)
                time.sleep(0.5)
            except Exception:
                pass
            return None
        
        name = line.split('|', 1)[1].strip()
        
        if not check_server_status():
            ui_logger.send_log(f'[LOBBY] Name rejected for {addr}: server paused during handshake')
            try:
                send_line(conn, MSG_SERVER_PAUSED)
                time.sleep(0.5)
            except Exception:
                pass
            return None
        
        if not name or REGISTRY.exists(name):
            if REGISTRY.exists(name):
                ui_logger.send_log(f'[LOBBY] Name rejected (already in use): {name}')
                send_line(conn, MSG_ERROR_NAME_TAKEN)
            else:
                send_line(conn, MSG_NAME_TAKEN)
            ui_logger.update_active_players(REGISTRY.list_names())
            ui_logger.send_log('Active names: ' + str(REGISTRY.list_names()))
            continue
        
        REGISTRY.add(name, conn)
        send_line(conn, MSG_NAME_OK)
        ui_logger.mark_started(name)
        ui_logger.update_active_players(REGISTRY.list_names())
        ui_logger.send_log(f'[LOBBY] Name accepted: {name}')
        ui_logger.send_log('Active names: ' + str(REGISTRY.list_names()))
        return name


def prepare_quiz_questions(questions: List[Dict]) -> List[Dict]:
    """Prepare shuffled subset of questions for a client."""
    client_questions = list(questions)
    random.shuffle(client_questions)
    if len(client_questions) > MAX_QUESTIONS:
        client_questions = client_questions[:MAX_QUESTIONS]
    return client_questions


def shuffle_question_options(question: Dict) -> Tuple[str, List[str]]:
    """
    Shuffle question options and return new correct letter and shuffled options.
    Returns (new_answer_letter, shuffled_options_list)
    """
    orig_opts = [
        question.get('A', ''),
        question.get('B', ''),
        question.get('C', ''),
        question.get('D', '')
    ]
    
    orig_correct_letter = question.get('answer', 'A').upper()
    orig_correct_text = question.get(orig_correct_letter, '')
    
    shuffled_opts = list(orig_opts)
    random.shuffle(shuffled_opts)
    
    letters = ['A', 'B', 'C', 'D']
    new_answer_letter = 'A'
    for i, text in enumerate(shuffled_opts):
        if text == orig_correct_text:
            new_answer_letter = letters[i]
            break
    
    return new_answer_letter, shuffled_opts


def _handle_quiz_timeout(player_name: str, score: int, idx: int) -> None:
    """Handle player timeout during quiz."""
    ui_logger.send_log(
        f"Client {player_name} timed out after {QUESTION_TIMEOUT/60:.1f} minutes "
        f"on question {idx+1}"
    )
    send_line_safe = lambda c, m: None  # Will be passed from caller
    ui_logger.update_scoreboard(player_name, score, max(idx, 1), status='timeout')
    ui_logger.set_player_status(player_name, 'timeout')
    ui_logger.mark_finished(player_name)
    ui_logger.send_log(f"Player {player_name} auto-finished (timeout): {score}/{idx}")


def _handle_disconnect_mid_quiz(player_name: str, score: int, idx: int, total: int, conn: socket.socket) -> None:
    """Handle player disconnect during quiz."""
    ui_logger.send_log(
        f"Client {player_name} disconnected mid-quiz at question {idx+1}/{total}"
    )
    if idx > 0:
        send_line(conn, f"SCORE|{score}/{idx}")
        ui_logger.update_scoreboard(player_name, score, idx, status='incomplete')
        ui_logger.mark_finished(player_name)
        ui_logger.send_log(f"Player {player_name} incomplete: {score}/{idx}")
    else:
        ui_logger.send_log(f"Player {player_name} disconnected before answering any question")
    ui_logger.set_player_status(player_name, 'incomplete')


def _parse_answer(line: str, qid: str) -> tuple:
    """Parse ANSWER message. Returns (is_valid, given_answer, matches_qid)."""
    if not line.startswith('ANSWER:'):
        return False, line, False
    
    try:
        _, payload = line.split(':', 1)
        rid, given = payload.split('|', 1)
        return True, given.strip(), rid.strip() == qid
    except Exception:
        return False, line, False


def _evaluate_answer(is_valid: bool, matches_qid: bool, given: str, correct: str, conn: socket.socket) -> bool:
    """Evaluate answer and send feedback. Returns True if correct."""
    if not is_valid or not matches_qid:
        send_line(conn, f"EVAL|WRONG|{given}")
        return False
    
    if given.upper() == correct.upper():
        send_line(conn, f"EVAL|RIGHT|{given}")
        return True
    else:
        send_line(conn, f"EVAL|WRONG|{given}")
        return False


def _finish_quiz(player_name: str, score: int, total: int, conn: socket.socket, status: str = 'done') -> None:
    """Send final score and update player status."""
    send_line(conn, f"SCORE|{score}/{total}")
    ui_logger.update_scoreboard(player_name, score, total, status=status)
    ui_logger.set_player_status(player_name, status)
    ui_logger.mark_finished(player_name)
    ui_logger.send_log(f"Player {player_name} {status}: {score}/{total}")


def run_quiz_session(conn: socket.socket, f, player_name: str, questions: List[Dict]) -> None:
    """Run the quiz session for a connected player."""
    client_questions = prepare_quiz_questions(questions)
    total = len(client_questions)
    score = 0
    
    ui_logger.set_player_status(player_name, 'in_quiz')
    
    try:
        for idx, question in enumerate(client_questions):
            qid = str(idx)
            new_answer_letter, shuffled_opts = shuffle_question_options(question)
            
            opts_str = ','.join(shuffled_opts)
            send_line(conn, f"QUESTION:{qid}|{question['question']}|{opts_str}")
            
            try:
                conn.settimeout(QUESTION_TIMEOUT)
                line = f.readline()
                conn.settimeout(None)
            except socket.timeout:
                send_line(conn, f"SCORE|{score}/{max(idx, 1)}")
                _handle_quiz_timeout(player_name, score, idx)
                return
            
            if not line:
                _handle_disconnect_mid_quiz(player_name, score, idx, total, conn)
                return
            
            is_valid, given, matches_qid = _parse_answer(line.strip(), qid)
            if _evaluate_answer(is_valid, matches_qid, given, new_answer_letter, conn):
                score += 1
        
        _finish_quiz(player_name, score, total, conn, 'done')
        
    except Exception as e:
        ui_logger.send_log(f"Error in quiz session for {player_name}: {e}")
        questions_attempted = score + 1
        try:
            send_line(conn, f"SCORE|{score}/{questions_attempted}")
        except Exception:
            pass
        ui_logger.update_scoreboard(player_name, score, questions_attempted, status='error')
        ui_logger.set_player_status(player_name, 'error')
        ui_logger.mark_finished(player_name)


def handle_client(conn: socket.socket, addr: Tuple, questions: List[Dict]) -> None:
    """Handle a single client connection through the full lifecycle."""
    ui_logger.send_log(f"Client connected: {addr}")
    player_name = None
    
    try:
        f = conn.makefile('r', encoding='utf-8')
        
        player_name = perform_name_handshake(conn, addr, f)
        if not player_name:
            return
        
        run_quiz_session(conn, f, player_name, questions)
        
    except Exception as e:
        ui_logger.send_log(f"Error with client {addr}: {e}")
    finally:
        try:
            f.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        
        if player_name:
            ui_logger.send_log(f'{player_name} disconnected (name still reserved)')


def start_server_socket(questions: List[Dict]) -> None:
    """Start the main server socket and accept loop."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        server_socket.settimeout(ACCEPT_TIMEOUT)
        
        ui_logger.send_log(f"Quiz server listening on {HOST}:{PORT}")
        
        try:
            while not ui_logger.is_shutdown_requested():
                try:
                    conn, addr = server_socket.accept()
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=handle_client,
                        args=(conn, addr, questions),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except OSError:
                    break  # Socket closed during shutdown
                    
        except KeyboardInterrupt:
            ui_logger.send_log('KeyboardInterrupt received, shutting down')
        finally:
            ui_logger.send_log('Server main loop exiting')


def show_port_in_use_error(port: int) -> None:
    try:
        root = tk.Tk()
        root.title("❌ Lỗi Khởi Động Server")
        root.geometry("500x300")
        root.resizable(False, False)
        root.configure(bg='#f8d7da')
        
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        
        main_frame = tk.Frame(root, bg='#f8d7da', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        title_label = tk.Label(
            main_frame,
            text="⚠️ KHÔNG THỂ KHỞI ĐỘNG SERVER",
            font=('Arial', 14, 'bold'),
            fg='#721c24',
            bg='#f8d7da'
        )
        title_label.pack(pady=(0, 15))
        
        msg_text = (
            f"Server đã chạy trên cổng {port}!\n\n"
            f"Không thể khởi động thêm instance mới.\n\n"
            f"Vui lòng:\n"
            f"  • Tắt server hiện tại trước khi khởi động lại\n"
            f"  • Hoặc sử dụng port khác trong file config.py"
        )
        
        msg_label = tk.Label(
            main_frame,
            text=msg_text,
            font=('Arial', 10),
            fg='#721c24',
            bg='#f8d7da',
            justify='left'
        )
        msg_label.pack(pady=(0, 20))
        
        def close_window():
            root.quit()
            root.destroy()
        
        ok_button = tk.Button(
            main_frame,
            text="OK",
            command=close_window,
            font=('Arial', 10, 'bold'),
            bg='#dc3545',
            fg='white',
            padx=30,
            pady=8,
            cursor='hand2'
        )
        ok_button.pack()
        
        root.protocol("WM_DELETE_WINDOW", close_window)
        
        root.mainloop()
        
    except Exception as e:
        print(f"[GUI Error] Không thể hiển thị popup: {e}")


def main() -> None:
    if is_port_in_use(HOST, PORT):
        show_port_in_use_error(PORT)
        
        error_msg = (
            f"╔{'═' * 60}╗\n"
            f"║  KHÔNG THỂ KHỞI ĐỘNG SERVER                               ║\n"
            f"║                                                            ║\n"
            f"║  Server đã chạy trên cổng {PORT:<5}                            ║\n"
            f"║  Không thể khởi động thêm instance mới!                    ║\n"
            f"║                                                            ║\n"
            f"║  Vui lòng:                                                 ║\n"
            f"║  • Tắt server hiện tại trước khi khởi động lại            ║\n"
            f"║  • Hoặc sử dụng port khác trong file config.py            ║\n"
            f"╚{'═' * 60}╝"
        )
        print(error_msg)
        ui_logger.send_log(f"Server đã chạy trên cổng {PORT}, không thể khởi động lại")
        sys.exit(1)
    
    questions = load_questions(QUESTIONS_PATH, max_questions=MAX_QUESTIONS)
    if not questions:
        ui_logger.send_log(f"No questions found at {QUESTIONS_PATH}; server exiting.")
        sys.exit(1)
    
    ui_logger.send_log(
        f"Loaded {len(questions)} questions from {QUESTIONS_PATH} "
        f"(max per-client: {MAX_QUESTIONS})"
    )
    
    try:
        from server.server_dashboard import start_dashboard
        dashboard_thread = threading.Thread(
            target=lambda: start_dashboard(REGISTRY),
            daemon=True
        )
        dashboard_thread.start()
    except Exception as e:
        ui_logger.send_log(f"Dashboard failed to start: {e}")
    
    ui_logger.send_log(f"Starting server on {HOST}:{PORT}...")
    start_server_socket(questions)


if __name__ == '__main__':
    main()
