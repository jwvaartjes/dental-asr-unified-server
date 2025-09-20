"""
Core metrics tracking for WebSocket connections and audio processing.
Provides real-time monitoring of multi-client performance and resource usage.
"""
import asyncio
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from statistics import mean, median


@dataclass
class ClientMetrics:
    """Metrics for a single WebSocket client"""
    client_id: str
    device_type: str = "unknown"
    connection_time: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    # Audio processing metrics
    total_audio_chunks: int = 0
    total_audio_bytes: int = 0
    current_queue_size: int = 0
    max_queue_size: int = 0

    # Processing latency tracking (last 100 measurements)
    processing_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    transcription_latencies: deque = field(default_factory=lambda: deque(maxlen=100))

    # Success/error tracking
    successful_transcriptions: int = 0
    failed_transcriptions: int = 0
    connection_errors: int = 0

    # Session tracking
    session_text_length: int = 0
    session_line_breaks: int = 0

    def get_connection_duration(self) -> float:
        """Get connection duration in seconds"""
        return time.time() - self.connection_time

    def get_avg_processing_latency(self) -> float:
        """Get average processing latency in milliseconds"""
        if not self.processing_latencies:
            return 0.0
        return mean(self.processing_latencies)

    def get_avg_transcription_latency(self) -> float:
        """Get average transcription latency in milliseconds"""
        if not self.transcription_latencies:
            return 0.0
        return mean(self.transcription_latencies)

    def get_success_rate(self) -> float:
        """Get transcription success rate (0.0 - 1.0)"""
        total = self.successful_transcriptions + self.failed_transcriptions
        if total == 0:
            return 1.0
        return self.successful_transcriptions / total

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()


@dataclass
class SystemMetrics:
    """System-wide metrics across all clients"""
    start_time: float = field(default_factory=time.time)
    total_connections: int = 0
    total_disconnections: int = 0
    peak_concurrent_clients: int = 0

    # Aggregate processing metrics
    total_audio_processed_bytes: int = 0
    total_transcriptions: int = 0
    total_errors: int = 0

    # Rate tracking (per minute)
    recent_connection_times: deque = field(default_factory=lambda: deque(maxlen=60))
    recent_transcription_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time

    def get_connection_rate(self) -> float:
        """Get connections per minute"""
        now = time.time()
        recent = [t for t in self.recent_connection_times if now - t < 60]
        return len(recent)

    def get_transcription_rate(self) -> float:
        """Get transcriptions per minute"""
        now = time.time()
        recent = [t for t in self.recent_transcription_times if now - t < 60]
        return len(recent)


class WebSocketMetrics:
    """Thread-safe metrics collector for WebSocket connections"""

    def __init__(self):
        self._lock = threading.Lock()
        self.clients: Dict[str, ClientMetrics] = {}
        self.system = SystemMetrics()
        self.channels: Dict[str, Set[str]] = defaultdict(set)  # channel_id -> client_ids

        # Event history for real-time monitoring
        self.event_history: deque = deque(maxlen=1000)

    def record_client_connected(self, client_id: str, device_type: str = "unknown", client_ip: str = None):
        """Record new client connection"""
        with self._lock:
            if client_id not in self.clients:
                self.clients[client_id] = ClientMetrics(
                    client_id=client_id,
                    device_type=device_type
                )
                self.system.total_connections += 1
                self.system.recent_connection_times.append(time.time())

                # Update peak concurrent clients
                current_count = len(self.clients)
                if current_count > self.system.peak_concurrent_clients:
                    self.system.peak_concurrent_clients = current_count

                self._add_event("client_connected", {
                    "client_id": client_id,
                    "device_type": device_type,
                    "client_ip": client_ip,
                    "concurrent_clients": current_count
                })
            else:
                # Update existing client info if device type changes
                self.clients[client_id].device_type = device_type

    def record_client_disconnected(self, client_id: str, reason: str = None):
        """Record client disconnection"""
        with self._lock:
            if client_id in self.clients:
                metrics = self.clients[client_id]
                duration = metrics.get_connection_duration()

                self._add_event("client_disconnected", {
                    "client_id": client_id,
                    "device_type": metrics.device_type,
                    "connection_duration": duration,
                    "reason": reason,
                    "final_stats": {
                        "chunks_processed": metrics.total_audio_chunks,
                        "success_rate": metrics.get_success_rate(),
                        "avg_latency": metrics.get_avg_processing_latency()
                    }
                })

                del self.clients[client_id]
                self.system.total_disconnections += 1

                # Remove from all channels
                for channel_clients in self.channels.values():
                    channel_clients.discard(client_id)

    def record_channel_join(self, client_id: str, channel_id: str):
        """Record client joining a channel"""
        with self._lock:
            self.channels[channel_id].add(client_id)
            self._add_event("channel_joined", {
                "client_id": client_id,
                "channel_id": channel_id,
                "channel_size": len(self.channels[channel_id])
            })

    def record_audio_received(self, client_id: str, audio_size: int):
        """Record audio chunk received from client"""
        with self._lock:
            if client_id in self.clients:
                metrics = self.clients[client_id]
                metrics.total_audio_chunks += 1
                metrics.total_audio_bytes += audio_size
                metrics.update_activity()

                self.system.total_audio_processed_bytes += audio_size

    def record_queue_update(self, client_id: str, queue_size: int):
        """Record current queue size for client"""
        with self._lock:
            if client_id in self.clients:
                metrics = self.clients[client_id]
                metrics.current_queue_size = queue_size
                if queue_size > metrics.max_queue_size:
                    metrics.max_queue_size = queue_size

                # Alert on queue backup
                if queue_size > 5:
                    self._add_event("queue_backup_warning", {
                        "client_id": client_id,
                        "queue_size": queue_size,
                        "severity": "high" if queue_size > 10 else "medium"
                    })

    def record_processing_started(self, client_id: str) -> float:
        """Record processing start and return timestamp for latency calculation"""
        timestamp = time.time()
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id].update_activity()
        return timestamp

    def record_processing_completed(self, client_id: str, start_time: float, success: bool = True):
        """Record processing completion with latency"""
        latency_ms = (time.time() - start_time) * 1000

        with self._lock:
            if client_id in self.clients:
                metrics = self.clients[client_id]
                metrics.processing_latencies.append(latency_ms)
                metrics.update_activity()

                if success:
                    metrics.successful_transcriptions += 1
                    self.system.total_transcriptions += 1
                    self.system.recent_transcription_times.append(time.time())
                else:
                    metrics.failed_transcriptions += 1
                    self.system.total_errors += 1

                # Alert on high latency
                if latency_ms > 2000:  # > 2 seconds
                    self._add_event("high_latency_warning", {
                        "client_id": client_id,
                        "latency_ms": latency_ms,
                        "severity": "high" if latency_ms > 5000 else "medium"
                    })

    def record_transcription_latency(self, client_id: str, latency_ms: float):
        """Record transcription-specific latency"""
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id].transcription_latencies.append(latency_ms)

    def record_session_update(self, client_id: str, session_length: int, line_breaks: int):
        """Record session transcription stats"""
        with self._lock:
            if client_id in self.clients:
                metrics = self.clients[client_id]
                metrics.session_text_length = session_length
                metrics.session_line_breaks = line_breaks

    def record_error(self, client_id: str, error_type: str, error_message: str):
        """Record error for client"""
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id].connection_errors += 1

            self._add_event("error", {
                "client_id": client_id,
                "error_type": error_type,
                "error_message": error_message[:200]  # Truncate long messages
            })

    def get_client_metrics(self, client_id: str) -> Optional[ClientMetrics]:
        """Get metrics for specific client"""
        with self._lock:
            return self.clients.get(client_id)

    def get_all_client_metrics(self) -> Dict[str, ClientMetrics]:
        """Get metrics for all active clients"""
        with self._lock:
            return self.clients.copy()

    def get_system_metrics(self) -> SystemMetrics:
        """Get system-wide metrics"""
        with self._lock:
            return self.system

    def get_channel_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all channels"""
        with self._lock:
            channel_metrics = {}
            for channel_id, client_ids in self.channels.items():
                if client_ids:  # Only include active channels
                    device_breakdown = defaultdict(int)
                    for client_id in client_ids:
                        if client_id in self.clients:
                            device_type = self.clients[client_id].device_type
                            device_breakdown[device_type] += 1

                    channel_metrics[channel_id] = {
                        "client_count": len(client_ids),
                        "device_breakdown": dict(device_breakdown),
                        "client_ids": list(client_ids)
                    }
            return channel_metrics

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events for real-time monitoring"""
        with self._lock:
            return list(self.event_history)[-limit:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all clients"""
        with self._lock:
            if not self.clients:
                return {
                    "active_clients": 0,
                    "avg_processing_latency_ms": 0,
                    "avg_transcription_latency_ms": 0,
                    "overall_success_rate": 1.0,
                    "total_queue_size": 0
                }

            # Aggregate metrics across all clients
            all_processing_latencies = []
            all_transcription_latencies = []
            total_successful = 0
            total_failed = 0
            total_queue_size = 0

            for metrics in self.clients.values():
                all_processing_latencies.extend(metrics.processing_latencies)
                all_transcription_latencies.extend(metrics.transcription_latencies)
                total_successful += metrics.successful_transcriptions
                total_failed += metrics.failed_transcriptions
                total_queue_size += metrics.current_queue_size

            total_transcriptions = total_successful + total_failed
            overall_success_rate = total_successful / total_transcriptions if total_transcriptions > 0 else 1.0

            return {
                "active_clients": len(self.clients),
                "avg_processing_latency_ms": mean(all_processing_latencies) if all_processing_latencies else 0,
                "avg_transcription_latency_ms": mean(all_transcription_latencies) if all_transcription_latencies else 0,
                "median_processing_latency_ms": median(all_processing_latencies) if all_processing_latencies else 0,
                "overall_success_rate": overall_success_rate,
                "total_queue_size": total_queue_size,
                "connection_rate_per_minute": self.system.get_connection_rate(),
                "transcription_rate_per_minute": self.system.get_transcription_rate()
            }

    def _add_event(self, event_type: str, data: Dict[str, Any]):
        """Add event to history for real-time monitoring"""
        event = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.event_history.append(event)


class AudioProcessingMetrics(WebSocketMetrics):
    """Extended metrics specifically for audio processing"""

    def __init__(self):
        super().__init__()
        self.audio_formats: Dict[str, int] = defaultdict(int)  # format -> count
        self.chunk_sizes: deque = deque(maxlen=1000)  # Recent chunk sizes

    def record_audio_format(self, format_type: str):
        """Record audio format usage"""
        with self._lock:
            self.audio_formats[format_type] += 1

    def record_chunk_size(self, size: int):
        """Record audio chunk size for analysis"""
        with self._lock:
            self.chunk_sizes.append(size)

    def get_audio_format_stats(self) -> Dict[str, int]:
        """Get audio format usage statistics"""
        with self._lock:
            return dict(self.audio_formats)

    def get_chunk_size_stats(self) -> Dict[str, float]:
        """Get chunk size statistics"""
        with self._lock:
            if not self.chunk_sizes:
                return {"avg": 0, "median": 0, "min": 0, "max": 0}

            sizes = list(self.chunk_sizes)
            return {
                "avg": mean(sizes),
                "median": median(sizes),
                "min": min(sizes),
                "max": max(sizes),
                "count": len(sizes)
            }


# Global metrics instance
_global_metrics = None

def get_metrics() -> AudioProcessingMetrics:
    """Get or create global metrics instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = AudioProcessingMetrics()
    return _global_metrics

def reset_metrics():
    """Reset global metrics (for testing)"""
    global _global_metrics
    _global_metrics = AudioProcessingMetrics()