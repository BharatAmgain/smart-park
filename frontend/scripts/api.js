// API Service for Smart Parking System

const API_BASE = '/api';

class ParkingAPI {
    constructor() {
        this.baseUrl = API_BASE;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Dashboard
    async getDashboard() {
        return this.request('/dashboard/');
    }

    // Zones
    async getZones() {
        return this.request('/zones/');
    }

    async getZone(zoneId) {
        return this.request(`/zones/${zoneId}/`);
    }

    // Slots
    async getSlots(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return this.request(`/slots/${params ? '?' + params : ''}`);
    }

    async getAvailableSlots(zoneId = null) {
        let url = '/slots/available/';
        if (zoneId) url += `?zone=${zoneId}`;
        return this.request(url);
    }

    // Allocation
    async allocateParking(data) {
        return this.request('/allocate/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // Nearest Parking
    async findNearestParking(lat, lng, vehicleType = 'Sedan', limit = 10) {
        return this.request('/nearest/', {
            method: 'POST',
            body: JSON.stringify({
                lat: lat,
                lng: lng,
                vehicle_type: vehicleType,
                limit: limit
            })
        });
    }

    // Predictions
    async getPredictions(zoneId = null) {
        let url = '/predict/';
        if (zoneId) url += `?zone=${zoneId}`;
        return this.request(url);
    }

    async predictAvailability(data) {
        return this.request('/predict/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // Sessions
    async getActiveSessions() {
        return this.request('/sessions/active/');
    }

    async endSession(sessionId) {
        return this.request(`/sessions/${sessionId}/end_session/`, {
            method: 'POST'
        });
    }

    // Live Data
    async getLiveData() {
        return this.request('/live/');
    }

    async getRealtimeUpdates() {
        return this.request('/realtime/');
    }

    // Statistics
    async getZoneStatistics() {
        return this.request('/zone-stats/');
    }
}

const api = new ParkingAPI();

// Helper function to show notification
function showNotification(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">SmartPark</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;

    document.querySelector('.toast-container').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}