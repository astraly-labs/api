from functools import lru_cache  # noqa: D100

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_key: str = Field(..., description="Pragma API key")
    api_base_url: str = Field(..., description="Pragma API base URL")
    crawler_api_base_url: str = Field(..., description="Pragma Crawler API base URL")
    websocket_url: str = Field(..., description="Pragma WebSocket URL")
    otel_service_name: str = Field("pragma-api", description="Service name for OpenTelemetry")
    otel_exporter_otlp_endpoint: str | None = Field(None, description="OpenTelemetry collector endpoint")
    environment: str = Field("development", description="Environment")

    # CORS Settings
    cors_origins: list[str] = ["*"]
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    data_sources: dict[str, str] = {}

    initial_assets: list[dict[str, str]] = [
        {
            "ticker": "btc/usd",
            "name": "Bitcoin",
            "icon": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png?1747033579",
        },
        {
            "ticker": "eth/usd",
            "name": "Ethereum",
            "icon": "https://assets.coingecko.com/coins/images/279/large/ethereum.png?1746016443",
        },
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set data_sources after base_url is initialized
        self.data_sources = {
            "mainnet": f"{self.api_base_url}/onchain",
            "sepolia": f"{self.api_base_url}/onchain",
            "checkpointsMainnet": f"{self.api_base_url}/onchain/checkpoints",
            "checkpointsSepolia": f"{self.api_base_url}/onchain/checkpoints",
            "publishersMainnet": f"{self.api_base_url}/onchain/publishers?network=starknet-mainnet&data_type=spot_entry",
            "publishersSepolia": f"{self.api_base_url}/onchain/publishers?network=starknet-sepolia&data_type=spot_entry",
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "PRAGMA_"


@lru_cache
def get_settings():
    """Get cached settings to avoid reloading from environment each time."""
    return Settings()
