#!/usr/bin/env python3
import time
import random
import argparse
from config.client_config import client_config
from core.network_utils import create_socket_with_file, send_line

HOST = client_config.DEFAULT_HOST
PORT = client_config.DEFAULT_PORT


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', '-n', default=f'bot{random.randint(100,999)}')
    p.add_argument('--choice', '-c', choices=['A', 'B', 'C', 'D'], default=None)
    args = p.parse_args()
    name = args.name
    forced_choice = args.choice

    sock, f = create_socket_with_file(HOST, PORT, timeout=5)
    
    if sock is None or f is None:
        print(f"[{name}] Could not connect to {HOST}:{PORT}")
        return

    try:
        send_line(sock, f'NAME|{name}')
        print(f"[{name}] Connected and sent NAME")

        for raw in f:
            line = raw.rstrip('\n')
            if not line:
                continue
            print(f"[{name}] RECV: {line}")
            if line.startswith('QUESTION:'):
                parts = line.split('|')
                try:
                    qidx = parts[1]
                except Exception:
                    qidx = '0'
                delay = random.uniform(0.3, 1.5)
                time.sleep(delay)
                if forced_choice:
                    choice = forced_choice
                else:
                    choice = random.choice(['A', 'B', 'C', 'D'])
                msg = f'ANSWER:{qidx}|{choice}'
                if send_line(sock, msg):
                    print(f"[{name}] SENT: {msg}")
                else:
                    print(f"[{name}] Error sending answer")
            if 'GAME OVER' in line or line.startswith('RESULT|'):
                print(f"[{name}] Game over detected, exiting.")
                break

    except Exception as e:
        print(f"[{name}] Receiver error: {e}")
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
