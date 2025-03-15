import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PragmaCrawlerClient:
    """Client for interacting with Pragma Crawler API endpoints."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def _make_request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a request to the Pragma Crawler API.

        Args:
            path: The API endpoint path
            params: Optional query parameters
        """
        url = f"{self.base_url}/{path}"
        logger.info(f"Making request to {url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise e
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            raise e

    async def get_all_tokens(self) -> Any:
        """Fetch all tokens from the Pragma Crawler API.

        Returns:
            The JSON response containing all tokens information.
        """
        return await self._make_request("tokens/all")
