from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pragma.routers.endpoints.onchain import app

# Create test client
test_app = FastAPI()
test_app.include_router(app)
client = TestClient(test_app)

# Mock successful response data
MOCK_SUCCESSFUL_RESPONSE = {
    "pair_id": "BTC/USD",
    "last_updated_timestamp": 1742586307,
    "price": "0x7a1daae86ff",
    "decimals": 8,
    "nb_sources_aggregated": 9,
    "asset_type": "Crypto",
    "components": [
        {
            "publisher": "PRAGMA",
            "source": "KUCOIN",
            "price": "0x7a1daae86ff",
            "tx_hash": "0x00dba5c4bcc7b5581732936ae20eab35a99a262cc3fdb4cc512665b52de2a298",
            "timestamp": 1742585806,
        }
    ],
    "variations": {"1h": 0.0024294928, "1d": 0.02291528, "1w": -0.05567832},
}

# Expected formatted response
EXPECTED_SUCCESSFUL_RESPONSE = {
    "image": "/assets/currencies/btc.svg",
    "type": "Crypto",
    "ticker": "BTC/USD",
    "lastUpdated": 1742586307,
    "price": 32481.23,  # Converted from hex
    "sources": 9,
    "variations": {"past1h": 0.0024294928, "past24h": 0.02291528, "past7d": -0.05567832},
    "chart": "",
    "ema": "N/A",
    "macd": "N/A",
    "error": None,
    "isUnsupported": False,
}


@pytest.mark.asyncio
async def test_get_aggregated_onchain_data_success():
    """Test successful response from get_aggregated_onchain_data endpoint"""
    # Mock the client response
    mock_client = AsyncMock()
    mock_client.get_onchain_data_aggregated.return_value = MOCK_SUCCESSFUL_RESPONSE

    with patch("pragma.client.token.get_api_client", return_value=mock_client):
        response = client.get("/onchain/btc/usd?network=mainnet&aggregation=median")

        assert response.status_code == 200
        assert response.json() == EXPECTED_SUCCESSFUL_RESPONSE
        mock_client.get_onchain_data_aggregated.assert_called_once_with("BTC/USD", "mainnet", "median")


@pytest.mark.asyncio
async def test_get_aggregated_onchain_data_error():
    """Test error response from get_aggregated_onchain_data endpoint"""
    # Mock the client to return an error
    mock_client = AsyncMock()
    mock_client.get_onchain_data_aggregated.return_value = {"error": "API Error"}

    with patch("pragma.client.token.get_api_client", return_value=mock_client):
        response = client.get("/onchain/btc/usd?network=mainnet&aggregation=median")

        assert response.status_code == 200
        assert response.json() == {
            "image": "/assets/currencies/btc.svg",
            "type": "Crypto",
            "ticker": "BTC/USD",
            "lastUpdated": "Error fetching data",
            "price": 0,
            "sources": 0,
            "variations": {
                "past1h": 0,
                "past24h": 0,
                "past7d": 0,
            },
            "chart": "",
            "ema": "N/A",
            "macd": "N/A",
            "error": "API Error",
            "isUnsupported": False,
        }


@pytest.mark.asyncio
async def test_get_aggregated_onchain_data_exception():
    """Test exception handling in get_aggregated_onchain_data endpoint"""
    # Mock the client to raise an exception
    mock_client = AsyncMock()
    mock_client.get_onchain_data_aggregated.side_effect = Exception("Test error")

    with patch("pragma.client.token.get_api_client", return_value=mock_client):
        response = client.get("/onchain/btc/usd?network=mainnet&aggregation=median")

        assert response.status_code == 200
        assert response.json() == {
            "image": "/assets/currencies/btc.svg",
            "type": "Crypto",
            "ticker": "BTC/USD",
            "lastUpdated": "Error fetching data",
            "price": 0,
            "sources": 0,
            "variations": {
                "past1h": 0,
                "past24h": 0,
                "past7d": 0,
            },
            "chart": "",
            "ema": "N/A",
            "macd": "N/A",
            "error": "Test error",
            "isUnsupported": False,
        }


@pytest.mark.asyncio
async def test_get_aggregated_onchain_data_invalid_pair():
    """Test handling of invalid trading pair format"""
    mock_client = AsyncMock()

    with patch("pragma.client.token.get_api_client", return_value=mock_client):
        response = client.get("/onchain/invalid-pair?network=mainnet&aggregation=median")

        assert response.status_code == 200
        data = response.json()
        assert data["error"] == "Failed to fetch data"
        assert data["ticker"] == "INVALID-PAIR"


@pytest.mark.asyncio
async def test_get_aggregated_onchain_data_default_params():
    """Test endpoint with default parameters"""
    mock_client = AsyncMock()
    mock_client.get_onchain_data_aggregated.return_value = MOCK_SUCCESSFUL_RESPONSE

    with patch("pragma.client.token.get_api_client", return_value=mock_client):
        response = client.get("/onchain/btc/usd")

        assert response.status_code == 200
        mock_client.get_onchain_data_aggregated.assert_called_once_with("BTC/USD", "mainnet", "median")
