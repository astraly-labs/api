from fastapi import APIRouter, Depends

from pragma.client.crawler import PragmaCrawlerClient
from pragma.client.token import get_crawler_client
from pragma.models.schemas import ErrorResponse

app = APIRouter(
    prefix="/tokens",
    tags=["tokens"],
)


@app.get(
    "/all",
    responses={
        200: {"description": "Successfully retrieved all tokens"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["tokens"],
)
async def get_all_tokens(
    client: PragmaCrawlerClient = Depends(get_crawler_client),
):
    return await client.get_all_tokens()
