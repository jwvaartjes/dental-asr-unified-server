"""
SafeSend utility - backwards compatible with per-client locks.
"""
import json
import logging
import asyncio
import weakref
from typing import Any, Dict, Optional
from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger(__name__)

# Per-WS send lock for concurrent sends (no manager needed)
_WS_LOCKS: "weakref.WeakKeyDictionary[WebSocket, asyncio.Lock]" = weakref.WeakKeyDictionary()

def _get_ws_lock(ws: WebSocket) -> asyncio.Lock:
    lock = _WS_LOCKS.get(ws)
    if lock is None:
        lock = asyncio.Lock()
        _WS_LOCKS[ws] = lock
    return lock

class SafeSend:
    """Send helpers that prevent race conditions and auto-cleanup."""

    # ==== BACKWARDS COMPATIBLE API ====
    @staticmethod
    async def json(ws: WebSocket, data: Dict[str, Any]) -> bool:
        """Backwards compatible. Uses per-WS lock, no cleanup."""
        try:
            if not SafeSend.is_connected(ws):
                return False
            async with _get_ws_lock(ws):
                await ws.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.debug(f"SafeSend.json failed: {e}")
            return False

    @staticmethod
    def is_connected(ws: WebSocket) -> bool:
        """Check if WebSocket is connected."""
        try:
            return (ws.application_state == WebSocketState.CONNECTED and
                    ws.client_state == WebSocketState.CONNECTED)
        except Exception:
            return False

    # ==== NEW API WITH CLEANUP ====
    @staticmethod
    async def json_to(manager, client_id: str, payload: Dict[str, Any]) -> bool:
        """Send with manager-based cleanup on failure."""
        ws: Optional[WebSocket] = manager.active_connections.get(client_id)
        if not ws:
            return False
        lock = manager.get_send_lock(client_id)
        async with lock:
            try:
                await ws.send_text(json.dumps(payload))
                return True
            except Exception as e:
                logger.warning(f"SafeSend failed → cleanup {client_id}: {e}")
                await SafeSend._cleanup(manager, client_id, ws)
                return False

    @staticmethod
    async def _cleanup(manager, client_id: str, ws: WebSocket):
        """Auto-cleanup failed connection."""
        try:
            if ws.application_state == WebSocketState.CONNECTED:
                await ws.close()
        except Exception:
            pass
        manager.active_connections.pop(client_id, None)
        await manager._remove_from_all_channels(client_id)

    @staticmethod
    async def binary(ws: WebSocket, data: bytes) -> bool:
        """
        Safely send binary data to WebSocket with connection state validation.
        Returns True if message was sent successfully, False if failed.
        """
        try:
            # Check connection state
            if (ws.application_state != WebSocketState.CONNECTED or
                ws.client_state != WebSocketState.CONNECTED):
                logger.debug(f"SafeSend: Skipping binary send to closed WebSocket")
                return False

            # Send binary data
            await ws.send_bytes(data)
            return True

        except RuntimeError as e:
            if "websocket.close" in str(e):
                logger.debug(f"SafeSend: Binary WebSocket race condition avoided")
                return False
            else:
                logger.warning(f"SafeSend: Unexpected binary RuntimeError - {e}")
                return False

        except Exception as e:
            logger.warning(f"SafeSend: Failed to send binary data - {e}")
            return False

    @staticmethod
    async def text(ws: WebSocket, message: str) -> bool:
        """
        Safely send text message to WebSocket with connection state validation.
        Returns True if message was sent successfully, False if failed.
        """
        try:
            # Check connection state
            if (ws.application_state != WebSocketState.CONNECTED or
                ws.client_state != WebSocketState.CONNECTED):
                logger.debug(f"SafeSend: Skipping text send to closed WebSocket")
                return False

            # Send text message
            await ws.send_text(message)
            return True

        except RuntimeError as e:
            if "websocket.close" in str(e):
                logger.debug(f"SafeSend: Text WebSocket race condition avoided")
                return False
            else:
                logger.warning(f"SafeSend: Unexpected text RuntimeError - {e}")
                return False

        except Exception as e:
            logger.warning(f"SafeSend: Failed to send text message - {e}")
            return False

    @staticmethod
    def is_connected(ws: WebSocket) -> bool:
        """
        Check if WebSocket is properly connected and ready for sending.
        """
        try:
            return (ws.application_state == WebSocketState.CONNECTED and
                    ws.client_state == WebSocketState.CONNECTED)
        except Exception:
            return False