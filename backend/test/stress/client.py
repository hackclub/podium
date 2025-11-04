"""HTTP client for stress testing."""

import time
from typing import Dict, Any, Optional, List, Tuple
import httpx

# Handle both relative and absolute imports
try:
    from .config import API_BASE_URL, API_TIMEOUT
except ImportError:
    from config import API_BASE_URL, API_TIMEOUT


class StressTestClient:
    """HTTP client with response time tracking."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[httpx.AsyncClient] = None
        self.response_times: List[Tuple[str, float, int]] = []  # (endpoint, time, status_code)
        self.auth_token: Optional[str] = None
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=API_TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def _log_request(self, endpoint: str, response_time: float, status_code: int):
        """Log request timing."""
        # Clean up endpoint names for better graph readability
        clean_endpoint = self._clean_endpoint_name(endpoint)
        self.response_times.append((clean_endpoint, response_time, status_code))
    
    def _clean_endpoint_name(self, endpoint: str) -> str:
        """Clean endpoint names for better graph readability."""
        # Remove query parameters with tokens
        if "?token=" in endpoint:
            base_endpoint = endpoint.split("?token=")[0]
            return f"{base_endpoint}?token=***"
        
        # Shorten long query parameters
        if "?" in endpoint and len(endpoint) > 50:
            base_endpoint = endpoint.split("?")[0]
            return f"{base_endpoint}?..."
        
        # Replace long record IDs with generic placeholder
        import re
        endpoint = re.sub(r'/rec[A-Za-z0-9]{14,}', '/rec***', endpoint)
        
        return endpoint
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with timing."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get('headers', {})
        
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        kwargs['headers'] = headers
        
        start_time = time.time()
        try:
            response = await self.session.request(method, url, **kwargs)
            response_time = time.time() - start_time
            self._log_request(endpoint, response_time, response.status_code)
            return response
        except Exception as e:
            response_time = time.time() - start_time
            self._log_request(f"{endpoint} (ERROR)", response_time, 0)
            raise e
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._make_request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._make_request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._make_request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._make_request("DELETE", endpoint, **kwargs)
    
    def set_auth_token(self, token: str):
        """Set authentication token for requests."""
        self.auth_token = token
    
    def get_response_times(self) -> List[Tuple[str, float, int]]:
        """Get all logged response times."""
        return self.response_times.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get response time statistics."""
        if not self.response_times:
            return {}
        
        times = [rt[1] for rt in self.response_times]
        status_codes = [rt[2] for rt in self.response_times]
        
        return {
            "total_requests": len(self.response_times),
            "avg_response_time": sum(times) / len(times),
            "min_response_time": min(times),
            "max_response_time": max(times),
            "success_rate": sum(1 for sc in status_codes if 200 <= sc < 300) / len(status_codes),
            "error_count": sum(1 for sc in status_codes if sc >= 400),
        }
