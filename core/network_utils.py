"""Centralized network utilities for socket operations.

This module provides reusable functions for socket connection, sending, and receiving
to eliminate code duplication across client and server modules.
"""

import socket
import logging
from typing import Optional, Tuple, Any
from config.client_config import client_config

DEFAULT_HOST = client_config.DEFAULT_HOST
DEFAULT_PORT = client_config.DEFAULT_PORT
DEFAULT_TIMEOUT = client_config.CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)


def create_socket_connection(
    host: str = None,
    port: int = None,
    timeout: float = None
) -> Optional[socket.socket]:
    """Create and connect a TCP socket to server.
    
    Args:
        host: Server hostname or IP (defaults to config.DEFAULT_HOST)
        port: Server port (defaults to config.DEFAULT_PORT)
        timeout: Connection timeout in seconds (defaults to config.CONNECTION_TIMEOUT)
        
    Returns:
        Connected socket object, or None if connection failed.
    """
    if host is None:
        host = DEFAULT_HOST
    if port is None:
        port = DEFAULT_PORT
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        
        try:
            sock.settimeout(None)
        except Exception as e:
            logger.warning(f"Failed to set blocking mode: {e}")
        
        logger.info(f"Successfully connected to {host}:{port}")
        return sock
        
    except socket.timeout as e:
        logger.error(f"Connection timeout to {host}:{port}: {e}")
        return None
    except ConnectionRefusedError as e:
        logger.error(f"Connection refused by {host}:{port}: {e}")
        return None
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {host}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected connection error to {host}:{port}: {e}")
        return None


def send_line(sock: socket.socket, line: str) -> bool:
    """Send a line-delimited message through socket.
    
    Args:
        sock: Connected socket object
        line: Message to send (newline will be appended)
        
    Returns:
        True if send successful, False otherwise.
    """
    try:
        message = line.rstrip('\n') + '\n'
        sock.sendall(message.encode('utf-8'))
        return True
        
    except BrokenPipeError as e:
        logger.error(f"Broken pipe while sending: {e}")
        return False
    except ConnectionResetError as e:
        logger.error(f"Connection reset while sending: {e}")
        return False
    except socket.timeout as e:
        logger.error(f"Send timeout: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected send error: {e}")
        return False


def recv_line(sock: socket.socket) -> str:
    """Receive one line-delimited message from socket.
    
    Args:
        sock: Connected socket object
        
    Returns:
        Received line as string (without newline), or empty string on error/disconnect.
    """
    buf = []
    try:
        while True:
            ch = sock.recv(1)
            
            if not ch:
                logger.warning("Connection closed by peer during recv_line")
                return ''
            
            if ch == b'\n':
                break
                
            buf.append(ch)
        
        line = b''.join(buf).decode('utf-8').rstrip('\r')
        return line
        
    except socket.timeout as e:
        logger.error(f"Receive timeout: {e}")
        return ''
    except ConnectionResetError as e:
        logger.error(f"Connection reset during receive: {e}")
        return ''
    except UnicodeDecodeError as e:
        logger.error(f"UTF-8 decode error: {e}")
        return ''
    except Exception as e:
        logger.error(f"Unexpected receive error: {e}")
        return ''


def close_socket_safely(sock: Optional[socket.socket]) -> None:
    """Safely close a socket, suppressing all errors.
    
    Args:
        sock: Socket to close (can be None)
    """
    if sock is None:
        return
        
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    
    try:
        sock.close()
    except Exception:
        pass


def create_socket_with_file(
    host: str = None,
    port: int = None,
    timeout: float = None,
    encoding: str = 'utf-8',
    newline: str = '\n'
) -> Tuple[Optional[socket.socket], Optional[Any]]:
    """Create socket connection and wrap with file object for line reading.
    
    Args:
        host: Server hostname or IP (defaults to config.DEFAULT_HOST)
        port: Server port (defaults to config.DEFAULT_PORT)
        timeout: Connection timeout in seconds (defaults to config.CONNECTION_TIMEOUT)
        encoding: File encoding (default: 'utf-8')
        newline: Line ending (default: '\\n')
        
    Returns:
        Tuple of (socket, file_object), or (None, None) if connection failed.
    """
    sock = create_socket_connection(host, port, timeout)
    if sock is None:
        return None, None
    
    try:
        file_obj = sock.makefile('r', encoding=encoding, newline=newline)
        return sock, file_obj
    except Exception as e:
        logger.error(f"Failed to create file object: {e}")
        close_socket_safely(sock)
        return None, None
