// WebSocket Manager for Real-time Updates

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.eventHandlers = new Map();
        this.messageHandlers = new Map();
        this.isConnected = false;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = protocol + window.location.host + '/ws/parking/';

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.triggerEvent('connect');

            // Subscribe to default groups
            this.subscribe(['parking_updates', 'zone_updates']);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.triggerEvent('error', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.triggerEvent('disconnect');
            this.reconnect();
        };
    }

    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        console.log(`Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
    }

    handleMessage(data) {
        const type = data.type;

        // Trigger specific message handlers
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            handlers.forEach(handler => handler(data.data || data));
        }

        // Trigger generic message handler
        if (this.messageHandlers.has('*')) {
            const handlers = this.messageHandlers.get('*');
            handlers.forEach(handler => handler(data));
        }
    }

    onMessage(type, handler) {
        if (!this.messageHandlers.has(type)) {
            this.messageHandlers.set(type, []);
        }
        this.messageHandlers.get(type).push(handler);
    }

    onEvent(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    triggerEvent(event, data = null) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => handler(data));
        }
    }

    send(data) {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    subscribe(groups) {
        return this.send({
            type: 'subscribe',
            groups: groups
        });
    }

    unsubscribe(groups) {
        return this.send({
            type: 'unsubscribe',
            groups: groups
        });
    }

    getNearestParking(lat, lng, vehicleType = 'Sedan') {
        return this.send({
            type: 'get_nearest',
            lat: lat,
            lng: lng,
            vehicle_type: vehicleType
        });
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Global WebSocket instance
let wsManager = null;

function initWebSocket() {
    wsManager = new WebSocketManager();
    wsManager.connect();
    return wsManager;
}

function getWebSocket() {
    if (!wsManager) {
        return initWebSocket();
    }
    return wsManager;
}