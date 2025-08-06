"""
Async client for topn-db FastAPI service.
"""

from typing import Optional

import httpx

from core.config import settings

from .topn_db_client import TopnDbClient

_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    """Get the global async client instance."""
    global _client
    if _client is None:
        base_url = settings.TOPN_DB_BASE_URL
        _client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )
    return _client


async def close_client():
    """Close the global async client."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


topn_db_client = TopnDbClient(base_url=settings.TOPN_DB_BASE_URL, client=get_client())
