"""API client for LINEAGE game - handles network communication"""
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.api_config import APIConfig

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


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
    """HTTP client for LINEAGE API"""
    
    def __init__(self):
        self.base_url = APIConfig.get_base_url()
        self.enabled = APIConfig.is_enabled() and REQUESTS_AVAILABLE
        self.timeout = APIConfig.get_timeout()
        self.retry_count = APIConfig.get_retry_count()
        self.retry_delay = APIConfig.get_retry_delay()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/leaderboard")
            data: Request body data (for POST)
            retry: Whether to retry on failure
        
        Returns:
            Response JSON as dict, or None on failure
        """
        if not self.enabled:
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retry_count + 1):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, timeout=self.timeout)
                elif method.upper() == "POST":
                    response = requests.post(
                        url,
                        json=data,
                        timeout=self.timeout
                    )
                else:
                    return None
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_count and retry:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                # Log error but don't raise (graceful degradation)
                print(f"API request failed: {e}")
                return None
        
        return None
    
    def is_online(self) -> bool:
        """
        Check if API is reachable.
        
        Returns:
            True if API is online, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            response = self._make_request("GET", "/api/health", retry=False)
            return response is not None and response.get("status") == "healthy"
        except Exception:
            return False
    
    def fetch_leaderboard(self, limit: int = 100, offset: int = 0) -> List[LeaderboardEntry]:
        """
        Fetch leaderboard entries.
        
        Args:
            limit: Maximum number of entries to fetch
            offset: Offset for pagination
        
        Returns:
            List of LeaderboardEntry objects, empty list on failure
        """
        endpoint = f"/api/leaderboard?limit={limit}&offset={offset}"
        response = self._make_request("GET", endpoint)
        
        if response is None:
            return []
        
        try:
            entries = []
            for entry_data in response:
                entries.append(LeaderboardEntry(**entry_data))
            return entries
        except Exception as e:
            print(f"Error parsing leaderboard response: {e}")
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
        Submit SELF stats to leaderboard.
        
        Args:
            self_name: Name of the SELF
            soul_level: Current soul level
            soul_xp: Current soul XP
            clones_uploaded: Number of clones uploaded
            total_expeditions: Total expeditions completed
        
        Returns:
            True if submission successful, False otherwise
        """
        if not self_name or not self_name.strip():
            return False
        
        submission = {
            "self_name": self_name.strip(),
            "soul_level": soul_level,
            "soul_xp": soul_xp,
            "clones_uploaded": clones_uploaded,
            "total_expeditions": total_expeditions
        }
        
        response = self._make_request("POST", "/api/leaderboard/submit", data=submission)
        return response is not None
    
    def upload_telemetry(self, events: List[Dict[str, Any]]) -> bool:
        """
        Upload telemetry events.
        
        Args:
            events: List of telemetry event dictionaries
        
        Returns:
            True if upload successful, False otherwise
        """
        if not events:
            return True  # Nothing to upload
        
        response = self._make_request("POST", "/api/telemetry", data=events)
        return response is not None


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get global API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client

