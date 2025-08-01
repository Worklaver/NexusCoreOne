import os
import aiohttp
import logging
from typing import Dict, Any, Optional
import json

# Configure logging
logger = logging.getLogger(__name__)

# API base URL
API_BASE_URL = os.getenv("API_URL", "http://api:8000")

class APIClient:
    """Client for interacting with the API"""
    
    def __init__(self):
        self.session = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        """
        Send GET request to API
        
        Args:
            endpoint: API endpoint (starting with /)
            params: Query parameters
            
        Returns:
            Response object
        """
        await self._ensure_session()
        url = f"{API_BASE_URL}{endpoint}"
        try:
            return await self.session.get(url, params=params)
        except Exception as e:
            logger.error(f"Error in GET request to {url}: {e}")
            raise
    
    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None):
        """
        Send POST request to API
        
        Args:
            endpoint: API endpoint (starting with /)
            json: Request body
            
        Returns:
            Response object
        """
        await self._ensure_session()
        url = f"{API_BASE_URL}{endpoint}"
        try:
            return await self.session.post(url, json=json)
        except Exception as e:
            logger.error(f"Error in POST request to {url}: {e}")
            raise
    
    async def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None):
        """
        Send PUT request to API
        
        Args:
            endpoint: API endpoint (starting with /)
            json: Request body
            
        Returns:
            Response object
        """
        await self._ensure_session()
        url = f"{API_BASE_URL}{endpoint}"
        try:
            return await self.session.put(url, json=json)
        except Exception as e:
            logger.error(f"Error in PUT request to {url}: {e}")
            raise
    
    async def delete(self, endpoint: str):
        """
        Send DELETE request to API
        
        Args:
            endpoint: API endpoint (starting with /)
            
        Returns:
            Response object
        """
        await self._ensure_session()
        url = f"{API_BASE_URL}{endpoint}"
        try:
            return await self.session.delete(url)
        except Exception as e:
            logger.error(f"Error in DELETE request to {url}: {e}")
            raise

# Create singleton instance
api_client = APIClient()