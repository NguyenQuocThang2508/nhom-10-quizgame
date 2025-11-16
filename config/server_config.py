"""Server configuration settings."""

import os


class ServerConfig:
    """Server configuration settings."""
    
    # Network settings
    HOST = os.getenv('QUIZ_HOST', '127.0.0.1')
    PORT = int(os.getenv('QUIZ_PORT', 65432))
    
    # Game settings
    QUESTIONS_PATH = 'data/questions.csv'
    MAX_QUESTIONS = 10
    
    # Protocol timing
    WAIT_SIGNAL_INTERVAL = 2.0  # seconds between WAIT signals
    ACCEPT_TIMEOUT = 1.0  # seconds for accept() timeout
    QUESTION_TIMEOUT = 180.0  # 3 minutes total timeout for answering each question
    
    # Protocol messages
    MSG_NAME_OK = 'NAME_OK'
    MSG_NAME_TAKEN = 'NAME_TAKEN'
    MSG_WAIT = 'WAIT'
    MSG_START = 'START'
    MSG_STOP = 'STOP'
    MSG_ERROR_NAME_TAKEN = 'ERROR|Tên đã được sử dụng, vui lòng nhập tên khác.'
    MSG_SERVER_PAUSED = 'SERVER_PAUSED|Server đang tạm ngưng, vui lòng đợi...'
    MSG_GAME_STARTED = 'GAME_STARTED|Game đã bắt đầu, không thể tham gia.'
    MSG_SERVER_READY = 'SERVER_READY|Server đã sẵn sàng, vui lòng nhập tên.'


server_config = ServerConfig()
