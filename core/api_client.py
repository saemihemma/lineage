"""API client for LINEAGE game - handles network communication"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

from core.api_config import APIConfig

# Setup logging
logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available - API features will be disabled")
    # Create a placeholder type for type checking when httpx is not available
    if TYPE_CHECKING:
        httpx = None  # type: ignore


@dataclass
class LeaderboardEntry:
    """Leaderboard entry from API"""
    id: str
    self_name: str
    soul_level: int
    soul_xp: int
    clones_uploaded: int
    total_expeditions: int
    created_at: str
    updated_at: str


class APIClient:
    """
    HTTP client for LINEAGE API using httpx.
    
    Provides both async and sync methods:
    - Async methods (prefixed with async_) are for web frontend
    - Sync methods are for desktop Tkinter code (which can't await)
    
    NOTE: We maintain both sync and async interfaces because:
    1. Desktop version uses Tkinter (synchronous event loop)
    2. Web version will use async/await for better performance
    3. This dual interface allows both codebases to work without refactoring
    
    When the web frontend is implemented, it should use the async_* methods.
    The sync methods use asyncio.run() internally to bridge to async code.
    """

    def __init__(self):
        self.base_url = APIConfig.get_base_url()
        self.enabled = APIConfig.is_enabled() and HTTPX_AVAILABLE
        self.timeout = APIConfig.get_timeout()
        self.retry_count = APIConfig.get_retry_count()
        self.retry_delay = APIConfig.get_retry_delay()
        self._client: Optional[Any] = None

    async def _get_client(self) -> Optional[Any]:
        """Get or create async HTTP client"""
        if not HTTPX_AVAILABLE or httpx is None:
            return None
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make async HTTP request with retry logic and exponential backoff.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/leaderboard")
            data: Request body data (for POST)
            retry: Whether to retry on failure

        Returns:
            Response JSON as dict, or None on failure
        """
        if not self.enabled:
            logger.debug("API client disabled")
            return None

        url = f"{self.base_url}{endpoint}"
        client = await self._get_client()
        
        if client is None:
            logger.debug("HTTP client not available")
            return None

        for attempt in range(self.retry_count + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(url)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data)
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return None

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.retry_count + 1}): {e}")
                if attempt < self.retry_count and retry:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                return None

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    return None
                # Retry server errors (5xx)
                if attempt < self.retry_count and retry:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                return None

            except httpx.ConnectError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.retry_count + 1}): {e}")
                if attempt < self.retry_count and retry:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                return None

            except Exception as e:
                logger.error(f"Unexpected error during API request: {e}")
                return None

        return None

    # ============================================================================
    # Internal async methods (used by both sync and async wrappers)
    # ============================================================================
    
    async def _is_online_async(self) -> bool:
        """Internal async method for checking API health"""
        if not self.enabled:
            return False

        try:
            response = await self._make_request("GET", "/api/health", retry=False)
            return response is not None and response.get("status") == "healthy"
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def _fetch_leaderboard_async(self, limit: int = 100, offset: int = 0) -> List[LeaderboardEntry]:
        """Internal async method for fetching leaderboard"""
        endpoint = f"/api/leaderboard?limit={limit}&offset={offset}"
        response = await self._make_request("GET", endpoint)

        if response is None:
            return []

        try:
            entries = []
            for entry_data in response:
                entries.append(LeaderboardEntry(**entry_data))
            return entries
        except Exception as e:
            logger.error(f"Error parsing leaderboard response: {e}")
            return []

    async def _submit_to_leaderboard_async(
        self,
        self_name: str,
        soul_level: int,
        soul_xp: int,
        clones_uploaded: int = 0,
        total_expeditions: int = 0
    ) -> bool:
        """Internal async method for submitting to leaderboard"""
        if not self_name or not self_name.strip():
            logger.warning("Cannot submit to leaderboard: empty self_name")
            return False

        submission = {
            "self_name": self_name.strip(),
            "soul_level": soul_level,
            "soul_xp": soul_xp,
            "clones_uploaded": clones_uploaded,
            "total_expeditions": total_expeditions
        }

        response = await self._make_request("POST", "/api/leaderboard/submit", data=submission)
        success = response is not None
        if success:
            logger.info(f"Successfully submitted to leaderboard: {self_name}")
        return success

    async def _upload_telemetry_async(self, events: List[Dict[str, Any]]) -> bool:
        """Internal async method for uploading telemetry"""
        if not events:
            return True  # Nothing to upload

        logger.debug(f"Uploading {len(events)} telemetry events")
        response = await self._make_request("POST", "/api/telemetry", data=events)
        success = response is not None
        if success:
            logger.info(f"Successfully uploaded {len(events)} telemetry events")
        return success
    
    # ============================================================================
    # Synchronous wrapper methods for desktop Tkinter code
    # These methods use asyncio.run() to call the async methods internally.
    # Desktop Tkinter code cannot use async/await, so these wrappers bridge that gap.
    # ============================================================================
    
    def is_online(self) -> bool:
        """
        Check if API is reachable (synchronous wrapper for desktop code).
        
        Returns:
            True if API is online, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            return asyncio.run(self._is_online_async())
        except Exception as e:
            logger.debug(f"Health check failed (sync): {e}")
            return False
    
    def fetch_leaderboard(self, limit: int = 100, offset: int = 0) -> List[LeaderboardEntry]:
        """
        Fetch leaderboard entries (synchronous wrapper for desktop code).
        
        Args:
            limit: Maximum number of entries to fetch
            offset: Offset for pagination
        
        Returns:
            List of LeaderboardEntry objects, empty list on failure
        """
        try:
            return asyncio.run(self._fetch_leaderboard_async(limit, offset))
        except Exception as e:
            logger.error(f"Error fetching leaderboard (sync): {e}")
            return []
    
    def submit_to_leaderboard(
        self,
        self_name: str,
        soul_level: int,
        soul_xp: int,
        clones_uploaded: int = 0,
        total_expeditions: int = 0
    ) -> bool:
        """
        Submit SELF stats to leaderboard (synchronous wrapper for desktop code).
        
        Args:
            self_name: Name of the SELF
            soul_level: Current soul level
            soul_xp: Current soul XP
            clones_uploaded: Number of clones uploaded
            total_expeditions: Total expeditions completed
        
        Returns:
            True if submission successful, False otherwise
        """
        try:
            return asyncio.run(self._submit_to_leaderboard_async(
                self_name, soul_level, soul_xp, clones_uploaded, total_expeditions
            ))
        except Exception as e:
            logger.error(f"Error submitting to leaderboard (sync): {e}")
            return False
    
    def upload_telemetry(self, events: List[Dict[str, Any]]) -> bool:
        """
        Upload telemetry events (synchronous wrapper for desktop code).
        
        Args:
            events: List of telemetry event dictionaries
        
        Returns:
            True if upload successful, False otherwise
        """
        if not events:
            return True  # Nothing to upload
        
        try:
            return asyncio.run(self._upload_telemetry_async(events))
        except Exception as e:
            logger.error(f"Error uploading telemetry (sync): {e}")
            return False
    
    # ============================================================================
    # Async methods for web frontend (use async_ prefix to distinguish)
    # Web frontend should use these methods for better async performance
    # ============================================================================
    
    async def async_is_online(self) -> bool:
        """Async version of is_online for web frontend"""
        return await self._is_online_async()
    
    async def async_fetch_leaderboard(self, limit: int = 100, offset: int = 0) -> List[LeaderboardEntry]:
        """Async version of fetch_leaderboard for web frontend"""
        return await self._fetch_leaderboard_async(limit, offset)
    
    async def async_submit_to_leaderboard(
        self,
        self_name: str,
        soul_level: int,
        soul_xp: int,
        clones_uploaded: int = 0,
        total_expeditions: int = 0
    ) -> bool:
        """Async version of submit_to_leaderboard for web frontend"""
        return await self._submit_to_leaderboard_async(
            self_name, soul_level, soul_xp, clones_uploaded, total_expeditions
        )
    
    async def async_upload_telemetry(self, events: List[Dict[str, Any]]) -> bool:
        """Async version of upload_telemetry for web frontend"""
        return await self._upload_telemetry_async(events)

    def upload_telemetry_background(self, events: List[Dict[str, Any]]):
        """
        Upload telemetry in background (fire-and-forget).
        Creates an asyncio task without blocking the caller.

        Args:
            events: List of telemetry event dictionaries
        """
        if not events:
            return

        async def _upload():
            try:
                await self._upload_telemetry_async(events)
            except Exception as e:
                logger.error(f"Background telemetry upload failed: {e}")

        # Try to create task in existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_upload())
            else:
                # If no loop is running, run in new loop
                asyncio.run(_upload())
        except RuntimeError:
            # No event loop, run in new loop
            asyncio.run(_upload())


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get global API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client
