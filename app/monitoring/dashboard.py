"""
Real-time monitoring dashboard for WebSocket connections and audio processing.
Provides REST API endpoints for metrics visualization and system health monitoring.
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request
from pydantic import BaseModel

from .metrics import get_metrics, AudioProcessingMetrics


class DashboardResponse(BaseModel):
    """Response model for dashboard data"""
    timestamp: str
    uptime_seconds: float
    active_clients: int
    device_breakdown: Dict[str, int]
    performance: Dict[str, Any]
    queue_status: Dict[str, Dict[str, Any]]
    channels: Dict[str, Dict[str, Any]]
    system_health: Dict[str, Any]


class MonitoringDashboard:
    """Real-time monitoring dashboard for multi-client WebSocket connections"""

    def __init__(self):
        self.metrics: AudioProcessingMetrics = get_metrics()
        self.router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
        self._setup_routes()

        # WebSocket connections for real-time monitoring
        self.monitoring_connections: Dict[str, WebSocket] = {}

    def _setup_routes(self):
        """Setup dashboard API routes"""

        @self.router.get("/dashboard", response_model=DashboardResponse)
        async def get_dashboard():
            """Get comprehensive dashboard data"""
            return await self._get_dashboard_data()

        @self.router.get("/clients")
        async def get_client_list():
            """Get list of all active clients with basic info"""
            clients = self.metrics.get_all_client_metrics()
            client_list = []

            for client_id, metrics in clients.items():
                client_list.append({
                    "client_id": client_id,
                    "device_type": metrics.device_type,
                    "connection_duration": metrics.get_connection_duration(),
                    "last_activity": time.time() - metrics.last_activity,
                    "audio_chunks": metrics.total_audio_chunks,
                    "queue_size": metrics.current_queue_size,
                    "success_rate": metrics.get_success_rate(),
                    "avg_latency": metrics.get_avg_processing_latency()
                })

            return {
                "clients": client_list,
                "total_count": len(client_list),
                "timestamp": datetime.now().isoformat()
            }

        @self.router.get("/client/{client_id}")
        async def get_client_details(client_id: str):
            """Get detailed metrics for specific client"""
            metrics = self.metrics.get_client_metrics(client_id)
            if not metrics:
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

            return {
                "client_id": client_id,
                "device_type": metrics.device_type,
                "connection_time": datetime.fromtimestamp(metrics.connection_time).isoformat(),
                "connection_duration": metrics.get_connection_duration(),
                "last_activity": datetime.fromtimestamp(metrics.last_activity).isoformat(),
                "activity_age": time.time() - metrics.last_activity,
                "audio_stats": {
                    "total_chunks": metrics.total_audio_chunks,
                    "total_bytes": metrics.total_audio_bytes,
                    "avg_chunk_size": metrics.total_audio_bytes / max(1, metrics.total_audio_chunks)
                },
                "queue_stats": {
                    "current_size": metrics.current_queue_size,
                    "max_size": metrics.max_queue_size
                },
                "performance": {
                    "avg_processing_latency_ms": metrics.get_avg_processing_latency(),
                    "avg_transcription_latency_ms": metrics.get_avg_transcription_latency(),
                    "recent_processing_latencies": list(metrics.processing_latencies)[-10:],
                    "recent_transcription_latencies": list(metrics.transcription_latencies)[-10:]
                },
                "transcription_stats": {
                    "successful": metrics.successful_transcriptions,
                    "failed": metrics.failed_transcriptions,
                    "success_rate": metrics.get_success_rate(),
                    "total": metrics.successful_transcriptions + metrics.failed_transcriptions
                },
                "session_stats": {
                    "text_length": metrics.session_text_length,
                    "line_breaks": metrics.session_line_breaks,
                    "estimated_paragraphs": metrics.session_line_breaks + 1
                },
                "errors": {
                    "connection_errors": metrics.connection_errors
                }
            }

        @self.router.get("/performance")
        async def get_performance_summary():
            """Get system performance summary"""
            return self.metrics.get_performance_summary()

        @self.router.get("/channels")
        async def get_channel_status():
            """Get status of all active channels"""
            return {
                "channels": self.metrics.get_channel_metrics(),
                "timestamp": datetime.now().isoformat()
            }

        @self.router.get("/events")
        async def get_recent_events(limit: int = 100):
            """Get recent system events"""
            events = self.metrics.get_recent_events(limit)
            return {
                "events": events,
                "count": len(events),
                "timestamp": datetime.now().isoformat()
            }

        @self.router.get("/timeout-analysis")
        async def analyze_client_timeouts(request: Request, timeout_threshold: int = 300):
            """Analyze client connections for potential timeouts (read-only)"""
            # This is SAFE monitoring - no cleanup, only analysis
            try:
                connection_manager = request.app.state.connection_manager
                current_time = time.time()

                timeout_analysis = []
                warnings = []

                # Analyze all tracked clients
                for client_id, metrics in self.metrics.get_all_client_metrics().items():
                    time_since_activity = current_time - metrics.last_activity
                    connection_duration = metrics.get_connection_duration()

                    # Check if client exists in connection manager
                    is_active_connection = client_id in connection_manager.active_connections

                    analysis = {
                        "client_id": client_id,
                        "device_type": metrics.device_type,
                        "time_since_last_activity": round(time_since_activity, 1),
                        "connection_duration": round(connection_duration, 1),
                        "is_active_websocket": is_active_connection,
                        "status": "healthy"
                    }

                    # Determine status based on thresholds
                    if not is_active_connection:
                        analysis["status"] = "stale_connection"
                        warnings.append(f"Client {client_id} in metrics but not in active connections")
                    elif time_since_activity > timeout_threshold:
                        analysis["status"] = "inactive_timeout"
                        warnings.append(f"Client {client_id} inactive for {time_since_activity:.1f}s")
                    elif time_since_activity > timeout_threshold * 0.8:
                        analysis["status"] = "approaching_timeout"

                    timeout_analysis.append(analysis)

                # Summary statistics
                total_clients = len(timeout_analysis)
                stale_count = len([c for c in timeout_analysis if c["status"] == "stale_connection"])
                timeout_count = len([c for c in timeout_analysis if c["status"] == "inactive_timeout"])

                return {
                    "analysis_status": "completed",
                    "timeout_threshold_seconds": timeout_threshold,
                    "summary": {
                        "total_clients": total_clients,
                        "stale_connections": stale_count,
                        "timed_out_clients": timeout_count,
                        "healthy_clients": total_clients - stale_count - timeout_count
                    },
                    "clients": timeout_analysis,
                    "warnings": warnings,
                    "recommendations": [
                        f"Consider cleanup for {stale_count} stale connections" if stale_count > 0 else "No cleanup needed",
                        f"Monitor {timeout_count} timed-out clients" if timeout_count > 0 else "All clients active"
                    ],
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                return {
                    "analysis_status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        @self.router.get("/health")
        async def get_system_health():
            """Get system health status"""
            system_metrics = self.metrics.get_system_metrics()
            performance = self.metrics.get_performance_summary()

            # Determine health status based on metrics
            health_issues = []
            health_score = 100

            # Check for high queue backlogs
            total_queue_size = performance.get("total_queue_size", 0)
            if total_queue_size > 10:
                health_issues.append(f"High queue backlog: {total_queue_size} pending items")
                health_score -= 20

            # Check for high latency
            avg_latency = performance.get("avg_processing_latency_ms", 0)
            if avg_latency > 2000:
                health_issues.append(f"High processing latency: {avg_latency:.0f}ms")
                health_score -= 15

            # Check for low success rate
            success_rate = performance.get("overall_success_rate", 1.0)
            if success_rate < 0.9:
                health_issues.append(f"Low success rate: {success_rate:.1%}")
                health_score -= 25

            # Check for connection issues (high error rate)
            if system_metrics.total_errors > 0:
                error_rate = system_metrics.total_errors / max(1, system_metrics.total_transcriptions)
                if error_rate > 0.1:
                    health_issues.append(f"High error rate: {error_rate:.1%}")
                    health_score -= 10

            # Determine overall status
            if health_score >= 90:
                status = "healthy"
            elif health_score >= 70:
                status = "warning"
            else:
                status = "critical"

            return {
                "status": status,
                "health_score": max(0, health_score),
                "issues": health_issues,
                "uptime_seconds": system_metrics.get_uptime(),
                "active_clients": len(self.metrics.get_all_client_metrics()),
                "total_connections": system_metrics.total_connections,
                "total_transcriptions": system_metrics.total_transcriptions,
                "total_errors": system_metrics.total_errors,
                "performance_summary": performance,
                "timestamp": datetime.now().isoformat()
            }

        @self.router.get("/audio-stats")
        async def get_audio_statistics():
            """Get audio processing statistics"""
            format_stats = self.metrics.get_audio_format_stats()
            chunk_stats = self.metrics.get_chunk_size_stats()

            return {
                "format_usage": format_stats,
                "chunk_size_stats": chunk_stats,
                "timestamp": datetime.now().isoformat()
            }

        @self.router.get("/heartbeat")
        async def get_heartbeat_statistics(request: Request):
            """Get heartbeat system statistics"""
            try:
                connection_manager = request.app.state.connection_manager
                heartbeat_stats = connection_manager.heartbeat.get_heartbeat_stats()

                return {
                    "heartbeat_status": "active" if heartbeat_stats["heartbeat_enabled"] else "inactive",
                    "statistics": heartbeat_stats,
                    "ping_interval_seconds": connection_manager.heartbeat.ping_interval,
                    "pong_timeout_seconds": connection_manager.heartbeat.pong_timeout,
                    "max_missed_pongs": connection_manager.heartbeat.max_missed_pongs,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                return {
                    "heartbeat_status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        @self.router.get("/transcriber-status")
        async def get_transcriber_status(request: Request):
            """Get current transcriber type and switching capability"""
            try:
                # Get transcriber manager from app state
                transcriber_manager = getattr(request.app.state, 'transcriber_manager', None)

                if transcriber_manager:
                    status = transcriber_manager.get_status()
                    return {
                        "transcriber_available": True,
                        **status,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "transcriber_available": False,
                        "message": "TranscriberManager not initialized",
                        "timestamp": datetime.now().isoformat()
                    }

            except Exception as e:
                return {
                    "transcriber_available": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        @self.router.post("/switch-transcriber")
        async def switch_transcriber_type(request: Request, target_type: str = "spsc"):
            """Hot-swap transcriber type without server restart"""
            try:
                # Get transcriber manager from app state
                transcriber_manager = getattr(request.app.state, 'transcriber_manager', None)

                if not transcriber_manager:
                    return {
                        "success": False,
                        "error": "TranscriberManager not available",
                        "timestamp": datetime.now().isoformat()
                    }

                # Validate target type
                if target_type not in ["standard", "spsc"]:
                    return {
                        "success": False,
                        "error": f"Invalid transcriber type: {target_type}. Use 'standard' or 'spsc'",
                        "timestamp": datetime.now().isoformat()
                    }

                # Perform hot-swap
                if target_type == "spsc":
                    result = await transcriber_manager.switch_to_spsc()
                else:
                    result = await transcriber_manager.switch_to_standard()

                result["timestamp"] = datetime.now().isoformat()
                return result

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to switch to {target_type} transcriber",
                    "timestamp": datetime.now().isoformat()
                }

        @self.router.get("/validate-client/{client_id}")
        async def validate_client_registration(client_id: str, request: Request):
            """Validate if client is properly registered in all backend systems"""
            try:
                connection_manager = request.app.state.connection_manager

                # Check registration in all systems
                is_in_connections = client_id in connection_manager.active_connections
                is_in_metrics = client_id in connection_manager.metrics.get_all_client_metrics()
                is_in_heartbeat = client_id in connection_manager.heartbeat.client_heartbeats

                # Overall validation
                valid = is_in_connections and is_in_metrics and is_in_heartbeat
                missing_systems = []

                if not is_in_connections:
                    missing_systems.append("connection_manager")
                if not is_in_metrics:
                    missing_systems.append("metrics_system")
                if not is_in_heartbeat:
                    missing_systems.append("heartbeat_system")

                return {
                    "valid": valid,
                    "client_id": client_id,
                    "registrations": {
                        "connection_manager": is_in_connections,
                        "metrics_system": is_in_metrics,
                        "heartbeat_system": is_in_heartbeat
                    },
                    "missing_systems": missing_systems,
                    "recommendation": "re_identify" if not valid else "healthy",
                    "action_required": bool(missing_systems),
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                return {
                    "valid": False,
                    "client_id": client_id,
                    "error": str(e),
                    "recommendation": "re_connect",
                    "timestamp": datetime.now().isoformat()
                }

        @self.router.get("/validate-state")
        async def validate_connection_state(request: Request):
            """Read-only validation of ConnectionManager vs Metrics state consistency"""
            try:
                # Get connection manager from app state
                connection_manager = request.app.state.connection_manager

                # Get state from both systems
                cm_clients = set(connection_manager.active_connections.keys())
                metrics_clients = set(self.metrics.get_all_client_metrics().keys())

                # Find inconsistencies
                only_in_cm = cm_clients - metrics_clients
                only_in_metrics = metrics_clients - cm_clients
                consistent = cm_clients & metrics_clients

                # Calculate health
                total_expected = len(cm_clients)
                total_tracked = len(metrics_clients)
                max_clients = max(total_expected, total_tracked)
                consistency_score = len(consistent) / max(1, max_clients) * 100 if max_clients > 0 else 100

                return {
                    "validation_status": "healthy" if consistency_score == 100 else "inconsistent",
                    "consistency_score": round(consistency_score, 1),
                    "connection_manager": {
                        "active_connections": len(cm_clients),
                        "client_ids": list(cm_clients)
                    },
                    "metrics_system": {
                        "tracked_clients": len(metrics_clients),
                        "client_ids": list(metrics_clients)
                    },
                    "inconsistencies": {
                        "only_in_connection_manager": list(only_in_cm),
                        "only_in_metrics": list(only_in_metrics),
                        "consistent": list(consistent)
                    },
                    "recommendations": self._generate_cleanup_recommendations(only_in_cm, only_in_metrics),
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                return {
                    "validation_status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        @self.router.post("/cleanup-stale")
        async def manual_cleanup_stale_clients(request: Request, confirm: bool = False):
            """Manual cleanup of stale clients with admin confirmation"""
            # This is a SAFE manual operation - no automatic cleanup
            # Requires explicit confirmation parameter

            if not confirm:
                return {
                    "status": "confirmation_required",
                    "message": "Add ?confirm=true to execute cleanup",
                    "warning": "This will remove stale clients from metrics tracking",
                    "timestamp": datetime.now().isoformat()
                }

            try:
                # Get connection manager from app state
                connection_manager = request.app.state.connection_manager

                # Get state from both systems (same as validate-state)
                cm_clients = set(connection_manager.active_connections.keys())
                metrics_clients = set(self.metrics.get_all_client_metrics().keys())

                # Find clients to cleanup (only in metrics, not in connection manager)
                stale_clients = metrics_clients - cm_clients

                if not stale_clients:
                    return {
                        "status": "no_action_needed",
                        "message": "No stale clients found",
                        "connection_manager_clients": len(cm_clients),
                        "metrics_clients": len(metrics_clients),
                        "timestamp": datetime.now().isoformat()
                    }

                # Manual cleanup (SAFE - only removes from metrics, not connection manager)
                cleaned_count = 0
                cleanup_results = []

                for client_id in stale_clients:
                    try:
                        # Remove from metrics system only
                        self.metrics.record_client_disconnected(client_id, "manual_cleanup")
                        cleaned_count += 1
                        cleanup_results.append(f"✅ Removed {client_id} from metrics")
                    except Exception as e:
                        cleanup_results.append(f"❌ Failed to remove {client_id}: {e}")

                return {
                    "status": "cleanup_completed",
                    "message": f"Successfully cleaned {cleaned_count} stale clients",
                    "cleaned_clients": cleaned_count,
                    "stale_clients_found": len(stale_clients),
                    "cleanup_details": cleanup_results,
                    "remaining_state": {
                        "connection_manager_clients": len(cm_clients),
                        "metrics_clients": len(self.metrics.get_all_client_metrics())
                    },
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Cleanup failed due to error",
                    "timestamp": datetime.now().isoformat()
                }

    async def _get_dashboard_data(self) -> DashboardResponse:
        """Generate comprehensive dashboard data"""
        clients = self.metrics.get_all_client_metrics()
        system_metrics = self.metrics.get_system_metrics()
        performance = self.metrics.get_performance_summary()
        channels = self.metrics.get_channel_metrics()

        # Device breakdown
        device_breakdown = {}
        queue_status = {}

        for client_id, metrics in clients.items():
            # Device type counting
            device_type = metrics.device_type
            device_breakdown[device_type] = device_breakdown.get(device_type, 0) + 1

            # Queue status
            queue_status[client_id] = {
                "size": metrics.current_queue_size,
                "max_size": metrics.max_queue_size,
                "avg_latency_ms": metrics.get_avg_processing_latency(),
                "success_rate": metrics.get_success_rate(),
                "device_type": metrics.device_type,
                "connection_duration": metrics.get_connection_duration()
            }

        # System health assessment
        health_score = 100
        if performance.get("total_queue_size", 0) > 10:
            health_score -= 20
        if performance.get("avg_processing_latency_ms", 0) > 2000:
            health_score -= 15
        if performance.get("overall_success_rate", 1.0) < 0.9:
            health_score -= 25

        system_health = {
            "status": "healthy" if health_score >= 90 else "warning" if health_score >= 70 else "critical",
            "score": max(0, health_score),
            "uptime": system_metrics.get_uptime(),
            "peak_concurrent": system_metrics.peak_concurrent_clients,
            "connection_rate": system_metrics.get_connection_rate(),
            "transcription_rate": system_metrics.get_transcription_rate()
        }

        return DashboardResponse(
            timestamp=datetime.now().isoformat(),
            uptime_seconds=system_metrics.get_uptime(),
            active_clients=len(clients),
            device_breakdown=device_breakdown,
            performance=performance,
            queue_status=queue_status,
            channels=channels,
            system_health=system_health
        )

    # WebSocket endpoint for real-time monitoring
    async def websocket_monitor(self, websocket: WebSocket):
        """WebSocket endpoint for real-time monitoring updates"""
        monitor_id = f"monitor_{id(websocket)}"

        try:
            await websocket.accept()
            self.monitoring_connections[monitor_id] = websocket

            # Send initial dashboard data
            dashboard_data = await self._get_dashboard_data()
            await websocket.send_text(json.dumps({
                "type": "dashboard_data",
                "data": dashboard_data.dict()
            }))

            # Listen for requests
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    if message.get("type") == "request_update":
                        # Send updated dashboard data
                        dashboard_data = await self._get_dashboard_data()
                        await websocket.send_text(json.dumps({
                            "type": "dashboard_data",
                            "data": dashboard_data.dict()
                        }))

                    elif message.get("type") == "request_events":
                        # Send recent events
                        events = self.metrics.get_recent_events(50)
                        await websocket.send_text(json.dumps({
                            "type": "events",
                            "data": events
                        }))

                    elif message.get("type") == "subscribe_client":
                        # Subscribe to specific client updates
                        client_id = message.get("client_id")
                        if client_id:
                            client_metrics = self.metrics.get_client_metrics(client_id)
                            if client_metrics:
                                await websocket.send_text(json.dumps({
                                    "type": "client_data",
                                    "client_id": client_id,
                                    "data": {
                                        "queue_size": client_metrics.current_queue_size,
                                        "avg_latency": client_metrics.get_avg_processing_latency(),
                                        "success_rate": client_metrics.get_success_rate(),
                                        "activity": time.time() - client_metrics.last_activity
                                    }
                                }))

                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))

        except WebSocketDisconnect:
            pass
        finally:
            if monitor_id in self.monitoring_connections:
                del self.monitoring_connections[monitor_id]

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast event to all monitoring WebSocket connections"""
        if not self.monitoring_connections:
            return

        message = json.dumps({
            "type": "event",
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        })

        # Send to all connected monitors
        disconnected = []
        for monitor_id, websocket in self.monitoring_connections.items():
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(monitor_id)

        # Clean up disconnected monitors
        for monitor_id in disconnected:
            self.monitoring_connections.pop(monitor_id, None)

    def _generate_cleanup_recommendations(self, only_in_cm: set, only_in_metrics: set) -> List[str]:
        """Generate recommendations for fixing state inconsistencies"""
        recommendations = []

        if only_in_cm:
            recommendations.append(f"Add {len(only_in_cm)} missing clients to metrics tracking")

        if only_in_metrics:
            recommendations.append(f"Remove {len(only_in_metrics)} stale clients from metrics system")

        if not only_in_cm and not only_in_metrics:
            recommendations.append("State is consistent - no action needed")

        return recommendations