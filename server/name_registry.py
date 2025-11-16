import threading
from typing import Optional, Dict, List
import socket


class NameRegistry:
    """Thread-safe registry of active player names.

    Maps player names to socket connections for communication.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._names: Dict[str, socket.socket] = {}

    def clear_all(self):
        """Clear all registered names (used when Reset Scores)."""
        with self._lock:
            self._names.clear()

    def exists(self, name: str) -> bool:
        """Check if a name is already registered."""
        with self._lock:
            return name in self._names

    def add(self, name: str, conn_obj: socket.socket) -> None:
        with self._lock:
            self._names[name] = conn_obj

    def remove(self, name: str) -> None:
        with self._lock:
            if name in self._names:
                del self._names[name]

    def list_names(self) -> List[str]:
        with self._lock:
            return list(self._names.keys())
    
    def get_all_connections(self) -> List[socket.socket]:
        """Get all active socket connections."""
        with self._lock:
            return list(self._names.values())
