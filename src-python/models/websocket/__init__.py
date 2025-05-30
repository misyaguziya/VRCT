"""Initializes the websocket module, making WebSocketServer available for import."""
from typing import List

from .websocket_server import WebSocketServer

__all__: List[str] = ["WebSocketServer"]
