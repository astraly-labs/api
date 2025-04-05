const WebSocket = require("ws");
require("dotenv").config();

class PragmaWebSocketClient {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.ws = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 5000; // 5 seconds
        this.subscriptions = new Set();
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log("Already connected");
            return;
        }

        console.log("Connecting to WebSocket...");
        this.ws = new WebSocket(
            "ws://localhost:8007/node/v1/data/price/subscribe",
            {
                headers: {
                    Authorization: `Bearer ${this.apiKey}`,
                },
            }
        );

        this.ws.on("open", () => {
            console.log("Connected to WebSocket");
            this.connected = true;
            this.reconnectAttempts = 0;

            // Resubscribe to previous subscriptions
            if (this.subscriptions.size > 0) {
                this.subscribe(Array.from(this.subscriptions));
            }
        });

        this.ws.on("message", (data) => {
            try {
                const message = JSON.parse(data);
                if (
                    message.msg_type === "subscribe" &&
                    message.status === "subscribed"
                ) {
                    console.log("Subscription confirmed:", message.pairs);
                    message.pairs.forEach((pair) => this.subscriptions.add(pair));
                } else if (message.oracle_prices !== undefined) {
                    console.log("Price update:", JSON.stringify(message, null, 2));
                } else {
                    console.log("Received message:", JSON.stringify(message, null, 2));
                }
            } catch (error) {
                console.error("Error parsing message:", error);
                console.log("Raw message:", data.toString());
            }
        });

        this.ws.on("close", (code, reason) => {
            console.log(`WebSocket closed: ${code} - ${reason}`);
            this.connected = false;
            this.reconnect();
        });

        this.ws.on("error", (error) => {
            console.error("WebSocket error:", error);
        });
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.connected = false;
            this.subscriptions.clear();
        }
    }

    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log("Max reconnection attempts reached");
            return;
        }

        this.reconnectAttempts++;
        console.log(
            `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
        );
        setTimeout(() => this.connect(), this.reconnectDelay);
    }

    subscribe(pairs) {
        if (!this.connected) {
            console.log("Not connected. Connect first.");
            return;
        }

        const message = {
            msg_type: "subscribe",
            pairs: pairs,
        };

        console.log("Subscribing to pairs:", pairs);
        this.ws.send(JSON.stringify(message));
        pairs.forEach((pair) => this.subscriptions.add(pair));
    }

    unsubscribe(pairs) {
        if (!this.connected) {
            console.log("Not connected. Connect first.");
            return;
        }

        const message = {
            msg_type: "unsubscribe",
            pairs: pairs,
        };

        console.log("Unsubscribing from pairs:", pairs);
        this.ws.send(JSON.stringify(message));
        pairs.forEach((pair) => this.subscriptions.delete(pair));
    }
}

// Get API key from environment variable
const apiKey = process.env.PRAGMA_API_KEY;
if (!apiKey) {
    console.error("PRAGMA_API_KEY environment variable is not set");
    process.exit(1);
}

// Create and start the client
const client = new PragmaWebSocketClient(apiKey);
const pairs = ["BTC/USD", "ETH/USD:MARK"];

// Connect and subscribe
client.connect();
setTimeout(() => {
    client.subscribe(pairs);
}, 1000);

// Handle process termination
process.on("SIGINT", () => {
    console.log("\nDisconnecting...");
    client.disconnect();
    process.exit();
});

// Keep the process running
process.stdin.resume();
