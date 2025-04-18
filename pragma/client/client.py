import logging
from typing import Any

import httpx
from fastapi import HTTPException

# Set up logging
logger = logging.getLogger(__name__)


class PragmaApiClient:
    """Client for interacting with Pragma API endpoints."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the Pragma API client.

        Args:
            base_url: The base URL for the Pragma API
            api_key: The API key to use for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"x-api-key": api_key}

    async def _make_request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a request to the Pragma API.

        Args:
            path: The API endpoint path
            params: Optional query parameters

        Returns:
            The JSON response from the API

        Raises:
            HTTPException: If the request fails
        """
        url = f"{self.base_url}/{path}"
        logger.info(f"Making request to {url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

                try:
                    error_data = response.json() if response.headers.get("content-type") == "application/json" else None
                except ValueError:
                    error_data = None

                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as e:
                        logger.error(f"Failed to parse JSON response: {response.text}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Invalid JSON response from API: {response.text[:200]}",
                        ) from e

                # Handle specific error cases
                if error_data and "message" in error_data:
                    if "No checkpoints found" in error_data["message"]:
                        return []
                    # Return the actual error message from the API
                    raise HTTPException(status_code=response.status_code, detail=error_data["message"])

                # Handle other errors
                detail = (
                    f"External API error: {error_data.get('error', 'Unknown error')}"
                    if error_data
                    else f"Failed to fetch data from external API: {response.text[:200]}"
                )
                raise HTTPException(status_code=response.status_code, detail=detail)

        except httpx.RequestError as exc:
            logger.error(f"Request error for {url}: {exc}")
            raise HTTPException(
                status_code=500,
                detail=f"Error connecting to external API ({url}): {str(exc)}",
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}") from exc

    async def get_assertion_details(self, assertion_id: str) -> dict[str, Any]:
        """Get details for a specific assertion."""
        return await self._make_request(f"optimistic/assertions/{assertion_id}")

    async def get_assertions(self, status: str = "active", page: int = 1, limit: int = 5) -> dict[str, Any]:
        """Get paginated list of assertions."""
        params = {"status": status, "page": str(page), "limit": str(limit)}
        return await self._make_request("optimistic/assertions", params)

    async def get_checkpoints(self, pair: str, network: str = "starknet-sepolia") -> list[dict[str, Any]]:
        """Get checkpoint data for a specific pair and network."""
        params = {"network": network}
        return await self._make_request(f"onchain/checkpoints/{pair}", params)

    async def get_onchain_data(
        self,
        pair: str,
        network: str = "starknet-mainnet",
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get on-chain data for a specific pair and network."""
        params = {"network": network}
        if start_timestamp is not None and end_timestamp is not None:
            params["timestamp"] = f"{start_timestamp},{end_timestamp}"

        try:
            return await self._make_request(f"onchain/history/{pair}", params)
        except HTTPException as e:
            logger.error(f"Error fetching onchain data for {pair}: {str(e)}")
            raise

    async def get_onchain_data_aggregated(
        self, pair: str, network: str = "starknet-mainnet", aggregation: str = "median"
    ) -> list[dict[str, Any]]:
        """Get on-chain data for a specific pair and network."""
        # Separate the base and quote from the pair
        base, quote = pair.split("/")
        params = {"network": network, "aggregation": aggregation}
        return await self._make_request(f"onchain/{base}/{quote}", params)

    async def get_candlestick_data(self, pair: str, interval: str = "15min") -> list[dict[str, Any]]:
        """Get candlestick data for a specific pair."""
        params = {"interval": interval}
        return await self._make_request(f"aggregation/candlestick/{pair}", params)

    async def get_publishers(self, network: str = "starknet-sepolia", data_type: str = "spot_entry") -> list[dict[str, Any]]:
        """Get publishers for a specific network and data type."""
        params = {"network": network, "data_type": data_type}
        return await self._make_request("onchain/publishers", params)

    async def fetch_multiple_assets(
        self, assets: list[dict[str, str]], source_network: str = "starknet-mainnet"
    ) -> dict[str, Any]:
        """Fetch data for multiple assets in parallel.

        Args:
            assets: List of asset objects with ticker property
            source_network: The network to fetch data from

        Returns:
            Combined data response
        """
        import asyncio

        # Define the fetch tasks
        asset_tasks = [self.get_onchain_data(asset["ticker"], source_network) for asset in assets]

        checkpoint_tasks = [self.get_checkpoints(asset["ticker"], source_network) for asset in assets]

        publishers_task = self.get_publishers(source_network)

        # Execute all tasks in parallel
        asset_results, checkpoint_results, publishers_data = await asyncio.gather(
            asyncio.gather(*asset_tasks),
            asyncio.gather(*checkpoint_tasks),
            publishers_task,
        )

        # Structure the results
        results = {asset["ticker"]: data for asset, data in zip(assets, asset_results)}
        checkpoints_data = {asset["ticker"]: data for asset, data in zip(assets, checkpoint_results)}

        return {
            "results": results,
            "publishersData": publishers_data,
            "checkpointsData": checkpoints_data,
        }

    async def get_entry(
        self,
        base: str,
        quote: str,
        timestamp: int | None = None,
        interval: str | None = None,
        routing: bool | None = None,
        aggregation: str | None = None,
        entry_type: str | None = None,
        expiry: str | None = None,
    ) -> dict[str, Any]:
        """Get price entry for a trading pair."""
        params = {
            "timestamp": timestamp,
            "interval": interval,
            "routing": routing,
            "aggregation": aggregation,
            "entry_type": entry_type,
            "expiry": expiry,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return await self._make_request(f"data/{base}/{quote}", params)

    async def get_ohlc(
        self,
        base: str,
        quote: str,
        interval: str | None = None,
        timestamp: int | None = None,
        routing: bool | None = None,
        aggregation: str | None = None,
    ) -> dict[str, Any]:
        """Get OHLC (candlestick) data for a trading pair."""
        params = {
            "interval": interval,
            "timestamp": timestamp,
            "routing": routing,
            "aggregation": aggregation,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._make_request(f"aggregation/candlestick/{base}/{quote}", params)

    async def get_offchain_data(
        self,
        base: str,
        quote: str,
        timestamp: int | None = None,
        interval: str | None = None,
        aggregation: str | None = None,
        routing: bool | None = None,
        entry_type: str | None = None,
        expiry: str | None = None,
        with_components: bool | None = None,
    ) -> dict[str, Any]:
        """Get offchain data for a trading pair.

        Args:
            base: Base asset symbol (e.g. BTC)
            quote: Quote asset symbol (e.g. USD)
            timestamp: Unix timestamp in seconds for historical price data
            interval: Time interval for aggregated price data (e.g. "1min", "1h", "1d")
            aggregation: Price aggregation method ("median", "twap")
            routing: Enable price routing through intermediate pairs
            entry_type: Type of market entry ("spot", "perp", "future")
            expiry: Expiry date for future contracts in ISO 8601 format
            with_components: Include source components in the response

        Returns:
            Dictionary containing the price data and related information
        """
        params = {
            "timestamp": timestamp,
            "interval": interval,
            "routing": routing,
            "aggregation": aggregation,
            "entry_type": entry_type,
            "expiry": expiry,
            "with_components": with_components,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return await self._make_request(f"data/{base}/{quote}", params)
