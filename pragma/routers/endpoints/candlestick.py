from fastapi import APIRouter, Depends, Query

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.models.schemas import ErrorResponse

app = APIRouter(
    prefix="/aggregation",
    tags=["candlestick"],
)


@app.get(
    "/candlestick",
    responses={
        200: {"description": "Successfully retrieved candlestick data"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["candlestick"],
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
