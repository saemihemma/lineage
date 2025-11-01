"""API configuration for LINEAGE game client"""
import os
from typing import Optional


class APIConfig:
    """API configuration settings"""
    
    # Base URL for API (from environment or default)
    BASE_URL: str = os.getenv("LINEAGE_API_URL", "http://localhost:8000")
    
    # Feature flag - enable/disable API functionality
    ENABLED: bool = os.getenv("LINEAGE_API_ENABLED", "true").lower() == "true"
    
    # Timeout for API requests (seconds)
    TIMEOUT: float = float(os.getenv("LINEAGE_API_TIMEOUT", "5.0"))
    
    # Maximum number of retries for failed requests
    RETRY_COUNT: int = int(os.getenv("LINEAGE_API_RETRY_COUNT", "3"))
    
    # Retry delay (seconds) - exponential backoff starting from this
    RETRY_DELAY: float = float(os.getenv("LINEAGE_API_RETRY_DELAY", "1.0"))
    
    @classmethod
    def get_base_url(cls) -> str:
        """Get base API URL"""
        return cls.BASE_URL.rstrip("/")
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if API is enabled"""
        return cls.ENABLED
    
    @classmethod
    def get_timeout(cls) -> float:
        """Get request timeout"""
        return cls.TIMEOUT
    
    @classmethod
    def get_retry_count(cls) -> int:
        """Get max retry count"""
        return cls.RETRY_COUNT
    
    @classmethod
    def get_retry_delay(cls) -> float:
        """Get initial retry delay"""
        return cls.RETRY_DELAY

