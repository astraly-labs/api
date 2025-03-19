from datetime import UTC
from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.models.schemas import ErrorResponse

app = APIRouter(
    prefix="/onchain",
    tags=["onchain"],
)


@app.get(
    "/checkpoints/{base}/{quote}",
    responses={
        200: {"description": "Successfully retrieved checkpoint data"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["onchain"],
)
async def get_checkpoints(
    base: str,
    quote: str,
    network: str = Query("mainnet", description="Network name"),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Retrieve checkpoint data for a specific pair and network.

    Args:
        base: The base asset
        quote: The quote asset
        network: The network to fetch data from
        aggregation: The aggregation method to use
        client: The API client dependency
    Returns:
        List of checkpoint data
    """
    pair = f"{base}/{quote}"
    return await client.get_checkpoints(pair, network)


@app.get(
    "/history/{base}/{quote}",
    responses={
        200: {"description": "Successfully retrieved on-chain data"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        404: {"model": ErrorResponse, "description": "Entry not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["onchain"],
)
async def get_onchain_data(
    base: str,
    quote: str,
    network: str = Query("mainnet", description="Network name"),
    timestamp: str | None = Query(None, description="Timestamp range in seconds (format: start,end)"),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Retrieve on-chain data for a specific pair and network.

    Args:
        base: The base asset
        quote: The quote asset
        network: The network to fetch data from
        timestamp: Optional timestamp range in seconds (format: start,end)
        client: The API client dependency
    Returns:
        List of on-chain data
    """
    pair = f"{base}/{quote}".upper()

    # Parse timestamp range if provided
    start_ts = None
    end_ts = None
    if timestamp:
        try:
            start_ts, end_ts = timestamp.split(",")
            # Ensure they are valid integers
            start_ts = int(start_ts.strip())
            end_ts = int(end_ts.strip())
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid timestamp format. Expected format: start,end (e.g., 1234567,7654321)",
            ) from e

    try:
        return await client.get_onchain_data(pair, network, start_ts, end_ts)
    except HTTPException as e:
        if e.status_code == 404:
            return {
                "happened_at": dt.now(UTC).isoformat(),
                "message": f"Entry not found: {pair}",
                "resource": "EntryModel",
            }
        raise HTTPException(status_code=e.status_code, detail=str(e.detail)) from e


@app.get(
    "/publishers",
    responses={
        200: {"description": "Successfully retrieved publishers data"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["onchain"],
)
async def get_publishers(
    network: str = Query("sepolia", description="Network name"),
    data_type: str = Query(
        "spot_entry",
        description="Data type",
    ),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Retrieve publishers for a specific network and data type."""
    publishers = await client.get_publishers(network, data_type)

    formatted_publishers = []
    for publisher in publishers:
        formatted_publisher = {
            "image": f"/assets/publishers/{publisher['publisher'].lower()}.svg",
            "type": publisher.get("type", ""),
            "link": publisher.get("website_url", ""),
            "name": publisher["publisher"],
            "lastUpdated": publisher.get("last_updated_timestamp", 0),  # Just the raw timestamp
            "reputationScore": "soon",
            "nbFeeds": publisher.get("nb_feeds", 0),
            "dailyUpdates": publisher.get("daily_updates", 0),
            "totalUpdates": publisher.get("total_updates", 0),
        }
        formatted_publishers.append(formatted_publisher)

    return formatted_publishers
