"""Mock creation helpers for tests."""
from unittest.mock import AsyncMock, MagicMock
from typing import Any, Dict
import redis.asyncio as redis


class MockRedisClient:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
        self.sets = {}
        self.lists = {}
    
    async def get(self, key: str):
        return self.data.get(key)
    
    async def set(self, key: str, value: Any, ex: int = None):
        self.data[key] = value
        return True
    
    async def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)
        return len(keys)
    
    async def exists(self, key: str):
        return key in self.data
    
    async def flushdb(self):
        self.data.clear()
        self.sets.clear()
        self.lists.clear()
    
    async def close(self):
        pass
    
    async def ping(self):
        return True


class MockArqPool:
    """Mock ARQ pool for testing background jobs."""
    
    def __init__(self):
        self.enqueued_jobs = []
    
    async def enqueue_job(self, function: str, *args, **kwargs):
        job_data = {
            "function": function,
            "args": args,
            "kwargs": kwargs
        }
        self.enqueued_jobs.append(job_data)
        return MagicMock(job_id="test-job-id")
    
    async def aclose(self):
        pass


def create_mock_external_api():
    """Create mock for external API calls."""
    mock = AsyncMock()
    mock.return_value = {
        "status": "success",
        "data": "mocked_response"
    }
    return mock


def create_mock_websocket():
    """Create mock WebSocket for testing."""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_text = AsyncMock()
    mock_ws.receive_json = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws