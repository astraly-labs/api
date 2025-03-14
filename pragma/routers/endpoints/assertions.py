from fastapi import APIRouter, Depends, Query

from pragma.client.client import PragmaApiClient
from pragma.client.token import get_api_client
from pragma.models.schemas import ErrorResponse

app = APIRouter(
    prefix="/optimistic",
    tags=["assertions"],
)


@app.get(
    "/assertions/{assertion_id}",
    responses={
        200: {"description": "Successfully retrieved assertion details"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        404: {"model": ErrorResponse, "description": "Assertion not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["assertions"],
)
async def get_assertion_details(assertion_id: str, client: PragmaApiClient = Depends(get_api_client)):
    """Retrieve details for a specific assertion by ID.

    Args:
        assertion_id: The ID of the assertion to retrieve
        client: The API client dependency

    Returns:
        The assertion details
    """
    return await client.get_assertion_details(assertion_id)


@app.get(
    "assertions",
    responses={
        200: {"description": "Successfully retrieved assertions"},
        403: {"model": ErrorResponse, "description": "API key missing or invalid"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["assertions"],
)
async def get_assertions(
    status: str = Query("active", description="Assertion status"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(5, description="Results per page", ge=1, le=100),
    client: PragmaApiClient = Depends(get_api_client),
):
    """Retrieve a paginated list of assertions.

    Args:
        status: The assertion status to filter by
        page: The page number
        limit: The number of results per page
        client: The API client dependency

    Returns:
        Paginated list of assertions
    """
    return await client.get_assertions(status, page, limit)
