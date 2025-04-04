import json

import websocket


def on_message(ws, message):
    """Handle incoming messages from the WebSocket server."""
    try:
        data = json.loads(message)
        print(f"Received message: {data}")
    except json.JSONDecodeError:
        print(f"Received raw message: {message}")


def on_error(ws, error):
    """Handle WebSocket errors."""
    print(f"Error occurred: {error}")


def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket connection closure."""
    print(f"Connection closed: {close_status_code} - {close_msg}")


def on_open(ws):
    """Handle WebSocket connection opening."""
    print("Connected to WebSocket endpoint")

    # Subscribe to some pairs
    subscribe_message = {"msg_type": "subscribe", "pairs": ["BTC/USD", "ETH/USD:MARK"]}
    print(f"Sending subscription: {subscribe_message}")
    ws.send(json.dumps(subscribe_message))


def main():
    # WebSocket URL
    websocket_url = "ws://localhost:8007/websocket/price/subscribe"

    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        websocket_url, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open
    )

    print(f"Connecting to {websocket_url}...")
    ws.run_forever()


if __name__ == "__main__":
    main()
