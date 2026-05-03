// Main JavaScript for Smart Parking System

// Load parking status
async function loadParkingStatus() {
    try {
        const data = await api.getLiveData();
        const container = document.getElementById('parkingStatus');

        if (container && data.zones) {
            let html = '';
            data.zones.forEach(zone => {
                const availabilityPercent = (zone.available_slots / zone.total_slots * 100).toFixed(0);
                const statusColor = availabilityPercent > 50 ? 'success' : (availabilityPercent > 20 ? 'warning' : 'danger');

                html += `
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">Zone ${zone.zone_id}</h5>
                                <h6 class="card-subtitle mb-2 text-muted">${zone.zone_name}</h6>
                                <div class="progress mb-2">
                                    <div class="progress-bar bg-${statusColor}" style="width: ${availabilityPercent}%"></div>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>Available: ${zone.available_slots}</span>
                                    <span>Occupied: ${zone.occupied_slots}</span>
                                </div>
                                <div class="mt-2 text-muted small">
                                    <i class="fas fa-dollar-sign"></i> $${zone.hourly_rate}/hour
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading parking status:', error);
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const data = await api.getDashboard();

        if (data.overview) {
            const elements = {
                'totalSlots': data.overview.total_slots,
                'availableSlots': data.overview.available_slots,
                'occupiedSlots': data.overview.occupied_slots,
                'reservedSlots': data.overview.reserved_slots,
                'occupancyRate': data.overview.occupancy_rate + '%'
            };

            for (const [id, value] of Object.entries(elements)) {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            }
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load predictions
async function loadPredictions() {
    try {
        const data = await api.getPredictions();
        const container = document.getElementById('zonePredictions');

        if (container && data.predictions) {
            let html = '<div class="list-group">';
            data.predictions.forEach(pred => {
                const probPercent = (pred.availability_probability * 100).toFixed(0);
                const barColor = probPercent > 70 ? 'success' : (probPercent > 40 ? 'warning' : 'danger');

                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <strong>Zone ${pred.zone_id}</strong>
                            <span class="badge bg-${barColor}">${pred.prediction}</span>
                        </div>
                        <div class="progress mt-2" style="height: 5px;">
                            <div class="progress-bar bg-${barColor}" style="width: ${probPercent}%"></div>
                        </div>
                        <small class="text-muted">Confidence: ${(pred.confidence * 100).toFixed(0)}%</small>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading predictions:', error);
    }
}

// Handle login
async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // This would connect to Django authentication
    showNotification('Login feature coming soon!', 'info');
    return false;
}

// Handle reservation
async function handleReservation(event) {
    event.preventDefault();

    const vehicleType = document.getElementById('vehicleType').value;
    const vehicleNumber = document.getElementById('vehicleNumber').value;
    const duration = parseInt(document.getElementById('duration').value);
    const preferredZone = document.getElementById('preferredZone').value;

    try {
        const result = await api.allocateParking({
            vehicle_type: vehicleType,
            vehicle_number: vehicleNumber,
            duration: duration,
            preferred_zone: preferredZone || null,
            is_reservation: true
        });

        if (result.success) {
            showNotification(`✅ Slot ${result.slot_number} reserved!`, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('reservationModal'));
            modal.hide();
            document.getElementById('reservationForm').reset();
        } else {
            showNotification(result.error || 'Reservation failed', 'danger');
        }
    } catch (error) {
        showNotification('Error making reservation', 'danger');
    }

    return false;
}

// Refresh all data
function refreshAllData() {
    loadParkingStatus();
    loadStatistics();
    loadPredictions();
    showNotification('Data refreshed', 'info');
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadParkingStatus();
    loadStatistics();
    loadPredictions();

    // Set up form handlers
    const loginForm = document.getElementById('loginForm');
    if (loginForm) loginForm.onsubmit = handleLogin;

    const reservationForm = document.getElementById('reservationForm');
    if (reservationForm) reservationForm.onsubmit = handleReservation;

    // Auto refresh every 30 seconds
    setInterval(refreshAllData, 30000);
});