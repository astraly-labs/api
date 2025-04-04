import json
import time

import websocket

from pragma.config import get_settings

settings = get_settings()


class PragmaLightspeedClient:
    """Client for connecting to Pragma's Lightspeed WebSocket service."""

    def __init__(self, url: str):
        """Initialize the Lightspeed client.

        Args:
            url: The WebSocket URL to connect to
        """
        self.url = settings.pragma_websocket_url
        self.ws: websocket.WebSocketApp | None = None
        self.subscribed_pairs: set[str] = set()
        self._running = False

    def on_message(self, ws, message):
        """Handle incoming messages."""
        try:
            data = json.loads(message)
            # Handle different message types
            if "msg_type" in data:
                if data["msg_type"] in ["subscribe", "unsubscribe"]:
                    print(f"Subscription update: {data}")
            else:
                print(f"Price update: {data}")
        except json.JSONDecodeError:
            print(f"Received invalid JSON: {message}")

    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closure."""
        print(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        if self._running:
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            self.connect()

    def on_open(self, ws):
        """Handle WebSocket connection opening."""
        print("Connected to Pragma Lightspeed")
        # Subscribe to any existing pairs
        if self.subscribed_pairs:
            self.subscribe(list(self.subscribed_pairs))

    def subscribe(self, pairs: list[str]):
        """Subscribe to price updates for specific pairs."""
        if not self.ws:
            print("WebSocket not connected")
            return

        self.subscribed_pairs.update(pairs)
        self.extracted_from_subscribe("subscribe", "Subscribed to pairs: ", pairs)

    def unsubscribe(self, pairs: list[str]):
        """Unsubscribe from price updates for specific pairs."""
        if not self.ws:
            print("WebSocket not connected")
            return

        self.subscribed_pairs.difference_update(pairs)
        self.extracted_from_subscribe("unsubscribe", "Unsubscribed from pairs: ", pairs)

    def extracted_from_subscribe(self, msg_type: str, msg: str, pairs: list[str]):
        message = {"msg_type": msg_type, "pairs": list(self.subscribed_pairs)}
        self.ws.send(json.dumps(message))
        print(f"{msg}{pairs}")

    def connect(self):
        """Connect to the Pragma Lightspeed WebSocket service."""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            return

        print(f"Connecting to {self.url}...")
        self.ws = websocket.WebSocketApp(
            self.url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close
        )
        self._running = True
        self.ws.run_forever()

    def run(self):
        """Run the WebSocket client with automatic reconnection."""
        self.connect()
