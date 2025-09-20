"""
Pairing service with connection management and business logic.
"""
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket

from ..monitoring.metrics import get_metrics
from ..monitoring.heartbeat import HeartbeatManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.channels: Dict[str, Set[str]] = {}
        self.client_info: Dict[str, dict] = {}
        self.connection_ips: Dict[str, str] = {}

        # Connection activity tracking for timeout management
        self.last_activity: Dict[str, float] = {}
        self.connection_start_time: Dict[str, float] = {}

        # Monitoring and metrics
        self.metrics = get_metrics()

        # Heartbeat management for connection health
        self.heartbeat = HeartbeatManager(
            ping_interval=30,  # 30 seconds between pings
            pong_timeout=10,   # 10 seconds to respond
            max_missed_pongs=2 # 2 missed pongs = stale
        )

        logger.info("ConnectionManager initialized with monitoring and heartbeat enabled")

    async def connect(self, websocket: WebSocket, client_id: str, client_ip: str = None):
        """Accept and register a new WebSocket connection."""
        import time
        await websocket.accept()
        current_time = time.time()
        
        self.active_connections[client_id] = websocket
        self.last_activity[client_id] = current_time
        self.connection_start_time[client_id] = current_time
        
        if client_ip:
            self.connection_ips[client_id] = client_ip

        # Record connection for monitoring
        self.metrics.record_client_connected(client_id, device_type="unknown", client_ip=client_ip)

        # Register for heartbeat monitoring
        self.heartbeat.register_client(client_id)

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
            
        # Clean up activity tracking
        if client_id in self.last_activity:
            del self.last_activity[client_id]
        if client_id in self.connection_start_time:
            del self.connection_start_time[client_id]

        # Record disconnection for monitoring
        disconnect_reason = f"{device_type}_disconnect" if device_type != "unknown" else "client_disconnect"
        self.metrics.record_client_disconnected(client_id, reason=disconnect_reason)

        # Unregister from heartbeat monitoring
        self.heartbeat.unregister_client(client_id)

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
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send personal message to {client_id}: {e}")

    async def join_channel(self, client_id: str, channel_id: str, device_type: str):
        """Add a client to a channel."""
        if channel_id not in self.channels:
            self.channels[channel_id] = set()
        
        self.channels[channel_id].add(client_id)
        self.client_info[client_id] = {
            "device_type": device_type,
            "channel": channel_id
        }

        # Update device type in metrics (now that we know it)
        self.metrics.record_client_connected(client_id, device_type=device_type)
        self.metrics.record_channel_join(client_id, channel_id)

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
        from datetime import datetime

        if channel_id in self.channels:
            logger.info(f"📡 Broadcasting to channel {channel_id}: {message.get('type')} (exclude: {exclude})")
            logger.info(f"📋 Channel members: {list(self.channels[channel_id])}")
            logger.info(f"🔌 Active connections: {list(self.active_connections.keys())}")

            # Convert datetime objects to ISO strings for JSON serialization
            serializable_message = self._make_json_serializable(message)

            sent_count = 0
            for client_id in self.channels[channel_id]:
                if client_id != exclude and client_id in self.active_connections:
                    logger.info(f"📤 Sending {message.get('type')} to {client_id}")
                    try:
                        await self.active_connections[client_id].send_text(json.dumps(serializable_message))
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send message to {client_id}: {e}")
                else:
                    logger.info(f"⏭️ Skipping {client_id}: excluded={client_id == exclude}, active={client_id in self.active_connections}")

            logger.info(f"✅ Broadcast complete: {sent_count} messages sent to channel {channel_id}")
        else:
            logger.warning(f"❌ Channel {channel_id} not found for broadcasting. Available: {list(self.channels.keys())}")

    def _make_json_serializable(self, obj):
        """
        Convert objects to JSON-serializable format.
        Handles datetime objects and nested structures.
        """
        from datetime import datetime

        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def update_activity(self, client_id: str):
        """Update last activity time for a client."""
        import time
        if client_id in self.active_connections:
            self.last_activity[client_id] = time.time()

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


# Old PairingStore class removed - now using new interface from store.py


class PairingService:
    """Business logic for device pairing."""

    def __init__(self, connection_manager: ConnectionManager, store=None):
        self.manager = connection_manager
        # Import here to avoid circular imports
        from .store import InMemoryPairingStore
        self.store = store or InMemoryPairingStore()  # Use new in-memory store by default
        # Track user sessions to ensure only one active pairing per user
        self.user_sessions: Dict[str, Set[str]] = {}  # user_email -> {session_ids}
    
    def generate_pairing_code(self) -> str:
        """Generate a 6-digit pairing code."""
        import random
        return str(random.randint(100000, 999999))
    
    async def initiate_pairing(self, desktop_session_id: str, desktop_auth_info: dict = None) -> dict:
        """Desktop initiates pairing by generating a code."""
        from datetime import datetime, timedelta

        # Clean up any existing sessions for this user before creating new pairing
        if desktop_auth_info and desktop_auth_info.get("username"):
            user_email = desktop_auth_info["username"]
            await self.cleanup_user_sessions(user_email, desktop_session_id)

        code = self.generate_pairing_code()
        channel_id = f"pair-{code}"

        # Code expires after 5 minutes
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        if self.store:
            # Calculate TTL in seconds (5 minutes = 300 seconds)
            ttl_seconds = 300  # 5 minutes
            await self.store.store_pairing(code, desktop_session_id, ttl_seconds, desktop_auth_info)

        # Track that this user now has an active session
        if desktop_auth_info and desktop_auth_info.get("username"):
            user_email = desktop_auth_info["username"]
            self.user_sessions[user_email] = self.user_sessions.get(user_email, set())
            self.user_sessions[user_email].add(desktop_session_id)

        logger.info(f"Generated pairing code {code} for desktop {desktop_session_id} with auth: {bool(desktop_auth_info)}, expires at {expires_at}")

        # Frontend-compatible response with desktop state
        return {
            "success": True,
            "code": code,
            "channelId": channel_id,  # ✅ camelCase for frontend
            "desktopState": {
                "paired": True,          # ✅ Desktop is now in pairing mode
                "waitingForMobile": True,  # ✅ Status indicator
                "sessionId": desktop_session_id,
                "channelId": channel_id
            },
            "expiresAt": expires_at.isoformat() + "Z",
            "expiresIn": 300,
            "message": "Pairing code generated successfully"
        }
    
    async def validate_pairing(self, code: str, mobile_session_id: str) -> dict:
        """Mobile validates pairing code."""
        channel_id = f"pair-{code}"

        # Validate code format (proper validation)
        if not code or len(code) != 6:
            return {
                "success": False,
                "error": "INVALID_CODE_LENGTH", 
                "message": f"Pairing code must be exactly 6 digits, got {len(code) if code else 0}",
                "details": {
                    "provided_code": code,
                    "expected_format": "6 digits (000000-999999)"
                }
            }

        if not code.isdigit():
            return {
                "success": False,
                "error": "INVALID_CODE_FORMAT",
                "message": "Pairing code must contain only digits",
                "details": {
                    "provided_code": code,
                    "expected_format": "6 digits (000000-999999)"
                }
            }

        # Check if code exists and hasn't expired
        desktop_session_id = await self.store.get_pairing(code)

        if not desktop_session_id:
            return {
                "success": False,
                "error": "CODE_NOT_FOUND",
                "message": "Pairing code does not exist or has expired",
                "details": {
                    "provided_code": code,
                    "suggestion": "Generate a new pairing code on desktop"
                }
            }

        logger.info(f"Mobile {mobile_session_id} successfully paired with code {code}")

        # Frontend-compatible response with camelCase
        return {
            "success": True,
            "channelId": channel_id,  # ✅ camelCase for frontend compatibility
            "message": "Device paired successfully",
            "pairingCode": code,
            "expiresIn": 300  # Additional helpful info
        }

    async def cleanup_user_sessions(self, user_email: str, new_session_id: str):
        """Cleanup old pairing sessions for a user, keeping only the newest one."""
        if user_email not in self.user_sessions:
            self.user_sessions[user_email] = set()

        # Get existing sessions for this user
        old_sessions = self.user_sessions[user_email].copy()

        # Disconnect old sessions from their channels
        for old_session_id in old_sessions:
            client_info = self.manager.get_client_info(old_session_id)
            if client_info and client_info.get("channel"):
                old_channel = client_info["channel"]
                logger.info(f"Cleaning up old session {old_session_id} from channel {old_channel} for user {user_email}")
                await self.manager.disconnect(old_session_id)

        # Set new session as the only active one for this user
        self.user_sessions[user_email] = {new_session_id}
        logger.info(f"User {user_email} now has active session: {new_session_id}")