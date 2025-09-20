"""
Heartbeat management for WebSocket connection health monitoring.
Implements ping-pong mechanism to detect stale connections.
"""

import asyncio
import json
import logging
import time
import threading
from typing import Dict, Set, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClientHeartbeat:
    """Heartbeat tracking for individual client (RFC compliant - client sends pings)"""
    client_id: str
    last_ping_received: Optional[float] = None  # When we last received ping from client
    last_pong_sent: Optional[float] = None      # When we last sent pong to client
    missed_pings: int = 0                       # How many ping intervals client missed
    ping_count: int = 0                         # Total pings received from client
    pong_count: int = 0                         # Total pongs we sent back
    is_healthy: bool = True


class HeartbeatManager:
    """Manages WebSocket heartbeat ping-pong for connection health monitoring"""

    def __init__(self, ping_interval: int = 30, pong_timeout: int = 10, max_missed_pongs: int = 2):
        """
        Initialize heartbeat manager

        Args:
            ping_interval: Seconds between ping messages (default: 30s)
            pong_timeout: Seconds to wait for pong response (default: 10s)
            max_missed_pongs: Max missed pongs before marking as stale (default: 2)
        """
        self.ping_interval = ping_interval
        self.pong_timeout = pong_timeout
        self.max_missed_pongs = max_missed_pongs

        # Thread-safe tracking
        self._lock = threading.Lock()
        self.client_heartbeats: Dict[str, ClientHeartbeat] = {}

        # Heartbeat task management
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(f"HeartbeatManager initialized: ping_interval={ping_interval}s, pong_timeout={pong_timeout}s, max_missed={max_missed_pongs}")

    async def start_heartbeat(self, connection_manager):
        """Start the heartbeat monitoring system"""
        if self._running:
            logger.warning("Heartbeat system already running")
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(connection_manager))
        logger.info("✅ Heartbeat system started")

    async def stop_heartbeat(self):
        """Stop the heartbeat monitoring system"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Heartbeat system stopped")

    def register_client(self, client_id: str):
        """Register a new client for heartbeat monitoring"""
        with self._lock:
            if client_id not in self.client_heartbeats:
                self.client_heartbeats[client_id] = ClientHeartbeat(client_id=client_id)
                logger.info(f"💓 Registered client {client_id} for heartbeat monitoring")

    def unregister_client(self, client_id: str):
        """Remove client from heartbeat monitoring"""
        with self._lock:
            if client_id in self.client_heartbeats:
                del self.client_heartbeats[client_id]
                logger.info(f"💔 Unregistered client {client_id} from heartbeat monitoring")

    def handle_ping(self, client_id: str, timestamp: Optional[float] = None):
        """Handle ping received from client (RFC compliant)"""
        with self._lock:
            if client_id in self.client_heartbeats:
                heartbeat = self.client_heartbeats[client_id]
                heartbeat.last_ping_received = time.time()
                heartbeat.ping_count += 1
                heartbeat.missed_pings = 0  # Reset miss counter - client is alive
                heartbeat.is_healthy = True

                logger.debug(f"💓 Received ping from {client_id} (total: {heartbeat.ping_count})")

    def handle_pong_sent(self, client_id: str):
        """Track when we sent pong back to client"""
        with self._lock:
            if client_id in self.client_heartbeats:
                heartbeat = self.client_heartbeats[client_id]
                heartbeat.last_pong_sent = time.time()
                heartbeat.pong_count += 1

                logger.debug(f"💓 Sent pong to {client_id} (total: {heartbeat.pong_count})")

    async def _heartbeat_loop(self, connection_manager):
        """RFC compliant heartbeat loop - monitors client ping activity (no server pings)"""
        logger.info("🔄 Starting client activity monitoring loop (RFC compliant)")

        while self._running:
            try:
                # Only check for client activity - don't send pings
                await self._check_client_activity()

                # Wait for next check interval
                await asyncio.sleep(self.ping_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Heartbeat monitoring error: {e}")
                # Continue running even on errors
                await asyncio.sleep(5)

    async def _check_client_activity(self):
        """RFC compliant: Check for clients that haven't sent pings recently"""
        current_time = time.time()
        stale_clients = []

        with self._lock:
            for client_id, heartbeat in self.client_heartbeats.items():
                # Check if client hasn't pinged recently (RFC: client should initiate)
                time_since_last_ping = float('inf')
                if heartbeat.last_ping_received:
                    time_since_last_ping = current_time - heartbeat.last_ping_received

                # If client hasn't pinged in 2 * ping_interval, consider it inactive
                max_silence = self.ping_interval * 2  # 60 seconds by default

                if time_since_last_ping > max_silence:
                    heartbeat.missed_pings += 1
                    heartbeat.is_healthy = False

                    if heartbeat.missed_pings >= self.max_missed_pongs:  # Reuse threshold
                        stale_clients.append(client_id)
                        logger.warning(f"💀 Client {client_id} marked as stale (no ping for {time_since_last_ping:.1f}s)")
                    else:
                        logger.debug(f"⚠️ Client {client_id} silent for {time_since_last_ping:.1f}s ({heartbeat.missed_pings}/{self.max_missed_pongs})")

        # For now, only log stale clients - no automatic cleanup yet
        if stale_clients:
            logger.warning(f"🚨 Found {len(stale_clients)} inactive clients: {stale_clients}")
            logger.info("💡 Run manual cleanup via /api/monitoring/cleanup-stale?confirm=true")

    def get_heartbeat_stats(self) -> Dict:
        """Get heartbeat statistics for monitoring"""
        with self._lock:
            healthy_count = sum(1 for h in self.client_heartbeats.values() if h.is_healthy)
            total_count = len(self.client_heartbeats)
            total_pings_received = sum(h.ping_count for h in self.client_heartbeats.values())
            total_pongs_sent = sum(h.pong_count for h in self.client_heartbeats.values())

            return {
                "total_clients": total_count,
                "healthy_clients": healthy_count,
                "stale_clients": total_count - healthy_count,
                "total_pings_received": total_pings_received,  # RFC: we receive pings
                "total_pongs_sent": total_pongs_sent,          # RFC: we send pongs
                "ping_success_rate": (total_pongs_sent / max(1, total_pings_received)) * 100,
                "heartbeat_enabled": self._running,
                "compliance": "RFC_6455_compliant"  # Mark as standards compliant
            }