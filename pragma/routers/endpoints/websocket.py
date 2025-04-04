import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pragma.utils.ws import lightspeed_client

app = APIRouter(
    prefix="/websocket",
    tags=["websocket"],
)


@app.websocket("/price/subscribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected to our WebSocket endpoint")

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
                    lightspeed_client.subscribe(pairs)
                    # Send confirmation back to client
                    await websocket.send_json({"msg_type": "subscribe", "pairs": pairs, "status": "subscribed"})
                elif msg_type == "unsubscribe":
                    # Unsubscribe from pairs in Pragma Lightspeed
                    lightspeed_client.unsubscribe(pairs)
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
        print("Client disconnected from our WebSocket endpoint")
    except Exception as e:
        print(f"Error in WebSocket connection: {e}")
        await websocket.close()
