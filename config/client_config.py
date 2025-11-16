"""Client configuration settings."""

import os


class ClientConfig:
    """Client configuration settings."""
    
    # Network settings
    DEFAULT_HOST = os.getenv('QUIZ_HOST', '127.0.0.1')
    DEFAULT_PORT = int(os.getenv('QUIZ_PORT', 65432))
    
    # Connection settings
    CONNECTION_TIMEOUT = 5.0  # seconds
    RECONNECT_INTERVAL = 1.5  # seconds
    MAX_RECONNECT_ATTEMPTS = 10
    
    # UI settings
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    COUNTDOWN_SECONDS = 15  # seconds per question
    
    # GUI Theme colors
    COLORS = {
        'primary': '#2C3E50',
        'secondary': '#3498DB',
        'success': '#27AE60',
        'danger': '#E74C3C',
        'warning': '#F39C12',
        'info': '#5DADE2',
        'light': '#ECF0F1',
        'dark': '#34495E',
        'background': '#FFFFFF',
        'text': '#2C3E50',
        'muted': '#95A5A6',
    }


client_config = ClientConfig()
