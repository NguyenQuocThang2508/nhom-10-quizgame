"""Protocol parsing utilities for Quiz Game.

Centralized protocol message parsing to avoid code duplication.
"""

from typing import Optional, Tuple, List, Callable, Dict

class ProtocolParser:
    """Parser for line-delimited text protocol messages.
    
    Handles parsing of all server->client and client->server messages,
    dispatching to appropriate callbacks.
    """
    
    def __init__(self):
        """Initialize parser with callback handlers."""
        self.callbacks: Dict[str, Callable] = {}
        
    def register_callback(self, message_type: str, callback: Callable) -> None:
        """Register a callback for a specific message type.
        
        Args:
            message_type: Message prefix (e.g., 'NAME_OK', 'QUESTION:', 'EVAL|')
            callback: Function to call when message is received
        """
        self.callbacks[message_type] = callback
    
    def parse(self, line: str) -> bool:
        """Parse a protocol line and dispatch to appropriate callback.
        
        Args:
            line: Raw protocol line (without newline)
            
        Returns:
            True if message was handled, False if unknown message
        """
        line = line.strip()
        if not line:
            return False
            
        # Exact match messages
        exact_matches = ['NAME_OK', 'NAME_TAKEN', 'WAIT', 'START', 'STOP']
        for msg_type in exact_matches:
            if line == msg_type:
                callback = self.callbacks.get(msg_type)
                if callback:
                    try:
                        callback()
                        return True
                    except Exception as e:
                        print(f"Error in callback for {msg_type}: {e}")
                return True
        
        # Prefix match messages with payload
        if line.startswith('SERVER_PAUSED|'):
            return self._handle_with_payload(line, 'SERVER_PAUSED|', 
                                             'Server đang tạm ngưng, vui lòng đợi...')
        
        if line.startswith('GAME_STARTED|'):
            return self._handle_with_payload(line, 'GAME_STARTED|',
                                             'Game đã bắt đầu, không thể tham gia.')
        
        if line.startswith('GAME_PAUSED|'):
            return self._handle_with_payload(line, 'GAME_PAUSED|',
                                             'Game đã tạm dừng.')
        
        if line.startswith('ERROR|'):
            return self._handle_with_payload(line, 'ERROR|', '')
        
        if line.startswith('QUESTION:') or line.startswith('QUESTION|'):
            return self._handle_question(line)
        
        if line.startswith('EVAL|'):
            return self._handle_eval(line)
        
        if line.startswith('SCORE|'):
            return self._handle_with_payload(line, 'SCORE|', '')
        
        if line.startswith('LEADERBOARD|'):
            return self._handle_with_payload(line, 'LEADERBOARD|', '')
        
        # Unknown message
        return False
    
    def _handle_with_payload(self, line: str, prefix: str, default: str) -> bool:
        """Handle message with payload after delimiter."""
        payload = line.split('|', 1)[1] if '|' in line else default
        callback = self.callbacks.get(prefix)
        if callback:
            try:
                callback(payload)
                return True
            except Exception as e:
                print(f"Error in callback for {prefix}: {e}")
        return True
    
    def _handle_question(self, line: str) -> bool:
        """Parse QUESTION message: QUESTION:<qidx>|<text>|<opt1>,<opt2>,<opt3>,<opt4>"""
        try:
            sep = ':' if line.startswith('QUESTION:') else '|'
            payload = line.split(sep, 1)[1]
            parts = payload.split('|')
            
            if len(parts) < 2:
                return False
            
            # Parse question index
            raw_qidx = parts[0]
            try:
                qidx = int(raw_qidx) if raw_qidx.isdigit() else raw_qidx
            except Exception:
                qidx = raw_qidx
            
            qtext = parts[1]
            
            # Parse options (comma-separated or pipe-separated)
            opts = []
            if len(parts) >= 3:
                if ',' in parts[2] and len(parts) == 3:
                    opts = [o.strip() for o in parts[2].split(',') if o.strip()]
                else:
                    opts = [p.strip() for p in parts[2:]]
            
            callback = self.callbacks.get('QUESTION:')
            if callback:
                callback(qidx, qtext, opts)
                return True
                
        except Exception as e:
            print(f"Error parsing QUESTION: {e}")
        
        return False
    
    def _handle_eval(self, line: str) -> bool:
        """Parse EVAL message: EVAL|RIGHT|<letter> or EVAL|WRONG|<letter>"""
        try:
            parts = line.split('|')
            if len(parts) >= 3:
                tag = parts[1]  # RIGHT or WRONG
                given = parts[2]  # Letter answered
                
                callback = self.callbacks.get('EVAL|')
                if callback:
                    callback(tag, given)
                    return True
        except Exception as e:
            print(f"Error parsing EVAL: {e}")
        
        return False


class MessageBuilder:
    """Builder for constructing protocol messages.
    
    Provides consistent message formatting for client->server and server->client.
    """
    
    @staticmethod
    def name_request(name: str) -> str:
        """Build NAME request message."""
        return f'NAME|{name}'
    
    @staticmethod
    def answer(qidx, letter: str) -> str:
        """Build ANSWER message."""
        return f'ANSWER:{qidx}|{letter}'
    
    @staticmethod
    def question(qidx, text: str, options: List[str]) -> str:
        """Build QUESTION message."""
        opts_str = ','.join(options)
        return f'QUESTION:{qidx}|{text}|{opts_str}'
    
    @staticmethod
    def eval_result(is_correct: bool, letter: str) -> str:
        """Build EVAL message."""
        tag = 'RIGHT' if is_correct else 'WRONG'
        return f'EVAL|{tag}|{letter}'
    
    @staticmethod
    def score(points: int, total: int) -> str:
        """Build SCORE message."""
        return f'SCORE|{points}/{total}'
    
    @staticmethod
    def error(message: str) -> str:
        """Build ERROR message."""
        return f'ERROR|{message}'
    
    @staticmethod
    def server_paused(message: str = 'Server đang tạm ngưng, vui lòng đợi...') -> str:
        """Build SERVER_PAUSED message."""
        return f'SERVER_PAUSED|{message}'
    
    @staticmethod
    def game_started(message: str = 'Game đã bắt đầu, không thể tham gia.') -> str:
        """Build GAME_STARTED message."""
        return f'GAME_STARTED|{message}'
