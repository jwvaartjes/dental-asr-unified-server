"""
API router for pairing endpoints.
"""
import json
import logging
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Response, Depends, HTTPException, status
from pydantic import BaseModel

from .service import ConnectionManager, PairingService
from .security import JWTHandler, SecurityMiddleware, get_client_ip
from .schemas import MessageValidator
from ..ai.realtime_transcriber import RealtimeTranscriber
from ..ai.blob_transcriber import BlobTranscriber

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["pairing"])

# Request models
class GeneratePairCodeRequest(BaseModel):
    desktop_session_id: str

class PairDeviceRequest(BaseModel):
    code: str
    mobile_session_id: str

class WSTokenRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


def get_pairing_service(request: Request) -> PairingService:
    """Dependency to get pairing service from app state."""
    return request.app.state.pairing_service

def get_security_middleware(request: Request) -> SecurityMiddleware:
    """Dependency to get security middleware from app state."""
    return request.app.state.security_middleware


def _detect_wav_format(audio_message: dict) -> bool:
    """Detect if audio message contains WAV format data."""
    try:
        # Try to extract data and check for RIFF header
        data = None
        for field in ["data", "audio_data"]:
            if field in audio_message:
                field_data = audio_message[field]
                if isinstance(field_data, bytes):
                    data = field_data
                elif isinstance(field_data, str):
                    try:
                        data = base64.b64decode(field_data)
                    except:
                        continue
                break

        if data and len(data) >= 12:
            return data[:4] == b'RIFF' and data[8:12] == b'WAVE'

    except Exception:
        pass

    return False


# API Endpoints
@router.post("/generate-pair-code")
async def generate_pair_code(
    request_data: GeneratePairCodeRequest,
    request: Request,
    pairing_service: PairingService = Depends(get_pairing_service),
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Generate a 6-digit pairing code for desktop."""
    # Validate request
    await security.validate_request(request)

    # Extract desktop auth info for mobile inheritance
    desktop_auth_info = {}
    try:
        # Try to get user info from Authorization header, httpOnly cookie, or session
        token = None

        # First try Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

        # Fallback: try httpOnly cookie
        if not token:
            token = request.cookies.get("session_token")

        # Verify token if found
        if token:
            payload = JWTHandler.verify_token(token)
            if payload:
                # Handle different token formats (login vs WebSocket tokens)
                user_identifier = payload.get("user") or payload.get("email") or payload.get("user_id")
                desktop_auth_info = {
                    "username": user_identifier,
                    "device_type": payload.get("device_type", "desktop"),
                    "inherited_at": datetime.utcnow().isoformat()
                }

        # No fallback - require authentication
        if not desktop_auth_info:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for pairing"
            )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.warning(f"Could not extract desktop auth info: {e}")
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )

    # Generate pairing code with auth info
    result = await pairing_service.initiate_pairing(
        request_data.desktop_session_id,
        desktop_auth_info
    )
    return result


@router.get("/current-session")
async def get_current_session(
    request: Request,
    pairing_service: PairingService = Depends(get_pairing_service)
):
    """Get current active pairing session for authenticated user."""
    # Extract user auth info (same logic as generate-pair-code)
    try:
        token = None

        # Try Authorization header first
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

        # Fallback: try httpOnly cookie
        if not token:
            token = request.cookies.get("session_token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Verify token
        payload = JWTHandler.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication"
            )

        # Get user identifier
        user_identifier = payload.get("user") or payload.get("email") or payload.get("user_id")

        # Check if user has active sessions
        if user_identifier in pairing_service.user_sessions:
            active_sessions = pairing_service.user_sessions[user_identifier]

            if active_sessions:
                # Find the session's channel info
                for session_id in active_sessions:
                    client_info = pairing_service.manager.get_client_info(session_id)
                    if client_info and client_info.get("channel"):
                        channel_id = client_info["channel"]
                        # Extract pairing code from channel_id (format: "pair-123456")
                        if channel_id.startswith("pair-"):
                            code = channel_id.replace("pair-", "")
                            return {
                                "active": True,
                                "code": code,
                                "channel_id": channel_id,
                                "session_id": session_id
                            }

        # No active session found
        return {"active": False}

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Error getting current session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session info"
        )


@router.post("/pair-device")
async def pair_device(
    request_data: PairDeviceRequest,
    request: Request,
    pairing_service: PairingService = Depends(get_pairing_service),
    security: SecurityMiddleware = Depends(get_security_middleware)
):
    """Pair mobile device with desktop using code."""
    # Validate request with pairing-specific rate limiting
    await security.validate_request(request)
    
    # Additional pairing attempt rate limiting
    if security.ws_rate_limiter:
        if hasattr(security.ws_rate_limiter, 'can_attempt_pairing'):
            client_ip = get_client_ip(request)
            can_pair, retry_after = security.ws_rate_limiter.can_attempt_pairing(client_ip)
            if not can_pair:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many pairing attempts. Retry after {retry_after} seconds",
                    headers={"Retry-After": str(retry_after)}
                )
    
    # Validate pairing
    result = await pairing_service.validate_pairing(
        request_data.code,
        request_data.mobile_session_id
    )
    return result


async def get_message_size_limit_for_user(template_service, admin_user_id: str) -> int:
    """Get WebSocket message size limit - prioritize audio functionality."""
    # Always use 1MB for audio to ensure transcription works
    # Template-based limits can be implemented later if needed
    return 1024 * 1024  # 1MB for all WebSocket messages (audio priority)


# WebSocket endpoint (separate from APIRouter)
async def websocket_endpoint(
    websocket: WebSocket,
    connection_manager: ConnectionManager,
    security_middleware: SecurityMiddleware,
    template_service,
    data_registry,
    ai_factory=None,
    normalization_pipeline=None
):
    """WebSocket endpoint for real-time communication."""
    client_id = f"client_{id(websocket)}"
    client_ip = get_client_ip(websocket=websocket)

    # Initialize transcribers if AI factory available
    streaming_transcriber = None
    blob_transcriber = None
    original_streaming_transcriber = None

    if ai_factory:
        # Use blob transcriber for WAV blobs (file upload API quality)
        blob_transcriber = BlobTranscriber(ai_factory, normalization_pipeline)
        logger.info(f"🎯 Blob transcriber initialized for client {client_id} (file upload quality)")

        # Use original streaming transcriber for binary PCM chunks
        from ..ai.streaming_transcriber import StreamingTranscriber
        original_streaming_transcriber = StreamingTranscriber(ai_factory, normalization_pipeline, data_registry)
        logger.info(f"🔄 Original streaming transcriber initialized for client {client_id} (binary PCM + dental prompts)")

        # Keep realtime transcriber for other cases
        streaming_transcriber = RealtimeTranscriber(ai_factory, normalization_pipeline)
        logger.info(f"⚙️ Realtime transcriber available for client {client_id}")
    
    # Validate WebSocket connection
    is_valid, error_reason = await security_middleware.validate_websocket(websocket)
    if not is_valid:
        logger.warning(f"WebSocket rejected from {client_ip}: {error_reason}")
        await websocket.close(code=1008, reason=error_reason or "Connection rejected")
        return
    
    # Handle Bearer token authentication
    subprotocol = security_middleware.handle_bearer_token(websocket)
    
    # Accept connection
    if subprotocol:
        await websocket.accept(subprotocol=subprotocol)
    else:
        await websocket.accept()
    
    # Register with connection manager
    connection_manager.active_connections[client_id] = websocket
    connection_manager.connection_ips[client_id] = client_ip

    # Register with monitoring metrics
    if hasattr(connection_manager, 'metrics') and connection_manager.metrics:
        connection_manager.metrics.record_client_connected(client_id, "desktop", client_ip)

    # Register with rate limiter if available
    if security_middleware.ws_rate_limiter:
        if hasattr(security_middleware.ws_rate_limiter, 'register_connection'):
            security_middleware.ws_rate_limiter.register_connection(client_ip, client_id)

    logger.info(f"Client {client_id} connected from {client_ip}")
    
    try:
        # Get admin user ID and template-based message size limit
        admin_user_id = data_registry.loader.get_admin_id()
        message_size_limit = await get_message_size_limit_for_user(template_service, admin_user_id)
        logger.info(f"WebSocket message size limit for template: {message_size_limit // 1024}KB")

        # Send initial connection success
        await connection_manager.send_personal_message(
            json.dumps({"type": "connected", "client_id": client_id}),
            client_id
        )
        
        while True:
            # Receive message (either text or binary)
            try:
                message = await websocket.receive()

                # Handle disconnect messages first
                if message["type"] == "websocket.disconnect":
                    logger.info(f"🔌 Client {client_id} disconnected normally")
                    break

                # Handle both text and binary messages
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        data = message["text"]
                        is_binary = False
                        logger.debug(f"📝 Received text message from {client_id}: {len(data)} chars")
                    elif "bytes" in message:
                        # Handle binary audio data with channel-aware routing
                        binary_data = message["bytes"]
                        logger.info(f"🎵 Received binary audio from {client_id}: {len(binary_data)} bytes")

                        # Get client info for channel-aware transcription routing
                        client_info = connection_manager.client_info.get(client_id, {})
                        channel_id = client_info.get("channel")
                        device_type = client_info.get("device_type", "unknown")

                        logger.info(f"🔍 Binary audio routing: device={device_type}, channel={channel_id}")

                        # Create audio message for streaming transcriber
                        audio_message = {
                            "type": "audio_chunk",
                            "data": binary_data,
                            "format": "raw",
                            "timestamp": time.time()
                        }

                        # Handle streaming transcription with channel-aware routing
                        if original_streaming_transcriber:
                            try:
                                transcription_triggered = await original_streaming_transcriber.handle_audio_chunk(
                                    client_id,
                                    audio_message,
                                    connection_manager
                                )
                                if transcription_triggered:
                                    route_info = f"channel={channel_id}" if channel_id else "standalone"
                                    logger.info(f"🎯 Binary audio transcription triggered: {device_type} → {route_info}")
                            except Exception as e:
                                logger.error(f"Binary audio transcription error for {client_id}: {e}")
                        else:
                            logger.warning(f"No original streaming transcriber available for binary audio from {client_id}")

                        # Skip further processing for binary data
                        continue
                    else:
                        logger.warning(f"Received unknown message type from {client_id}: {message}")
                        continue
                else:
                    logger.warning(f"Received non-websocket message from {client_id}: {message}")
                    continue

            except Exception as e:
                # Check if this is a disconnect-related error
                if "disconnect" in str(e).lower() or "connection" in str(e).lower():
                    logger.info(f"🔌 Client {client_id} disconnected with error: {e}")
                    break
                logger.error(f"Error receiving WebSocket message from {client_id}: {e}")
                break  # Exit on any other error to prevent infinite loops

            # Template-aware message size validation (only for text messages)
            message_size = len(data.encode())
            if message_size > message_size_limit:
                logger.warning(f"Message from {client_id} exceeds template-based size limit: {message_size} > {message_size_limit}")
                await connection_manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": f"Message exceeds maximum size limit ({message_size_limit // 1024}KB for current template)",
                        "size_limit": message_size_limit,
                        "message_size": message_size
                    }),
                    client_id
                )
                continue
            
            # Rate limiting check
            if security_middleware.ws_rate_limiter:
                if hasattr(security_middleware.ws_rate_limiter, 'can_send_message'):
                    can_send, retry_after = security_middleware.ws_rate_limiter.can_send_message(client_id)
                    if not can_send:
                        logger.warning(f"Rate limit exceeded for {client_id}")
                        await connection_manager.send_personal_message(
                            json.dumps({"type": "error", "message": f"Rate limit exceeded. Retry after {retry_after:.1f} seconds"}),
                            client_id
                        )
                        continue
            
            # Parse message
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {client_id}")
                await connection_manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid message format"}),
                    client_id
                )
                continue
            
            # Validate message schema if validator available
            try:
                is_valid, validated_msg, error = MessageValidator.validate_message(message)
                if not is_valid:
                    logger.warning(f"Invalid message schema from {client_id}: {error}")
                    await connection_manager.send_personal_message(
                        json.dumps({"type": "error", "message": f"Invalid message: {error}"}),
                        client_id
                    )
                    continue
                if validated_msg:
                    message = validated_msg.model_dump()
            except:
                # MessageValidator not available, skip validation
                pass
            
            logger.info(f"📨 Received from {client_id}: {message.get('type')} (data size: {len(data)} bytes)")

            # Update activity tracking for timeout management
            connection_manager.update_activity(client_id)

            # Handle different message types
            msg_type = message.get("type")
            
            if msg_type == "mobile_init":
                device_type = message.get("device_type", "mobile")
                pairing_code = message.get("pairing_code")
                if pairing_code:
                    channel_id = f"pair-{pairing_code}"
                    await connection_manager.join_channel(client_id, channel_id, device_type)
                    await connection_manager.send_personal_message(
                        json.dumps({"type": "channel_joined", "channel": channel_id}),
                        client_id
                    )
                    
            elif msg_type == "join_channel":
                channel_id = message.get("channel")
                device_type = message.get("device_type", "unknown")
                if channel_id:
                    await connection_manager.join_channel(client_id, channel_id, device_type)
                    await connection_manager.send_personal_message(
                        json.dumps({"type": "channel_joined", "channel": channel_id}),
                        client_id
                    )
                    
            elif msg_type == "identify":
                device_type = message.get("device_type", "desktop")
                session_id = message.get("session_id", "unknown")

                # Enhanced device identification with session tracking
                import time
                identification_time = time.time()

                connection_manager.client_info[client_id] = {
                    "device_type": device_type,
                    "session_id": session_id,
                    "identified": True,
                    "identification_time": identification_time
                }

                # ATOMIC MULTI-SYSTEM REGISTRATION (prevents state drift)
                registrations = []

                # 1. Ensure connection manager registration
                if client_id not in connection_manager.active_connections:
                    connection_manager.active_connections[client_id] = websocket
                    registrations.append("connection_manager")

                # 2. Ensure metrics registration with correct device type
                if hasattr(connection_manager, 'metrics') and connection_manager.metrics:
                    connection_manager.metrics.record_client_connected(client_id, device_type, client_ip)
                    registrations.append("metrics_system")

                # 3. Ensure heartbeat registration
                if hasattr(connection_manager, 'heartbeat') and connection_manager.heartbeat:
                    connection_manager.heartbeat.register_client(client_id)
                    registrations.append("heartbeat_system")

                # Update activity on identification
                connection_manager.update_activity(client_id)

                logger.info(f"✅ Client {client_id} ({device_type}) registered in systems: {registrations}")

                logger.info(f"✅ Client {client_id} identified as {device_type} (session: {session_id})")

                # Send enhanced identification confirmation with registration status
                await connection_manager.send_personal_message(
                    json.dumps({
                        "type": "identified",
                        "device_type": device_type,
                        "session_id": session_id,
                        "registered_systems": registrations,
                        "registration_status": "fully_registered" if len(registrations) >= 2 else "partial_registration",
                        "timestamp": float(identification_time)  # Ensure JSON serializable
                    }),
                    client_id
                )
                
            elif msg_type == "channel_message":
                channel_id = message.get("channelId")
                if channel_id:
                    # Forward the entire message to other devices in channel (simple, like before)
                    await connection_manager.broadcast_to_channel(
                        channel_id,
                        message,
                        exclude=client_id
                    )

            elif msg_type == "settings_sync":
                channel_id = message.get("channelId")
                if channel_id:
                    # Forward settings sync to other devices in channel
                    await connection_manager.broadcast_to_channel(
                        channel_id,
                        message,
                        exclude=client_id
                    )

            elif msg_type == "audio_chunk" or msg_type == "audio_data" or msg_type == "audio_stream":
                # Get channel from client info and forward to desktop
                client_info = connection_manager.client_info.get(client_id, {})
                channel_id = client_info.get("channel")

                logger.info(f"🎵 Audio message received from {client_id}: type={msg_type}, channel={channel_id}, size={message_size}B, limit={message_size_limit}B")

                # Handle transcription with optimal routing
                if msg_type in ["audio_chunk", "audio_stream", "audio_data"]:
                    try:
                        # Check if this is a WAV blob for blob transcription (file upload quality)
                        format_field = message.get("format", "").lower()
                        is_wav_blob = (format_field in ["wav", "wave"] or
                                      _detect_wav_format(message))

                        transcription_triggered = False

                        if is_wav_blob and blob_transcriber:
                            # Use blob transcriber for WAV (file upload API quality)
                            logger.info(f"🎯 Using blob transcriber for WAV from {client_id}")
                            transcription_triggered = await blob_transcriber.handle_wav_blob(
                                client_id, message, connection_manager
                            )
                            # Don't use streaming transcriber for WAV blobs

                        elif streaming_transcriber:
                            # Use streaming transcriber for PCM chunks only
                            logger.info(f"🔊 Using streaming transcriber for PCM from {client_id}")
                            transcription_triggered = await streaming_transcriber.handle_audio_message(
                                client_id, message, connection_manager
                            )
                        else:
                            logger.warning(f"No transcriber available for {client_id}")

                        if transcription_triggered:
                            method = "blob" if is_wav_blob else "streaming"
                            logger.info(f"🎯 {method} transcription triggered for {client_id}")

                    except Exception as e:
                        logger.error(f"Audio transcription error for {client_id}: {e}")

                # Forward audio to channel (for pairing functionality)
                if channel_id:
                    await connection_manager.broadcast_to_channel(
                        channel_id,
                        message,
                        exclude=client_id
                    )
                    logger.info(f"🎵 Audio forwarded to channel {channel_id}")
                else:
                    logger.warning(f"🎵 Audio message from {client_id} has no channel - not forwarded")

            elif msg_type == "ping":
                # RFC compliant: Client sends ping, server responds with pong
                timestamp = message.get("timestamp", time.time())

                # Ensure timestamp is JSON serializable (convert datetime to float if needed)
                if hasattr(timestamp, 'timestamp'):  # datetime object
                    timestamp = timestamp.timestamp()
                elif not isinstance(timestamp, (int, float)):
                    timestamp = time.time()

                # Track ping reception for heartbeat monitoring
                connection_manager.heartbeat.handle_ping(client_id, timestamp)

                # Send pong response back to client (JSON safe timestamp)
                await connection_manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": timestamp}),
                    client_id
                )

                # Track pong sent
                connection_manager.heartbeat.handle_pong_sent(client_id)
                logger.debug(f"💓 Ping from {client_id} → responded with pong")

            elif msg_type == "pong":
                # Handle pong from client (should not happen in RFC compliant flow)
                logger.debug(f"💭 Unexpected pong from {client_id} (clients should send ping, not pong)")

            else:
                # Forward unknown message types to channel (for extensibility)
                client_info = connection_manager.client_info.get(client_id, {})
                channel_id = client_info.get("channel")
                if channel_id:
                    await connection_manager.broadcast_to_channel(
                        channel_id,
                        message,
                        exclude=client_id
                    )
                    
    except WebSocketDisconnect:
        await connection_manager.disconnect(client_id)
        # Clean up streaming transcriber resources (with final flush)
        if streaming_transcriber:
            await streaming_transcriber.cleanup_client(client_id, connection_manager)
        # Unregister from monitoring metrics
        if hasattr(connection_manager, 'metrics') and connection_manager.metrics:
            connection_manager.metrics.record_client_disconnected(client_id, "normal_disconnect")

        # Unregister from rate limiter
        if security_middleware.ws_rate_limiter and client_id in connection_manager.connection_ips:
            if hasattr(security_middleware.ws_rate_limiter, 'unregister_connection'):
                security_middleware.ws_rate_limiter.unregister_connection(
                    connection_manager.connection_ips[client_id],
                    client_id
                )
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await connection_manager.disconnect(client_id)
        # Clean up streaming transcriber resources (with final flush)
        if streaming_transcriber:
            await streaming_transcriber.cleanup_client(client_id, connection_manager)
        # Unregister from monitoring metrics
        if hasattr(connection_manager, 'metrics') and connection_manager.metrics:
            connection_manager.metrics.record_client_disconnected(client_id, "error_disconnect")
        # Unregister from rate limiter
        if security_middleware.ws_rate_limiter and client_id in connection_manager.connection_ips:
            if hasattr(security_middleware.ws_rate_limiter, 'unregister_connection'):
                security_middleware.ws_rate_limiter.unregister_connection(
                    connection_manager.connection_ips[client_id],
                    client_id
                )