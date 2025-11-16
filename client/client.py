#!/usr/bin/env python3
import time
from config.client_config import client_config
from core.network_utils import create_socket_connection, send_line, recv_line

HOST = client_config.DEFAULT_HOST
PORT = client_config.DEFAULT_PORT


def try_connect(max_attempts=10, delay=2):
    """Thử kết nối đến server với số lần thử và độ trễ giữa các lần."""
    print(f"Đang kết nối đến server {HOST}:{PORT}...")
    
    for attempt in range(1, max_attempts + 1):
        sock = create_socket_connection(HOST, PORT, timeout=2)
        
        if sock:
            print(f"✓ Kết nối thành công!")
            return sock
        else:
            if attempt < max_attempts:
                print(f"✗ Lần {attempt}: Server chưa bật. Thử lại sau {delay}s...")
                time.sleep(delay)
            else:
                print(f"✗ Không thể kết nối sau {max_attempts} lần thử.")
                print("\nVui lòng:")
                print("1. Kiểm tra server đã chạy chưa: python -m server.server")
                print("2. Kiểm tra địa chỉ và port đúng không")
                return None
    return None


def main():
    sock = try_connect(max_attempts=10, delay=2)
    if not sock:
        return

    try:
        line = recv_line(sock)
        if line:
            print('Server:', line)
        name = input('Enter your name: ').strip() or 'player'
        send_line(sock, name)

        while True:
            line = recv_line(sock)
            if not line:
                print('Connection closed by server')
                break
            
            # Check if server paused
            if line.startswith('SERVER_PAUSED|'):
                msg = line.split('|', 1)[1] if '|' in line else 'Server đang tạm ngưng, vui lòng đợi...'
                print(f'\n⏸️  {msg}')
                print('Vui lòng chờ server bật lại.\n')
                break
            
            # Check if game paused/stopped (during gameplay)
            if line == 'STOP' or line.startswith('GAME_PAUSED|'):
                msg = line.split('|', 1)[1] if '|' in line else 'Game đã tạm dừng.'
                print(f'\n⏸️  {msg}')
                print('Vui lòng chờ server bật lại.\n')
                continue
            
            if line.startswith('QUESTION:'):
                payload = line.split(':', 1)[1]
                try:
                    qid, qtext, opts = payload.split('|', 2)
                    print(f"\nQuestion [{qid}]: {qtext}")
                    print('Options:', opts)
                    ans = input('Answer (type letter or text): ').strip()
                    msg = f'ANSWER:{qid}|{ans}'
                    send_line(sock, msg)
                except Exception as e:
                    print('Malformed QUESTION:', e)
            elif line.startswith('EVAL|'):
                print('EVAL:', line)
            elif line.startswith('SCORE|'):
                print('Final:', line)
                break
            else:
                print('Server:', line)

    except KeyboardInterrupt:
        print('\nCancelled by user')
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
