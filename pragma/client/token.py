from fastapi import Depends, HTTPException, Request, status

from pragma.client.client import PragmaApiClient
from pragma.client.crawler import PragmaCrawlerClient
from pragma.config import Settings, get_settings

# Load settings
settings = get_settings()


# API Key validation dependency
async def verify_api_key(request: Request, settings: Settings = Depends(get_settings)):
    """Verify that the API key is present in the request headers.
    If not in headers, fall back to the environment variable.
    """
    if api_key := request.headers.get("x-api-key", settings.api_key):
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is required either in headers or environment variables",
        )


# API client dependency
async def get_api_client(
    api_key: str = Depends(verify_api_key), settings: Settings = Depends(get_settings)
) -> PragmaApiClient:
    """Create an API client with the given API key."""
    return PragmaApiClient(settings.pragma_api_base_url, api_key)


# Crawler client dependency
async def get_crawler_client(settings: Settings = Depends(get_settings)) -> PragmaCrawlerClient:
    """Create a crawler client with the given settings."""
    return PragmaCrawlerClient(settings.pragma_crawler_api_base_url)
