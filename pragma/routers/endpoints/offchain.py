from fastapi import APIRouter, Depends, HTTPException, Path, Query

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.models.schemas import ErrorResponse

app = APIRouter(
    prefix="/offchain",
    tags=["offchain"],
)


@app.get(
    "/aggregation/candlestick",
    responses={
        200: {"description": "Successfully retrieved candlestick data"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["offchain"],
)
async def get_candlestick_data(
    pair: str = Query("btc/usd", description="Asset pair"),
    interval: str = Query("15min", description="Time interval"),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Retrieve candlestick data for a specific pair.

    Args:
        pair: The asset pair to fetch data for
        interval: The time interval for candlestick data
        client: The API client dependency
    Returns:
        List of candlestick data
    """
    return await client.get_candlestick_data(pair, interval)


@app.get(
    "/data/{pair:path}",
    responses={
        200: {"description": "Successfully retrieved offchain data"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["offchain"],
)
async def get_offchain_data(
    pair: str = Path(..., description="Asset pair, e.g. btc/usd"),
    timestamp: int | None = Query(None, description="Unix timestamp in seconds for historical price data"),
    interval: str | None = Query(
        None,
        description="Time interval for aggregated price data",
        enum=["100ms", "1s", "5s", "10s", "1min", "5min", "15min", "1h", "2h", "1d", "1w"],
    ),
    routing: bool | None = Query(None, description="Enable price routing through intermediate pairs"),
    aggregation: str | None = Query(
        None,
        description="Method used to aggregate prices from multiple sources",
        enum=["median", "twap"],
    ),
    entry_type: str | None = Query(
        None,
        description="Type of market entry to retrieve",
        enum=["spot", "perp", "future"],
    ),
    expiry: str | None = Query(None, description="Expiry date for future contracts in ISO 8601 format"),
    with_components: bool | None = Query(None, description="Include source components in the response"),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Get offchain data for a trading pair.

    Args:
        pair: The asset pair to fetch data for (e.g. btc/usd)
        timestamp: Unix timestamp in seconds for historical price data
        interval: Time interval for aggregated price data
        routing: Enable price routing through intermediate pairs
        aggregation: Price aggregation method
        entry_type: Type of market entry
        expiry: Expiry date for future contracts
        with_components: Include source components in the response
        client: The API client dependency

    Returns:
        Dictionary containing the price data and related information
    """
    # Validate timestamp
    if timestamp and timestamp < 0:
        raise HTTPException(status_code=400, detail="Invalid timestamp")
    # Validate interval
    if interval and interval not in ["100ms", "1s", "5s", "10s", "1min", "5min", "15min", "1h", "2h", "1d", "1w"]:
        raise HTTPException(status_code=400, detail="Invalid interval")
    # Validate routing
    if routing is not None and routing not in [True, False]:
        raise HTTPException(status_code=400, detail="Invalid routing")
    # Validate aggregation
    if aggregation and aggregation not in ["median", "twap"]:
        raise HTTPException(status_code=400, detail="Invalid aggregation")
    # Validate entry type
    if entry_type and entry_type not in ["spot", "perp", "future"]:
        raise HTTPException(status_code=400, detail="Invalid entry type")
    # Validate expiry
    if expiry and expiry not in ["spot", "perp", "future"]:
        raise HTTPException(status_code=400, detail="Invalid expiry")
    # Validate with_components
    if with_components is not None and with_components not in [True, False]:
        raise HTTPException(status_code=400, detail="Invalid with_components")

    try:
        base, quote = pair.split("/")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid pair format. Expected format: base/quote (e.g. btc/usd)",
        ) from e

    data = await client.get_offchain_data(
        base=base,
        quote=quote,
        timestamp=timestamp,
        interval=interval,
        routing=routing,
        aggregation=aggregation,
        entry_type=entry_type,
        expiry=expiry,
        with_components=with_components,
    )

    # Transform the data into the desired format
    if not data or "error" in data:
        return {
            "image": f"/assets/currencies/{base.lower()}.svg",
            "type": "Crypto",
            "ticker": pair.upper(),
            "lastUpdated": "Error fetching data",
            "price": 0,
            "sources": 0,
            "components": [],
            "variations": {
                "past1h": 0,
                "past24h": 0,
                "past7d": 0,
            },
            "chart": "",
            "ema": "N/A",
            "macd": "N/A",
            "error": data.get("error") if data else "Failed to fetch data",
            "isUnsupported": False,
        }

    # Calculate price from hex value
    price = float(int(data["price"], 16)) / (10 ** data["decimals"])

    # Transform components
    components = [
        {
            "publisher": "PRAGMA",  # Default publisher for offchain data
            "source": component["source"],
            "price": component["price"],
            "tx_hash": "0x0",  # No tx hash in offchain data
            "timestamp": component["timestamp"] // 1000,  # Convert ms to seconds
        }
        for component in data["components"]
    ]

    return {
        "image": f"/assets/currencies/{base.lower()}.svg",
        "type": "Crypto",
        "ticker": data["pair_id"],
        "decimals": data["decimals"],
        "lastUpdated": data["timestamp"] // 1000,  # Convert ms to seconds
        "price": price,
        "sources": data["num_sources_aggregated"],
        "components": components,
        "variations": {
            "past1h": 0,  # These would need to be calculated separately
            "past24h": 0,
            "past7d": 0,
        },
        "chart": "",
        "ema": "N/A",
        "macd": "N/A",
        "error": None,
        "isUnsupported": False,
    }
