class TrackingManager {
    constructor() {
        this.isTracking = false;
        this.watchId = null;
        this.currentSession = null;
        this.lastPosition = null;
        this.totalDistance = 0;
        this.startTime = null;
        this.stopTimer = null;
        this.stopStartTime = null;
        this.stopsCount = 0;
        
        this.mapManager = new MapManager();
        this.updateInterval = 15000; // 15 saniyə
    }

    startTracking() {
        if (this.isTracking) return;

        if (!navigator.geolocation) {
            alert('Brauzeriniz GPS-i dəstəkləmir!');
            return;
        }

        this.isTracking = true;
        this.startTime = new Date();
        this.totalDistance = 0;
        this.stopsCount = 0;
        
        // Xəritəni təmizlə
        this.mapManager.clearMap();
        
        // Yeni sessiya yarat
        this.createSession();
        
        // GPS izləməni başlat
        this.watchId = navigator.geolocation.watchPosition(
            position => this.handlePositionUpdate(position),
            error => this.handlePositionError(error),
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );

        this.updateUI();
    }

    stopTracking() {
        if (!this.isTracking) return;

        this.isTracking = false;
        
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        
        if (this.stopTimer) {
            clearTimeout(this.stopTimer);
            this.stopTimer = null;
        }
        
        // Sessiyanı bitir
        this.endSession();
        this.updateUI();
    }

    handlePositionUpdate(position) {
        const { latitude, longitude, speed } = position.coords;
        const timestamp = new Date(position.timestamp);
        
        // İlk mövqe üçün marker əlavə et
        if (!this.lastPosition) {
            this.mapManager.addMarker(latitude, longitude, 'Başlanğıc nöqtəsi');
        }
        
        // Məsafəni hesabla
        if (this.lastPosition) {
            const distance = this.calculateDistance(
                this.lastPosition.latitude,
                this.lastPosition.longitude,
                latitude,
                longitude
            );
            this.totalDistance += distance;
        }
        
        // Xəritəni yenilə
        this.mapManager.addRoutePoint(latitude, longitude);
        
        // Dayanma yoxlaması
        this.checkForStop(speed, latitude, longitude, timestamp);
        
        // Məlumatları bazaya göndər
        this.saveLocation(latitude, longitude, speed, timestamp);
        
        // UI yenilə
        this.updateStats(position.coords);
        
        this.lastPosition = { latitude, longitude, timestamp };
    }

    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // Yer radiusu (metr)
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                Math.cos(φ1) * Math.cos(φ2) *
                Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

        return R * c; // metr
    }

    checkForStop(speed, lat, lng, timestamp) {
        const STOP_SPEED_THRESHOLD = 0.1; // m/s
        const STOP_DURATION = 5 * 60 * 1000; // 5 dəqiqə (millisaniyə)
        
        if (speed < STOP_SPEED_THRESHOLD) {
            if (!this.stopStartTime) {
                // Dayanma başladı
                this.stopStartTime = timestamp;
                this.stopTimer = setTimeout(() => {
                    // 5 dəqiqə dayanıbsa, dayanma nöqtəsi qeyd et
                    this.recordStopPoint(lat, lng);
                    this.stopsCount++;
                    this.stopStartTime = null;
                }, STOP_DURATION);
            }
        } else {
            // Hərəkət davam edir
            if (this.stopTimer) {
                clearTimeout(this.stopTimer);
                this.stopTimer = null;
            }
            this.stopStartTime = null;
        }
    }

    recordStopPoint(lat, lng) {
        const duration = 5 * 60; // 5 dəqiqə (saniyə)
        this.mapManager.addStopMarker(lat, lng, duration);
        
        // Bazaya dayanma məlumatını göndər
        this.saveStopPoint(lat, lng, duration);
    }

    updateStats(coords) {
        // Məsafə
        document.getElementById('distance').textContent = 
            (this.totalDistance / 1000).toFixed(2) + ' km';
        
        // Müddət
        if (this.startTime) {
            const duration = Math.floor((new Date() - this.startTime) / 1000);
            document.getElementById('duration').textContent = 
                this.formatTime(duration);
        }
        
        // Sürət
        const speedKmh = coords.speed ? (coords.speed * 3.6).toFixed(1) : '0';
        document.getElementById('speed').textContent = speedKmh + ' km/s';
        
        // Dayanma sayı
        document.getElementById('stops').textContent = this.stopsCount + ' dəfə';
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    updateUI() {
        const startBtn = document.getElementById('startTracking');
        const stopBtn = document.getElementById('stopTracking');
        const statusText = document.getElementById('statusText');
        const gpsStatus = document.getElementById('gpsStatus');
        
        if (this.isTracking) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusText.textContent = 'İzləmə aktiv';
            gpsStatus.textContent = 'GPS Aktiv';
            gpsStatus.className = 'gps-on';
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.textContent = 'İzləmə dayanıb';
            gpsStatus.textContent = 'GPS';
            gpsStatus.className = 'gps-off';
        }
    }

    handlePositionError(error) {
        console.error('GPS xətası:', error);
        let message = 'GPS xətası: ';
        
        switch(error.code) {
            case error.PERMISSION_DENIED:
                message += 'İcazə verilmədi';
                break;
            case error.POSITION_UNAVAILABLE:
                message += 'Mövqe müəyyən edilə bilmir';
                break;
            case error.TIMEOUT:
                message += 'Sorğunun müddəti bitdi';
                break;
            default:
                message += 'Naməlum xəta';
        }
        
        alert(message);
    }

    // Django API ilə əlaqə funksiyaları
    async createSession() {
        try {
            const response = await fetch('/api/tracking/sessions/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    start_time: this.startTime.toISOString()
                })
            });
            
            if (response.ok) {
                this.currentSession = await response.json();
            }
        } catch (error) {
            console.error('Sessiya yaradılarkən xəta:', error);
        }
    }

    async saveLocation(lat, lng, speed, timestamp) {
        if (!this.currentSession) return;
        
        try {
            await fetch('/api/tracking/locations/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    session: this.currentSession.id,
                    latitude: lat,
                    longitude: lng,
                    speed: speed,
                    timestamp: timestamp.toISOString()
                })
            });
        } catch (error) {
            console.error('Mövqe saxlanarkən xəta:', error);
        }
    }

    async saveStopPoint(lat, lng, duration) {
        if (!this.currentSession) return;
        
        try {
            await fetch('/api/tracking/stops/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    session: this.currentSession.id,
                    latitude: lat,
                    longitude: lng,
                    duration: duration
                })
            });
        } catch (error) {
            console.error('Dayanma nöqtəsi saxlanarkən xəta:', error);
        }
    }

    async endSession() {
        if (!this.currentSession) return;
        
        try {
            const duration = Math.floor((new Date() - this.startTime) / 1000);
            
            await fetch(`/api/tracking/sessions/${this.currentSession.id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    end_time: new Date().toISOString(),
                    total_distance: this.totalDistance,
                    total_duration: duration
                })
            });
        } catch (error) {
            console.error('Sessiya bitirilərkən xəta:', error);
        }
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}