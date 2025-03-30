import json
from urllib.parse import unquote, urlencode

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.models.schemas import GetEntryParams
from pragma.models.utils import DEFAULT_ENTRY_PARAMS
from pragma.utils.logging import logger

app = APIRouter(
    prefix="/data/multi",
)


@app.get(
    "/stream",
    responses={
        200: {
            "description": "Server-sent events stream of price entries for multiple pairs",
            "content": {"text/event-stream": {}},
        },
    },
    tags=["Stream"],
)
async def stream_multi_data(
    pairs: list[str] = Query(
        ...,
        description='List of trading pairs to stream prices for (e.g. ["ETH/USD", "BTC/USD"])',
        example=["ETH/USD", "BTC/USD"],
    ),
    interval: str | None = Query(None, description="Interval for updates (e.g. '2s', '1m')", example="2s"),
    aggregation: str | None = Query("median", description="Aggregation method"),
    historical_prices: int | None = Query(
        None,
        description="Number of historical price entries to fetch on initial connection",
        example=10,
    ),
    get_entry_params: str | None = Query(
        None,
        description="Base parameters for entry requests including interval, aggregation mode, and routing options",
    ),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Stream real-time price data for multiple pairs.

    Args:
        pairs: List of trading pairs to stream (required)
        interval: Interval for updates (e.g. '2s', '1m')
        aggregation: Aggregation method
        historical_prices: Number of historical prices to include (optional, default: 100)
        get_entry_params: Base parameters for entry requests as JSON string (optional)
        client: The API client dependency
    """

    async def event_generator():
        try:
            # Use default params if none provided
            if not get_entry_params:
                # Construct entry_params from direct query parameters
                entry_params = DEFAULT_ENTRY_PARAMS.copy()
                if interval is not None:
                    entry_params["interval"] = interval
                if aggregation is not None:
                    entry_params["aggregation"] = aggregation
            else:
                # Parse JSON parameters
                try:
                    decoded_params = unquote(get_entry_params)
                    entry_params = json.loads(decoded_params)
                    entry_params = {**DEFAULT_ENTRY_PARAMS, **entry_params}
                    logger.info(f"Successfully parsed entry params: {entry_params}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid get_entry_params JSON: {e}")
                    error_msg = f"data: {{'error': 'Invalid get_entry_params JSON', 'details': '{str(e)}'}}\n\n"
                    yield error_msg.encode("utf-8")
                    return

            # Validate entry params
            try:
                validated_params = GetEntryParams(**entry_params).model_dump(exclude_none=True)
                logger.info(f"Validated entry params: {validated_params}")
            except Exception as e:
                logger.error(f"Invalid entry parameters: {e}")
                error_msg = f"data: {{'error': 'Invalid entry parameters', 'details': '{str(e)}'}}\n\n"
                yield error_msg.encode("utf-8")
                return

            # Construct query parameters for internal API
            params = {
                "interval": validated_params["interval"],
                "aggregation": validated_params["aggregation"],
            }
            # Only add historical_prices if it's provided
            if historical_prices is not None:
                params["historical_prices"] = str(historical_prices)
            else:
                params["historical_prices"] = 0
            # Transform pairs to the format expected by internal API
            # Each pair should be a separate pairs[] parameter
            for pair in pairs:
                params.setdefault("pairs[]", []).append(pair)

            query_string = urlencode(params, doseq=True)
            url = f"{client.base_url}/data/multi/stream?{query_string}"

            logger.info(f"Fetching data from {url}")

            async with httpx.AsyncClient() as http_client:
                async with http_client.stream("GET", url, headers=client.headers, timeout=None) as response:
                    if not response.is_success:
                        error_text = await response.aread()
                        logger.error(f"API response not OK: {response.status_code} {error_text}")
                        error_msg = f"data: {{'error': 'Failed to fetch data', 'status': {response.status_code}, 'url': '{url}'}}\n\n"
                        yield error_msg.encode("utf-8")
                        return

                    # Forward the stream directly from the internal API
                    async for chunk in response.aiter_bytes():
                        yield chunk

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
            "Content-Type": "text/event-stream",
        },
    )
