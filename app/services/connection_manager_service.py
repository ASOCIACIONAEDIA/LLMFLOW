from fastapi import WebSocket
import logging
from typing import Dict, List, Set, Tuple, Optional, Any 
import json
import asyncio
from datetime import datetime, timedelta 

from app.schemas.websocket import (
    WSMessage,
    SubscriptionRequest,
    SubscriptionResponse,
    EventMessage,
    ConnectionStatus,
    HeartbeatMessage
)
from app.domain.types import WSMessageType, WebSocketEventType
from app.domain.events import BaseEvent

logger = logging.getLogger(__name__)

class MultiplexedConnectionManager:
    def __init__(self):
        # User connections: user_id -> {websocket -> subscription_set}
        self.user_connections: Dict[int, Dict[WebSocket, Set[str]]] = {}
        
        # Reverse lookup: channel_id -> set of (user_id, websocket) pairs
        self.channel_subscribers: Dict[str, Set[Tuple[int, WebSocket]]] = {}
        
        # Connection metadata: websocket -> connection info
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[WebSocket, datetime] = {}
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_stale_connections())

    async def connect_user(self, user_id: int, websocket: WebSocket) -> bool:
        """Connect a user with an empty subscription set"""
        try:
            await websocket.accept()
            
            if user_id not in self.user_connections:
                self.user_connections[user_id] = {}
                
            self.user_connections[user_id][websocket] = set()
            self.connection_metadata[websocket] = {
                "user_id": user_id,
                "connected_at": datetime.now(),
                "last_activity": datetime.now()
            }
            self.last_heartbeat[websocket] = datetime.now()
            
            logger.info(f"User {user_id} connected to multiplexed WebSocket")
            
            # Send connection confirmation
            status = ConnectionStatus(
                user_id=user_id,
                connected=True,
                subscriptions=[],
                connection_time=datetime.now()
            )
            
            await self._send_to_websocket(websocket, WSMessage(
                type=WSMessageType.CONNECTION_STATUS,
                data=status.model_dump()
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting user {user_id}: {e}")
            return False

    async def disconnect_user(self, user_id: int, websocket: WebSocket):
        """Disconnect a user and clean up subscriptions"""
        try:
            if user_id in self.user_connections and websocket in self.user_connections[user_id]:
                subscriptions = self.user_connections[user_id][websocket].copy()
                await self.unsubscribe_from_channels(user_id, websocket, list(subscriptions))
                
                del self.user_connections[user_id][websocket]
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            self.connection_metadata.pop(websocket, None)
            self.last_heartbeat.pop(websocket, None)
            
            logger.info(f"User {user_id} disconnected from multiplexed WebSocket")
            
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")

    async def subscribe_to_channels(self, user_id: int, websocket: WebSocket, channels: List[str]) -> SubscriptionResponse:
        """Subscribe a user's websocket to multiple channels"""
        try:
            if user_id not in self.user_connections or websocket not in self.user_connections[user_id]:
                return SubscriptionResponse(
                    action="subscribe",
                    channels=channels,
                    success=False,
                    message="Connection not found"
                )
            
            # Validate channels (basic validation - can be enhanced)
            valid_channels = []
            for channel in channels:
                if self._is_valid_channel(channel, user_id):
                    valid_channels.append(channel)
                else:
                    logger.warning(f"Invalid channel subscription attempt: {channel} by user {user_id}")
            
            # Add channels to user's subscription set
            self.user_connections[user_id][websocket].update(valid_channels)
            
            # Add to reverse lookup
            for channel in valid_channels:
                if channel not in self.channel_subscribers:
                    self.channel_subscribers[channel] = set()
                self.channel_subscribers[channel].add((user_id, websocket))
            
            # Update activity timestamp
            self._update_activity(websocket)
            
            active_subscriptions = list(self.user_connections[user_id][websocket])
            
            logger.info(f"User {user_id} subscribed to channels: {valid_channels}")
            
            return SubscriptionResponse(
                action="subscribe",
                channels=valid_channels,
                success=True,
                message=f"Subscribed to {len(valid_channels)} channels",
                active_subscriptions=active_subscriptions
            )
            
        except Exception as e:
            logger.error(f"Error subscribing user {user_id} to channels {channels}: {e}")
            return SubscriptionResponse(
                action="subscribe",
                channels=channels,
                success=False,
                message=f"Subscription error: {str(e)}"
            )

    async def unsubscribe_from_channels(self, user_id: int, websocket: WebSocket, channels: List[str]) -> SubscriptionResponse:
        """Unsubscribe a user's websocket from multiple channels"""
        try:
            if user_id not in self.user_connections or websocket not in self.user_connections[user_id]:
                return SubscriptionResponse(
                    action="unsubscribe",
                    channels=channels,
                    success=False,
                    message="Connection not found"
                )
            
            # Remove channels from user's subscription set
            for channel in channels:
                self.user_connections[user_id][websocket].discard(channel)
                
                # Remove from reverse lookup
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard((user_id, websocket))
                    if not self.channel_subscribers[channel]:
                        del self.channel_subscribers[channel]
            
            # Update activity timestamp
            self._update_activity(websocket)
            
            active_subscriptions = list(self.user_connections[user_id][websocket])
            
            logger.info(f"User {user_id} unsubscribed from channels: {channels}")
            
            return SubscriptionResponse(
                action="unsubscribe",
                channels=channels,
                success=True,
                message=f"Unsubscribed from {len(channels)} channels",
                active_subscriptions=active_subscriptions
            )
            
        except Exception as e:
            logger.error(f"Error unsubscribing user {user_id} from channels {channels}: {e}")
            return SubscriptionResponse(
                action="unsubscribe",
                channels=channels,
                success=False,
                message=f"Unsubscription error: {str(e)}"
            )

    async def send_event_to_channels(self, event: BaseEvent):
        """Send an event to all subscribers of its channels"""
        channels = event.get_channels()
        
        for channel in channels:
            await self.send_to_channel(event, channel)

    async def send_to_channel(self, event: BaseEvent, channel_id: str):
        """Send an event to all subscribers of a specific channel"""
        if channel_id not in self.channel_subscribers:
            return
        
        message = EventMessage(
            event_id=event.event_id,
            event_type=event.event_type,
            channel=channel_id,
            source=event.source,
            data=event.data,
            timestamp=event.timestamp
        )
        
        ws_message = WSMessage(
            type=WSMessageType.EVENT,
            data=message.model_dump()
        )
        
        # Send to all subscribers
        disconnected_connections = []
        
        for user_id, websocket in self.channel_subscribers[channel_id].copy():
            try:
                await self._send_to_websocket(websocket, ws_message)
                self._update_activity(websocket)
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                disconnected_connections.append((user_id, websocket))
        
        # Clean up disconnected connections
        for user_id, websocket in disconnected_connections:
            await self._cleanup_connection(user_id, websocket)

    async def send_to_user(self, user_id: int, event: BaseEvent):
        """Send an event to all connections of a specific user"""
        if user_id not in self.user_connections:
            return
        
        message = EventMessage(
            event_id=event.event_id,
            event_type=event.event_type,
            channel=f"user:{user_id}",
            source=event.source,
            data=event.data,
            timestamp=event.timestamp
        )
        
        ws_message = WSMessage(
            type=WSMessageType.EVENT,
            data=message.model_dump()
        )
        
        disconnected_connections = []
        
        for websocket in self.user_connections[user_id].copy():
            try:
                await self._send_to_websocket(websocket, ws_message)
                self._update_activity(websocket)
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                disconnected_connections.append((user_id, websocket))
        
        # Clean up disconnected connections
        for user_id, websocket in disconnected_connections:
            await self._cleanup_connection(user_id, websocket)

    async def broadcast_to_all(self, event: BaseEvent):
        """Broadcast an event to all connected users"""
        message = EventMessage(
            event_id=event.event_id,
            event_type=event.event_type,
            channel="broadcast",
            source=event.source,
            data=event.data,
            timestamp=event.timestamp
        )
        
        ws_message = WSMessage(
            type=WSMessageType.EVENT,
            data=message.model_dump()
        )
        
        disconnected_connections = []
        
        for user_id, websockets in self.user_connections.items():
            for websocket in websockets.copy():
                try:
                    await self._send_to_websocket(websocket, ws_message)
                    self._update_activity(websocket)
                except Exception as e:
                    logger.warning(f"Failed to broadcast to user {user_id}: {e}")
                    disconnected_connections.append((user_id, websocket))
        
        # Clean up disconnected connections
        for user_id, websocket in disconnected_connections:
            await self._cleanup_connection(user_id, websocket)

    async def send_heartbeat_to_all(self):
        """Send heartbeat to all connected clients"""
        heartbeat = HeartbeatMessage(
            timestamp=datetime.now(),
            active_subscriptions=0
        )
        
        ws_message = WSMessage(
            type=WSMessageType.HEARTBEAT,
            data=heartbeat.model_dump()
        )
        
        disconnected_connections = []
        
        for user_id, websockets in self.user_connections.items():
            for websocket, subscriptions in websockets.items():
                try:
                    heartbeat.active_subscriptions = len(subscriptions)
                    ws_message.data = heartbeat.model_dump()
                    await self._send_to_websocket(websocket, ws_message)
                    self.last_heartbeat[websocket] = datetime.now()
                except Exception as e:
                    logger.warning(f"Failed to send heartbeat to user {user_id}: {e}")
                    disconnected_connections.append((user_id, websocket))
        
        # Clean up disconnected connections
        for user_id, websocket in disconnected_connections:
            await self._cleanup_connection(user_id, websocket)

    def get_user_subscriptions(self, user_id: int) -> Dict[str, List[str]]:
        """Get all subscriptions for a user"""
        if user_id not in self.user_connections:
            return {}
        
        all_subscriptions = set()
        for websocket, subscriptions in self.user_connections[user_id].items():
            all_subscriptions.update(subscriptions)
        
        # Group by channel type
        grouped = {}
        for channel in all_subscriptions:
            channel_type = channel.split(':')[0]
            if channel_type not in grouped:
                grouped[channel_type] = []
            grouped[channel_type].append(channel)
        
        return grouped

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_connections = sum(len(websockets) for websockets in self.user_connections.values())
        total_subscriptions = sum(len(subscribers) for subscribers in self.channel_subscribers.values())
        
        return {
            "total_users": len(self.user_connections),
            "total_connections": total_connections,
            "total_channels": len(self.channel_subscribers),
            "total_subscriptions": total_subscriptions,
            "avg_subscriptions_per_connection": total_subscriptions / max(total_connections, 1)
        }

    # Private helper methods
    
    def _is_valid_channel(self, channel: str, user_id: int) -> bool:
        """Validate if a user can subscribe to a channel"""
        # Basic validation - enhance with proper permission checks
        parts = channel.split(':')
        if len(parts) < 2:
            return False
        
        channel_type = parts[0]
        
        # User can always subscribe to their own channels
        if channel_type == "user" and len(parts) >= 2:
            try:
                channel_user_id = int(parts[1])
                return channel_user_id == user_id
            except ValueError:
                return False
        
        # Job channels - validate user has access (simplified for now)
        if channel_type == "job":
            return True  # TODO: Add proper job access validation
        
        # Organization channels - validate user belongs to org (simplified)
        if channel_type == "org":
            return True  # TODO: Add proper organization access validation
        
        # System channels - allow for now (can restrict to admins)
        if channel_type == "system":
            return True
        
        return False

    async def _send_to_websocket(self, websocket: WebSocket, message: WSMessage):
        """Send a message to a specific websocket"""
        await websocket.send_text(message.model_dump_json())

    def _update_activity(self, websocket: WebSocket):
        """Update last activity timestamp for a connection"""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["last_activity"] = datetime.now()

    async def _cleanup_connection(self, user_id: int, websocket: WebSocket):
        """Clean up a disconnected connection"""
        try:
            await self.disconnect_user(user_id, websocket)
        except Exception as e:
            logger.error(f"Error cleaning up connection for user {user_id}: {e}")

    async def _cleanup_stale_connections(self):
        """Periodically clean up stale connections"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                stale_threshold = datetime.now() - timedelta(minutes=10)
                stale_connections = []
                
                for websocket, last_heartbeat in self.last_heartbeat.items():
                    if last_heartbeat < stale_threshold:
                        if websocket in self.connection_metadata:
                            user_id = self.connection_metadata[websocket]["user_id"]
                            stale_connections.append((user_id, websocket))
                
                for user_id, websocket in stale_connections:
                    logger.info(f"Cleaning up stale connection for user {user_id}")
                    await self._cleanup_connection(user_id, websocket)
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def _get_last_activity(self, user_id: int) -> datetime:
        """Get the last activity timestamp for a user"""
        logger.warning(f"Getting last activity for user {user_id} - not implemented. This is a placeholder.")
        return datetime.now() # TODO: Implement this

# Global instance
manager = MultiplexedConnectionManager()