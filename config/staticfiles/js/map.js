class MapManager {
    constructor() {
        this.map = null;
        this.markers = [];
        this.polyline = null;
        this.routePoints = [];
        this.initMap();
    }

    initMap() {
        // Xəritəni başlat
        this.map = L.map('map').setView([40.4093, 49.8671], 13); // Bakı koordinatları
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
    }

    addMarker(lat, lng, popupText = '') {
        const marker = L.marker([lat, lng])
            .addTo(this.map)
            .bindPopup(popupText);
        
        this.markers.push(marker);
        return marker;
    }

    updatePolyline() {
        // Köhnə xətti sil
        if (this.polyline) {
            this.map.removeLayer(this.polyline);
        }

        // Yeni xətt çək
        if (this.routePoints.length > 1) {
            this.polyline = L.polyline(this.routePoints, {
                color: 'blue',
                weight: 4,
                opacity: 0.7
            }).addTo(this.map);
        }
    }

    addRoutePoint(lat, lng) {
        this.routePoints.push([lat, lng]);
        this.updatePolyline();
        
        // Xəritəni son nöqtəyə fokusla
        this.map.setView([lat, lng], this.map.getZoom());
    }

    clearMap() {
        // Bütün markerları və xətti təmizlə
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.markers = [];
        
        if (this.polyline) {
            this.map.removeLayer(this.polyline);
            this.polyline = null;
        }
        
        this.routePoints = [];
    }

    addStopMarker(lat, lng, duration) {
        const stopMarker = L.circleMarker([lat, lng], {
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.5,
            radius: 8
        }).addTo(this.map)
          .bindPopup(`Dayanma: ${duration} saniyə`);
        
        this.markers.push(stopMarker);
    }
}