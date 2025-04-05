import json
import os

import websocket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def on_message(ws, message):
    print(f"Received: {message}")


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("Connection closed")


def on_open(ws):
    print("Connected to WebSocket endpoint")
    # Subscribe to specific pairs
    subscribe_message = {"msg_type": "subscribe", "pairs": ["BTC/USD", "ETH/USD:MARK"]}
    print(f"Sending subscription: {subscribe_message}")
    ws.send(json.dumps(subscribe_message))


# Get API key from environment
api_key = os.getenv("PRAGMA_API_KEY")
if not api_key:
    raise ValueError("PRAGMA_API_KEY environment variable is not set")

# Connect to our WebSocket endpoint
ws = websocket.WebSocketApp(
    "ws://localhost:8007/node/v1/data/price/subscribe",
    header={"Authorization": f"Bearer {api_key}"},
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open,
)

# Run the WebSocket client
ws.run_forever()
