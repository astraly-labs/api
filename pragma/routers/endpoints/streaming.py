import asyncio
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.models.schemas import ErrorResponse
from pragma.utils.logging import logger

app = APIRouter(
    prefix="/multi",
    tags=["streaming"],
)


@app.get(
    "/stream",
    responses={
        200: {"description": "Successfully streaming price data"},
        400: {"description": "Invalid request parameters"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["streaming"],
)
async def stream_multi_data(
    pairs: list[str] = Query(..., description="Asset pairs to stream"),
    interval: str = Query("1s", description="Time interval"),
    aggregation: str = Query("median", description="Aggregation method"),
    historical_prices: str = Query("10", description="Number of historical prices"),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Stream real-time price data for multiple pairs.

    Args:
        pairs: List of asset pairs to stream
        interval: Time interval for updates
        aggregation: Aggregation method
        historical_prices: Number of historical prices to include
        client: The API client dependency
    """

    async def event_generator():
        # Clean pairs (remove /USD suffix if present)
        clean_pairs = [pair.split("/")[0] for pair in pairs]

        # Construct query parameters
        params = {
            "interval": interval,
            "aggregation": aggregation,
            "historical_prices": historical_prices,
        }
        for pair in clean_pairs:
            params.setdefault("pairs[]", []).append(f"{pair}/USD")

        query_string = urlencode(params, doseq=True)
        url = f"{client.base_url}/data/multi/stream?{query_string}"

        logger.info(f"Fetching data from {url}")

        try:
            async with httpx.AsyncClient() as http_client:
                async with http_client.stream("GET", url, headers=client.headers, timeout=None) as response:
                    if not response.is_success:
                        error_text = await response.aread()
                        logger.error(f"API response not OK: {response.status_code} {error_text}")
                        error_msg = f"data: {{'error': 'Failed to fetch data', 'status': {response.status_code}}}\n\n"
                        yield error_msg.encode("utf-8")
                        return

                    # Send initial connection message
                    yield f"data: {{'connected': true, 'timestamp': {int(asyncio.get_event_loop().time() * 1000)}}}\n\n".encode()

                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk.decode("utf-8")
                        messages = buffer.split("\n\n")
                        buffer = messages.pop()  # Keep incomplete message in buffer

                        for message in messages:
                            if message.strip():
                                yield f"{message}\n\n".encode()

        except Exception as e:
            logger.error(f"Error in stream: {str(e)}")
            error_msg = f"data: {{'error': 'Stream error', 'details': '{str(e)}'}}\n\n"
            yield error_msg.encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )
