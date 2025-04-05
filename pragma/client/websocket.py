import asyncio
import contextlib
import json
import time
from queue import Empty, Queue
from threading import Event, Thread

import websocket
from fastapi import WebSocket

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
        self.headers = {"Authorization": f"Bearer {settings.api_key}"}
        # Keep track of connected clients and their subscriptions
        self.connected_clients: dict[str, dict] = {}
        self._current_client: str | None = None
        # Message queue for broadcasting
        self.message_queue = Queue()
        # Event for stopping the broadcast thread
        self.stop_event = Event()
        # Track closed websockets
        self._closed_websockets: set[str] = set()
        # Lock for WebSocket operations
        self._ws_lock = Event()
        self._ws_lock.set()  # Initially unlocked
        # Start the broadcast thread
        self.broadcast_thread = Thread(target=self._process_messages, daemon=True)
        self.broadcast_thread.start()

    def _process_messages(self):
        """Process messages from the queue and broadcast them to clients."""
        while not self.stop_event.is_set():
            try:
                data = self.message_queue.get(timeout=1)  # 1 second timeout
                if data is None:  # Sentinel value to stop processing
                    break

                # Get the event loop for the current thread
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                try:
                    # Run the broadcast
                    loop.run_until_complete(self._broadcast_message(data))
                except Exception as e:
                    print(f"Error broadcasting message: {e}")
                finally:
                    if loop != asyncio.get_event_loop():
                        loop.close()

            except Empty:
                # This is normal - just a timeout while waiting for messages
                # No need to log this as an error
                pass
            except Exception as e:
                # Log actual errors (not Empty queue exceptions)
                import traceback

                print(f"Error processing message: {e}\nTrace: {traceback.format_exc()}")

    async def _broadcast_message(self, data: dict):
        """Broadcast message to all connected clients."""
        if not self.connected_clients:
            # If no clients are connected, close the upstream connection
            if self.ws and self.ws.sock and self.ws.sock.connected:
                print("No active clients, closing upstream connection")
                self.ws.close()
                self._running = False
            return

        # For subscription confirmations, only send to the relevant client
        if data.get("msg_type") == "subscribe" and "status" in data:
            for client_id, client_info in list(self.connected_clients.items()):
                websocket = client_info.get("websocket")
                if (
                    websocket
                    and client_id not in self._closed_websockets
                    and all(pair in client_info["subscriptions"] for pair in data["pairs"])
                ):
                    try:
                        await websocket.send_json(data)
                    except Exception as e:
                        print(f"Error sending subscription confirmation to client {client_id}: {e}")
            return

        # For price updates and other messages
        for client_id, client_info in list(self.connected_clients.items()):
            try:
                websocket = client_info.get("websocket")
                # Check if the websocket is still open before trying to send
                if websocket and client_id not in self._closed_websockets:
                    # Additional check for websocket state
                    try:
                        if hasattr(websocket, "client_state") and websocket.client_state.value != 3:
                            # Only forward price updates for pairs the client is subscribed to
                            client_pairs = client_info.get("subscriptions", set())
                            if "oracle_prices" in data:
                                # Filter oracle prices based on subscribed pairs
                                filtered_prices = [
                                    price
                                    for price in data.get("oracle_prices", [])
                                    if price.get("pair") in client_pairs
                                ]
                                if filtered_prices or not data.get("oracle_prices"):
                                    # Send either filtered prices or empty updates
                                    message = {"oracle_prices": filtered_prices, "timestamp": data.get("timestamp")}
                                    await websocket.send_json(message)
                            else:
                                # Forward other types of messages as is
                                await websocket.send_json(data)
                    except RuntimeError as re:
                        if "close message has been sent" not in str(re):
                            raise  # Re-raise if it's a different RuntimeError
                        print(f"WebSocket for client {client_id} already closing: {re}")
                        self._closed_websockets.add(client_id)
            except Exception as e:
                import traceback

                print(f"Error sending message to client {client_id}: {e}\nTrace: {traceback.format_exc()}")
                self.remove_client(client_id)

    def on_message(self, ws, message):
        """Handle incoming messages."""
        try:
            data = json.loads(message)
            print(f"Received from upstream: {data}")  # Debug log

            # Don't forward subscription confirmations from upstream
            if data.get("msg_type") == "subscribe":
                return

            # Add message to the queue for processing
            self.message_queue.put(data)
        except json.JSONDecodeError:
            print(f"Received invalid JSON: {message}")

    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"Upstream WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closure."""
        print(f"Upstream WebSocket connection closed: {close_status_code} - {close_msg}")
        self._running = False
        self.ws = None  # Clear the WebSocket instance

        if self.connected_clients:  # Only reconnect if we have active clients
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            self.connect()

    def on_open(self, ws):
        """Handle WebSocket connection opening."""
        print("Connected to Pragma Lightspeed")
        # Subscribe to any existing pairs
        if self.subscribed_pairs:
            self.subscribe(list(self.subscribed_pairs))

    def add_client(self, client_id: str, websocket: WebSocket):
        """Add a new client connection."""
        self.connected_clients[client_id] = {"websocket": websocket, "subscriptions": set()}
        self._current_client = client_id
        if not self._running and self.subscribed_pairs:
            Thread(target=self.connect).start()

    def remove_client(self, client_id: str):
        """Remove a client connection."""
        if client_id not in self.connected_clients:
            return
        client_info = self.connected_clients.pop(client_id)
        subscribed_pairs = client_info.get("subscriptions", set())

        # Mark the client as closed before trying to close the websocket
        self._closed_websockets.add(client_id)

        if websocket := client_info.get("websocket"):
            try:
                # Create a simple synchronized close for the WebSocket
                # Don't use asyncio.create_task as it may cause race conditions
                if hasattr(websocket, "_closed") and not websocket._closed:
                    # Use existing event loop if possible
                    with contextlib.suppress(RuntimeError):
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Schedule the close without awaiting
                            asyncio.run_coroutine_threadsafe(websocket.close(), loop)
                        else:
                            # Create a new loop if needed
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            new_loop.run_until_complete(websocket.close())
                            new_loop.close()
            except Exception as e:
                import traceback

                print(f"Error closing websocket for client {client_id}: {e}\nTrace: {traceback.format_exc()}")

        if subscribed_pairs:
            self.unsubscribe(list(subscribed_pairs), client_id)

        if not self.connected_clients and self.ws:
            print("No more clients connected, closing upstream connection")
            self.ws.close()
            self._running = False
            self.stop_event.set()  # Signal the broadcast thread to stop
            # Keep the closed websockets set for a bit longer in case messages are still being processed
            # Only clear it when we have no clients and are fully shutting down
            if not self.connected_clients:
                self._closed_websockets.clear()

    def subscribe(self, pairs: list[str], client_id: str = None):
        """Subscribe to price updates for specific pairs."""
        if client_id is None:
            client_id = self._current_client

        if client_id not in self.connected_clients:
            print(f"Client {client_id} not found")
            return

        # Update client's subscriptions
        self.connected_clients[client_id]["subscriptions"].update(pairs)
        self.subscribed_pairs.update(pairs)

        # Ensure connection is established before subscribing
        if not self.ws or not self._running or not self.ws.sock or not self.ws.sock.connected:
            self.connect()
            # Wait a bit for the connection to establish
            time.sleep(1)

        if self.ws and self.ws.sock and self.ws.sock.connected:
            # Send subscription message to upstream
            self.extracted_from_subscribe("subscribe", "Subscribed to pairs: ", pairs)

            # Send confirmation directly to the client via the message queue
            try:
                confirmation_message = {"msg_type": "subscribe", "pairs": pairs, "status": "subscribed"}
                self.message_queue.put(confirmation_message)
            except Exception as e:
                print(f"Error queueing subscription confirmation: {e}")
        else:
            print("Failed to subscribe: WebSocket connection not available")

    def unsubscribe(self, pairs: list[str], client_id: str = None):
        """Unsubscribe from price updates for specific pairs."""
        if client_id is None:
            client_id = self._current_client

        if client_id not in self.connected_clients:
            return

        # Remove pairs from client's subscriptions
        self.connected_clients[client_id]["subscriptions"].difference_update(pairs)

        # Check if any other clients are still subscribed to these pairs
        still_subscribed = set()
        for client_info in self.connected_clients.values():
            still_subscribed.update(client_info.get("subscriptions", set()))

        if pairs_to_unsubscribe := set(pairs) - still_subscribed:
            self.subscribed_pairs.difference_update(pairs_to_unsubscribe)
            self.extracted_from_subscribe("unsubscribe", "Unsubscribed from pairs: ", list(pairs_to_unsubscribe))

        # If no more subscriptions and no clients, close the connection
        if (not self.subscribed_pairs or not self.connected_clients) and self.ws:
            self.ws.close()

    def extracted_from_subscribe(self, msg_type: str, msg: str, pairs: list[str]):
        """Send subscription message to WebSocket."""
        if not self.ws or not self.ws.sock or not self.ws.sock.connected:
            print("Cannot send message: WebSocket is not connected")
            return

        try:
            message = {"msg_type": msg_type, "pairs": list(self.subscribed_pairs)}
            self.ws.send(json.dumps(message))
            print(f"{msg}{pairs}")
        except Exception as e:
            print(f"Error sending subscription message: {e}")
            # Trigger reconnection if needed
            if "socket is already closed" in str(e):
                self._running = False
                self.ws = None
                self.connect()

    def connect(self):
        """Connect to the Pragma Lightspeed WebSocket service."""
        if not self._ws_lock.is_set():
            print("Connection attempt already in progress...")
            return

        self._ws_lock.clear()  # Lock WebSocket operations
        try:
            if self.ws:
                try:
                    self.ws.close()
                except Exception:
                    pass
                self.ws = None

            print(f"Connecting to {self.url}...")
            self.ws = websocket.WebSocketApp(
                self.url,
                header=self.headers,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            self._running = True

            # Run WebSocket in a separate thread
            ws_thread = Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()

            # Wait for connection to establish or timeout
            timeout = 5  # seconds
            start_time = time.time()
            while not (self.ws.sock and self.ws.sock.connected) and time.time() - start_time < timeout:
                time.sleep(0.1)

            if not (self.ws.sock and self.ws.sock.connected):
                print("Failed to establish connection within timeout")
                self.ws.close()
                self.ws = None
                self._running = False
        finally:
            self._ws_lock.set()  # Unlock WebSocket operations

    def run(self):
        """Run the WebSocket client with automatic reconnection."""
        # Don't connect automatically, only when needed
        pass
