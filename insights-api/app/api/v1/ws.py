import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Optional
 
from app.services.connection_manager_service import manager
from app.services.event_dispatcher_service import dispatcher
from app.core.websocket_auth import authenticate_user_from_token
from app.models import User
from app.schemas.websocket import (
    WSMessage, SubscriptionRequest, UnsubscriptionRequest,
    WSMessageType, HeartbeatMessage, AuthenticationMessage, AuthenticationResponse
)
from app.domain.types import WebSocketEventType
from app.domain.events import SystemEvent
 
logger = logging.getLogger(__name__)
router = APIRouter()
 
 
@router.websocket("/health")
async def websocket_health_endpoint(websocket: WebSocket) -> None:
    """
    Health check endpoint for WebSocket connections
    """
    await websocket.accept()
    try:
        health_data = {
            "status": "healthy",
            "service": "websocket",
            "timestamp": manager.get_connection_stats()
        }
        await websocket.send_text(json.dumps(health_data))
        await websocket.close()
    except Exception as e:
        logger.error(f"Error in health check endpoint: {str(e)}", exc_info=True)
 
@router.websocket("/multiplex")
async def multiplexed_websocket_endpoint(websocket: WebSocket) -> None:
    """
    Secure WebSocket endpoint for multiplexed connections.
    Authentication is handled via the first message sent by the client.
   
    Client should send authentication message first:
    {
        "type": "authenticate",
        "data": {
            "token": "your-jwt-token"
        }
    }
    """
    await websocket.accept()
    user: Optional[User] = None
   
    try:
        # Wait for authentication message
        try:
            raw_message = await websocket.receive_text()
            message_data = json.loads(raw_message)
           
            if message_data.get("type") != WSMessageType.AUTHENTICATE:
                await send_auth_error(websocket, "First message must be authentication")
                return
           
            # Validate authentication message
            try:
                auth_msg = AuthenticationMessage(**message_data.get("data", {}))
            except Exception as e:
                await send_auth_error(websocket, f"Invalid authentication message format: {str(e)}")
                return
           
            # Authenticate user
            user = await authenticate_user_from_token(auth_msg.token)
            if not user:
                await send_auth_error(websocket, "Invalid authentication credentials")
                return
               
            # Send authentication success response
            auth_response = AuthenticationResponse(
                success=True,
                message="Authentication successful",
                user_id=user.id
            )
           
            ws_message = WSMessage(
                type=WSMessageType.CONNECTION_STATUS,
                data=auth_response.model_dump()
            )
           
            await websocket.send_text(ws_message.model_dump_json())
            await manager.connect_user(user.id, websocket)
            logger.info(f"User {user.id} ({user.email}) authenticated and connected to multiplexed WebSocket")
           
        except json.JSONDecodeError:
            await send_auth_error(websocket, "Invalid JSON format in authentication message")
            return
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            await send_auth_error(websocket, "Authentication failed")
            return
 
        # Handle subsequent messages
        while True:
            try:
                raw_message = await websocket.receive_text()
                message_data = json.loads(raw_message)
 
                await handle_websocket_message(message_data, websocket, user)
           
            except WebSocketDisconnect:
                logger.warning(f"User {user.id} ({user.email}) disconnected from multiplexed WebSocket")
                break
           
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in message from user {user.id} ({user.email}): {str(e)}")
                await send_error_message(websocket, user, "Invalid JSON format")
            except Exception as e:
                logger.error(f"Error handling message from user {user.id} ({user.email}): {str(e)}", exc_info=True)
                await send_error_message(websocket, user, "Message handling error")
   
    except Exception as e:
        logger.error(f"Unexpected error in multiplexed WebSocket endpoint: {str(e)}", exc_info=True)
   
    finally:
        if user:
            await manager.disconnect_user(user.id, websocket)
 
async def send_auth_error(websocket: WebSocket, message: str) -> None:
    """
    Send authentication error and close connection
    """
    try:
        auth_response = AuthenticationResponse(
            success=False,
            message=message
        )
       
        ws_message = WSMessage(
            type=WSMessageType.ERROR,
            data=auth_response.model_dump()
        )
       
        await websocket.send_text(ws_message.model_dump_json())
        await websocket.close(code=1008, reason="Authentication failed")
    except Exception as e:
        logger.error(f"Error sending auth error: {str(e)}")
 
async def handle_websocket_message(message_data: dict, websocket: WebSocket, user: User) -> None:
    """
    Handle incoming websocket messages from clients
    """
    try:
        message_type = message_data.get("type")
        data = message_data.get("data", {})
 
        if message_type == WSMessageType.SUBSCRIBE:
            await handle_subscription(user, websocket, data)
        elif message_type == WSMessageType.UNSUBSCRIBE:
            await handle_unsubscription(user, websocket, data)
        elif message_type == WSMessageType.HEARTBEAT:
            await handle_heartbeat(user, websocket, data)
        elif message_type == WSMessageType.AUTHENTICATE:
            # Authentication should only happen once at the beginning
            await send_error_message(websocket, user, "Already authenticated")
        else:
            logger.warning(f"Unknown message type: {message_type} from user {user.id} ({user.email})")
            await send_error_message(websocket, user, "Unknown message type")
       
    except Exception as e:
        logger.error(f"Error handling websocket message for user {user.id} ({user.email}): {str(e)}", exc_info=True)
        await send_error_message(websocket, user, "Message handling error")
 
async def handle_subscription(user: User, websocket: WebSocket, data: dict) -> None:
    """
    Handle subscription requests
    """
    try:
        channels = data.get("channels", [])
        filters = data.get("filters", {})
 
        if not channels:
            await send_error_message(websocket, user, "No channels provided for subscription")
            return
       
        validated_channels = []
        for channel in channels:
            if await validate_channel_access(user, channel):
                validated_channels.append(channel)
            else:
                logger.warning(f"User {user.id} ({user.email}) does not have access to channel {channel}")
       
        if not validated_channels:
            await send_error_message(websocket, user, "No valid channels provided for subscription")
            return
       
        response = await manager.subscribe_to_channels(user.id, websocket, validated_channels)
 
        ws_message = WSMessage(
            type=WSMessageType.CONNECTION_STATUS,
            data=response.model_dump()
        )
 
        await websocket.send_text(ws_message.model_dump_json())
        logger.info(f"User {user.id} subscribed to {len(validated_channels)} channels")
   
    except Exception as e:
        logger.error(f"Error handling subscription request for user {user.id} ({user.email}): {str(e)}", exc_info=True)
        await send_error_message(websocket, user, "Subscription error")
 
async def handle_unsubscription(user: User, websocket: WebSocket, data: dict):
    """Handle unsubscription requests"""
    try:
        channels = data.get("channels", [])
       
        if not channels:
            await send_error_message(websocket, "No channels specified for unsubscription")
            return
 
        response = await manager.unsubscribe_from_channels(user.id, websocket, channels)
 
        ws_message = WSMessage(
            type=WSMessageType.CONNECTION_STATUS,
            data=response.model_dump()
        )
        await websocket.send_text(ws_message.model_dump_json())
       
        logger.info(f"User {user.id} unsubscribed from {len(channels)} channels")
       
    except Exception as e:
        logger.error(f"Error handling unsubscription: {e}")
        await send_error_message(websocket, "Unsubscription error")
 
async def handle_heartbeat(user: User, websocket: WebSocket, data: dict):
    """
    Handle heartbeat messages
    """
    try:
        manager._update_activity(websocket)
 
        subscriptions = manager.get_user_subscriptions(user.id)
        total_subscriptions = sum(len(channels) for channels in subscriptions.values())
 
        heartbeat = HeartbeatMessage(
            active_subscriptions=total_subscriptions
        )
 
        ws_message = WSMessage(
            type=WSMessageType.HEARTBEAT,
            data=heartbeat.model_dump()
        )
 
        await websocket.send_text(ws_message.model_dump_json())
 
    except Exception as e:
        logger.error(f"Error handling heartbeat: {e}")
 
async def validate_channel_access(user: User, channel: str) -> bool:
    """
    Validates if a user has access to a specific channel
    """
    return manager._is_valid_channel(channel, user.id) # TODO: Do we even need this function?
 
async def send_error_message(websocket: WebSocket, user: User, message: str) -> None:
    """
    Sends an error message to a WebSocket client
    """
    try:
        error_msg = WSMessage(
            type=WSMessageType.ERROR,
            data={
                "error": message
            }
        )
        await websocket.send_text(error_msg.model_dump_json())
    except Exception as e:
        logger.error(f"Error sending error message to user {user.id} ({user.email}): {str(e)}", exc_info=True)
 