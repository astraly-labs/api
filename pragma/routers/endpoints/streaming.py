import asyncio
import json
from urllib.parse import unquote, urlencode

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.utils.logging import logger

app = APIRouter(
    prefix="/data/multi",
)


class GetEntryParams(BaseModel):
    """Parameters for entry requests."""

    aggregation: str | None = None
    entry_type: str | None = None
    interval: str | None = None
    routing: bool = True
    timestamp: int | None = None


DEFAULT_PAIRS = ["ETH/USD", "BTC/USD"]

# Default entry parameters matching API.devnet
DEFAULT_ENTRY_PARAMS = {
    "aggregation": "median",
    "entry_type": None,  # Changeable from the frontend
    "interval": None,  # Changeable from the frontend
    "routing": True,
    "timestamp": None,
}


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
        ge=0,
        example=100,
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
                    # First URL decode the entire string
                    decoded_params = unquote(get_entry_params)
                    # Then parse as JSON
                    entry_params = json.loads(decoded_params)
                    # Merge with defaults to ensure all required fields are present
                    entry_params = {**DEFAULT_ENTRY_PARAMS, **entry_params}
                    logger.info(f"Successfully parsed entry params: {entry_params}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid get_entry_params JSON: {e}")
                    logger.error(f"Raw get_entry_params: {get_entry_params}")
                    logger.error(f"Decoded params: {decoded_params}")
                    error_msg = f"data: {{'error': 'Invalid get_entry_params JSON', 'details': '{str(e)}'}}\n\n"
                    yield error_msg.encode("utf-8")
                    return
                except Exception as e:
                    logger.error(f"Error processing get_entry_params: {e}")
                    error_msg = f"data: {{'error': 'Error processing parameters', 'details': '{str(e)}'}}\n\n"
                    yield error_msg.encode("utf-8")
                    return

            # Validate entry params using Pydantic model
            try:
                validated_params = GetEntryParams(**entry_params).model_dump(exclude_none=True)
                logger.info(f"Validated entry params: {validated_params}")
            except Exception as e:
                logger.error(f"Invalid entry parameters: {e}")
                error_msg = f"data: {{'error': 'Invalid entry parameters', 'details': '{str(e)}'}}\n\n"
                yield error_msg.encode("utf-8")
                return

            # Construct query parameters with only essential parameters
            params = {
                "interval": validated_params["interval"],
                "aggregation": validated_params["aggregation"],
                "historical_prices": str(historical_prices or 10),
            }
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

                    # Send initial connection message
                    yield f"data: {{'connected': true, 'timestamp': {int(asyncio.get_event_loop().time() * 1000)}}}\n\n".encode()

                    # Process the event stream
                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        try:
                            chunk_text = chunk.decode("utf-8")
                            buffer += chunk_text

                            # Split on double newlines to separate events
                            while "\n\n" in buffer:
                                event, buffer = buffer.split("\n\n", 1)

                                if event.startswith("data: "):
                                    try:
                                        # Strip 'data: ' prefix if present
                                        event_data = event.strip()
                                        if event_data.startswith("data: "):
                                            event_data = event_data[6:]  # Remove 'data: ' prefix
                                        parsed_data = json.loads(event_data)

                                        # Transform the data to match frontend expectations
                                        if isinstance(parsed_data, list):
                                            # Handle array of price updates
                                            transformed_data = []
                                            for update in parsed_data:
                                                if isinstance(update, dict) and "pair_id" in update:
                                                    transformed_update = {
                                                        "pair_id": update["pair_id"],
                                                        "price": update.get("price", "0x0"),
                                                        "timestamp": update.get(
                                                            "timestamp", int(asyncio.get_event_loop().time() * 1000)
                                                        ),
                                                        "decimals": update.get("decimals", 8),
                                                        "num_sources_aggregated": update.get(
                                                            "num_sources_aggregated", 1
                                                        ),
                                                        "variations": {"1h": 0, "1d": 0, "1w": 0},
                                                    }
                                                    transformed_data.append(transformed_update)

                                            if transformed_data:
                                                yield f"data: {json.dumps(transformed_data)}\n\n".encode()
                                        else:
                                            # Pass through non-array data (like connection messages)
                                            yield f"data: {json.dumps(parsed_data)}\n\n".encode()

                                    except json.JSONDecodeError as e:
                                        logger.error(f"Error parsing JSON from event: {e}")
                                        logger.error(f"JSON content: {event[:100]}...")  # For debugging
                                        continue
                                else:
                                    # Pass through non-data events (like comments)
                                    yield f"{event}\n\n".encode()
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            continue

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
