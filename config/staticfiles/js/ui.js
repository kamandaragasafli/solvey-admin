class UIManager {
    constructor() {
        this.trackingManager = new TrackingManager();
        this.initEventListeners();
        this.loadSessionHistory();
    }

    initEventListeners() {
        // İzləmə kontrolları
        document.getElementById('startTracking').addEventListener('click', () => {
            this.trackingManager.startTracking();
        });

        document.getElementById('stopTracking').addEventListener('click', () => {
            this.trackingManager.stopTracking();
            this.loadSessionHistory();
        });

        // Modal kontrolları
        document.getElementById('loginBtn').addEventListener('click', () => {
            this.showModal('loginModal');
        });

        document.getElementById('registerBtn').addEventListener('click', () => {
            this.showModal('registerModal');
        });

        // Modal bağlama
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.target.closest('.modal').style.display = 'none';
            });
        });

        // Xarici kliklə modalı bağlama
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });

        // Form göndərmə
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
    }

    showModal(modalId) {
        document.getElementById(modalId).style.display = 'block';
    }

    hideModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    async handleLogin() {
        const form = document.getElementById('loginForm');
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/api/auth/login/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.trackingManager.getCSRFToken()
                },
                body: formData
            });

            if (response.ok) {
                this.hideModal('loginModal');
                this.updateUserInterface();
            } else {
                alert('Giriş uğursuz oldu!');
            }
        } catch (error) {
            console.error('Giriş xətası:', error);
        }
    }

    async loadSessionHistory() {
        try {
            const response = await fetch('/api/tracking/sessions/');
            if (response.ok) {
                const sessions = await response.json();
                this.displaySessions(sessions);
            }
        } catch (error) {
            console.error('Sessiya tarixçəsi yüklənərkən xəta:', error);
        }
    }

    displaySessions(sessions) {
        const container = document.getElementById('sessionsList');
        container.innerHTML = '';

        sessions.forEach(session => {
            const sessionElement = document.createElement('div');
            sessionElement.className = 'session-item';
            sessionElement.innerHTML = `
                <strong>${new Date(session.start_time).toLocaleString('az-AZ')}</strong>
                <div>Məsafə: ${(session.total_distance / 1000).toFixed(2)} km</div>
                <div>Müddət: ${this.formatTime(session.total_duration)}</div>
            `;
            
            sessionElement.addEventListener('click', () => {
                this.showSessionDetails(session.id);
            });
            
            container.appendChild(sessionElement);
        });
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    async showSessionDetails(sessionId) {
        try {
            const response = await fetch(`/api/tracking/sessions/${sessionId}/`);
            if (response.ok) {
                const session = await response.json();
                // Sessiya detallarını göstər
                this.displaySessionOnMap(session);
            }
        } catch (error) {
            console.error('Sessiya detalları yüklənərkən xəta:', error);
        }
    }

    displaySessionOnMap(session) {
        // Xəritəni təmizlə
        this.trackingManager.mapManager.clearMap();
        
        // Sessiya məlumatlarını xəritədə göstər
        session.locations.forEach((location, index) => {
            if (index === 0) {
                this.trackingManager.mapManager.addMarker(
                    location.latitude, 
                    location.longitude, 
                    'Başlanğıc'
                );
            }
            this.trackingManager.mapManager.addRoutePoint(
                location.latitude, 
                location.longitude
            );
        });
        
        // Dayanma nöqtələrini göstər
        session.stops.forEach(stop => {
            this.trackingManager.mapManager.addStopMarker(
                stop.latitude,
                stop.longitude,
                stop.duration
            );
        });
    }

    updateUserInterface() {
        // İstifadəçi interfeysini yenilə
        const userControls = document.querySelector('.user-controls');
        // Giriş edildikdə kontrolları dəyiş
    }
}

// App başladıldıqda
document.addEventListener('DOMContentLoaded', () => {
    new UIManager();
});