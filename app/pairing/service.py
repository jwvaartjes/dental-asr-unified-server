"""
Pairing service with connection management and business logic.
"""
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.channels: Dict[str, Set[str]] = {}
        self.client_info: Dict[str, dict] = {}
        self.connection_ips: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str, client_ip: str = None):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if client_ip:
            self.connection_ips[client_id] = client_ip
        logger.info(f"Client {client_id} connected from {client_ip}")

    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection and clean up."""
        # Get client info before cleanup for disconnect notifications
        client_info = self.client_info.get(client_id, {})
        device_type = client_info.get("device_type", "unknown")
        channel_id = client_info.get("channel")
        
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # Send disconnect notifications to channel members before cleanup
        if channel_id and channel_id in self.channels:
            await self._handle_device_disconnect(client_id, channel_id, device_type)
            
        # Remove from all channels
        for channel_id in list(self.channels.keys()):
            if client_id in self.channels[channel_id]:
                self.channels[channel_id].remove(client_id)
                if not self.channels[channel_id]:
                    del self.channels[channel_id]
                    
        # Clean up client info
        if client_id in self.client_info:
            del self.client_info[client_id]
            
        # Clean up IP tracking
        if client_id in self.connection_ips:
            del self.connection_ips[client_id]
            
        logger.info(f"Client {client_id} disconnected")

    async def _handle_device_disconnect(self, client_id: str, channel_id: str, device_type: str):
        """Handle device disconnection and notify the paired device(s) correctly."""
        is_desktop = (device_type == "desktop")
        
        if is_desktop:
            # Desktop disconnected → notify only mobiles
            payload = {
                "type": "desktop_disconnected",
                "session_id": client_id,
                "channel": channel_id,
                "reason": "desktop_closed",
                "force_disconnect": True
            }
        else:
            # Mobile disconnected → notify only desktops
            payload = {
                "type": "mobile_disconnected", 
                "session_id": client_id,
                "channel": channel_id,
                "reason": "mobile_closed",
                "force_disconnect": False
            }
        
        # Send notification to all other devices in the channel
        logger.debug(f"Broadcasting {payload['type']} to channel {channel_id}, excluding {client_id}")
        await self.broadcast_to_channel(channel_id, payload, exclude=client_id)
        logger.info(f"{device_type.title()} {client_id} disconnected from {channel_id}, notified channel members")

    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def join_channel(self, client_id: str, channel_id: str, device_type: str):
        """Add a client to a channel."""
        if channel_id not in self.channels:
            self.channels[channel_id] = set()
        
        self.channels[channel_id].add(client_id)
        self.client_info[client_id] = {
            "device_type": device_type,
            "channel": channel_id
        }
        
        logger.info(f"Client {client_id} ({device_type}) joined channel {channel_id}")
        
        # Notify others in channel
        await self.broadcast_to_channel(channel_id, {
            "type": "client_joined",
            "client_id": client_id,
            "device_type": device_type
        }, exclude=client_id)
        
        # Check for pairing completion
        if device_type == "mobile":
            await self._check_pairing_complete(channel_id)

    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude: Optional[str] = None):
        """Broadcast a message to all clients in a channel."""
        import json
        if channel_id in self.channels:
            logger.debug(f"Broadcasting to channel {channel_id}: {message['type']}")
            logger.debug(f"Channel members: {list(self.channels[channel_id])}")
            logger.debug(f"Active connections: {list(self.active_connections.keys())}")
            logger.debug(f"Excluding: {exclude}")
            
            for client_id in self.channels[channel_id]:
                if client_id != exclude and client_id in self.active_connections:
                    logger.debug(f"Sending {message['type']} to {client_id}")
                    await self.active_connections[client_id].send_text(json.dumps(message))
                else:
                    logger.debug(f"Skipping {client_id}: excluded={client_id == exclude}, active={client_id in self.active_connections}")
        else:
            logger.warning(f"Channel {channel_id} not found for broadcasting")

    async def _check_pairing_complete(self, channel_id: str):
        """Check if both desktop and mobile are in channel and notify success."""
        if channel_id not in self.channels:
            return
            
        devices_in_channel = {
            self.client_info.get(cid, {}).get("device_type")
            for cid in self.channels[channel_id]
        }
        
        if "desktop" in devices_in_channel and "mobile" in devices_in_channel:
            await self.broadcast_to_channel(channel_id, {
                "type": "pairing_success",
                "message": "Mobile and desktop paired successfully"
            })

    def get_client_info(self, client_id: str) -> Optional[dict]:
        """Get information about a specific client."""
        return self.client_info.get(client_id)

    def get_channel_clients(self, channel_id: str) -> Set[str]:
        """Get all clients in a specific channel."""
        return self.channels.get(channel_id, set())

    def get_client_ip(self, client_id: str) -> Optional[str]:
        """Get the IP address of a specific client."""
        return self.connection_ips.get(client_id)


class PairingService:
    """Business logic for device pairing."""
    
    def __init__(self, connection_manager: ConnectionManager, store=None):
        self.manager = connection_manager
        self.store = store  # Will be injected (InMemory or Redis)
    
    def generate_pairing_code(self) -> str:
        """Generate a 6-digit pairing code."""
        import random
        return str(random.randint(100000, 999999))
    
    async def initiate_pairing(self, desktop_session_id: str) -> dict:
        """Desktop initiates pairing by generating a code."""
        code = self.generate_pairing_code()
        
        if self.store:
            await self.store.store_pairing(code, desktop_session_id)
        
        logger.info(f"Generated pairing code {code} for desktop {desktop_session_id}")
        return {"code": code, "status": "success"}
    
    async def validate_pairing(self, code: str, mobile_session_id: str) -> dict:
        """Mobile validates pairing code."""
        # In production, would check store for desktop_session_id
        channel_id = f"pair-{code}"
        
        logger.info(f"Mobile {mobile_session_id} validating code {code}")
        
        return {
            "success": True,
            "channelId": channel_id,
            "message": "Paired successfully"
        }