import pytest
from fastapi.testclient import TestClient

from pragma.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def mock_api_response():
    return {
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
