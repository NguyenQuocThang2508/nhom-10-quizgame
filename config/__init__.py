"""Configuration package for Quiz Game.

Provides centralized configuration for server and client components.
"""

from config.server_config import ServerConfig, server_config
from config.client_config import ClientConfig, client_config

__all__ = ['ServerConfig', 'server_config', 'ClientConfig', 'client_config']
