from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Model for error responses"""

    error: str


class PriceVariations(BaseModel):
    past1h: float = Field(default=0, description="Price variation in the last hour")
    past24h: float = Field(default=0, description="Price variation in the last 24 hours")
    past7d: float = Field(default=0, description="Price variation in the last 7 days")


class AggregatedOnchainResponse(BaseModel):
    image: str = Field(..., description="URL to the currency image")
    type: str = Field(default="Crypto", description="Asset type")
    ticker: str = Field(..., description="Trading pair ticker")
    lastUpdated: str | int = Field(..., description="Last update timestamp or error message")
    price: float = Field(default=0, description="Current price of the asset")
    sources: int = Field(default=0, description="Number of sources aggregated")
    variations: PriceVariations = Field(
        default_factory=PriceVariations, description="Price variations over different time periods"
    )
    chart: str = Field(default="", description="Chart data")
    ema: str = Field(default="N/A", description="Exponential Moving Average")
    macd: str = Field(default="N/A", description="Moving Average Convergence Divergence")
    error: str | None = Field(default=None, description="Error message if any")
    isUnsupported: bool = Field(default=False, description="Flag indicating if the pair is unsupported")
