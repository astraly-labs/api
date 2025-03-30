"""Utility functions for the models"""

DEFAULT_PAIRS = ["ETH/USD", "BTC/USD"]

# Default entry parameters matching API.devnet
DEFAULT_ENTRY_PARAMS = {
    "aggregation": "median",
    "entry_type": None,  # Changeable from the frontend
    "interval": None,  # Changeable from the frontend
    "routing": True,
    "timestamp": None,
}
