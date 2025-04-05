import json
import uuid

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect, status

from pragma.config import get_settings
from pragma.utils.ws import lightspeed_client

settings = get_settings()

app = APIRouter(
    prefix="/data",
    tags=["websocket"],
)


async def get_token(websocket: WebSocket, authorization: str = Header(None)):
    """Validate the authorization token."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization header is required")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization scheme")
        if token != settings.api_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
        return token
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization header format")


@app.websocket("/price/subscribe")
async def websocket_endpoint(websocket: WebSocket, authorization: str = Header(None)):
    client_id = str(uuid.uuid4())

    try:
        # Validate the authorization token
        await get_token(websocket, authorization)

        # Accept the WebSocket connection
        await websocket.accept()
        print(f"Client {client_id} connected to WebSocket endpoint")

        # Add client to the Lightspeed client
        lightspeed_client.add_client(client_id, websocket)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    msg_type = message.get("msg_type")
                    pairs = message.get("pairs", [])

                    if msg_type == "subscribe":
                        # Subscribe to pairs in Pragma Lightspeed
                        lightspeed_client.subscribe(pairs, client_id)
                        # Send confirmation back to client
                        await websocket.send_json({"msg_type": "subscribe", "pairs": pairs, "status": "subscribed"})
                    elif msg_type == "unsubscribe":
                        # Unsubscribe from pairs in Pragma Lightspeed
                        lightspeed_client.unsubscribe(pairs, client_id)
                        # Send confirmation back to client
                        await websocket.send_json({"msg_type": "unsubscribe", "pairs": pairs, "status": "unsubscribed"})
                    else:
                        await websocket.send_json(
                            {
                                "error": "Invalid message type",
                                "details": "msg_type must be either 'subscribe' or 'unsubscribe'",
                            }
                        )
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON", "details": "Message must be valid JSON"})
        except WebSocketDisconnect:
            print(f"Client {client_id} disconnected from WebSocket endpoint")
        except Exception as e:
            import traceback

            print(f"Error in WebSocket connection for client {client_id}: {e}\nTrace: {traceback.format_exc()}")
        finally:
            # Clean up the connection - Remove client first before closing the socket
            lightspeed_client.remove_client(client_id)
            try:
                # Check if the WebSocket is already closed before trying to close it again
                if websocket and hasattr(websocket, "_closed") and not websocket._closed:
                    await websocket.close()
            except RuntimeError as re:
                # Specifically handle "Cannot call send once a close message has been sent"
                if "close message has been sent" not in str(re):
                    print(f"Error during WebSocket close for client {client_id}: {re}")
            except Exception as e:
                # Log other exceptions but continue cleanup
                print(f"Error during WebSocket close for client {client_id}: {e}")
    except HTTPException as e:
        print(f"Authentication failed for client {client_id}: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
