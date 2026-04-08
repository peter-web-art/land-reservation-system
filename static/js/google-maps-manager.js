/**
 * Google Maps Manager for Land Reservation System
 * Handles map initialization, markers, and responsive behavior
 */

class LandMapManager {
    constructor(options = {}) {
        this.mapElement = options.mapElement || document.getElementById('map');
        this.mapData = options.mapData || [];
        this.defaultLat = options.defaultLat || -6.5;
        this.defaultLng = options.defaultLng || 35.5;
        this.defaultZoom = options.defaultZoom || 6;
        this.map = null;
        this.markers = [];
        this.markerCluster = null;
        this.infoWindows = [];
        this.init();
    }

    init() {
        if (!this.mapElement) return;
        
        this.map = new google.maps.Map(this.mapElement, {
            zoom: this.defaultZoom,
            center: {
                lat: this.defaultLat,
                lng: this.defaultLng
            },
            mapTypeControl: true,
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            zoomControl: true,
            zoomControlOptions: {
                position: google.maps.ControlPosition.RIGHT_BOTTOM,
            },
            streetViewControl: true,
            fullscreenControl: true,
            gestureHandling: 'cooperative',
        });

        this.addMarkers();
        this.fitBounds();
        this.handleResize();
    }

    addMarkers() {
        if (!this.mapData || this.mapData.length === 0) return;

        const bounds = new google.maps.LatLngBounds();

        this.mapData.forEach(pin => {
            if (!pin.lat || !pin.lng) return;

            const marker = new google.maps.Marker({
                position: {
                    lat: parseFloat(pin.lat),
                    lng: parseFloat(pin.lng)
                },
                map: this.map,
                title: pin.title,
                icon: this.createMarkerIcon(pin.status),
                animation: google.maps.Animation.DROP,
            });

            const infoWindow = new google.maps.InfoWindow({
                content: this.createInfoWindowContent(pin),
                maxWidth: 300,
            });

            marker.addListener('click', () => {
                this.infoWindows.forEach(iw => iw.close());
                infoWindow.open(this.map, marker);
            });

            this.markers.push(marker);
            this.infoWindows.push(infoWindow);
            bounds.extend(marker.getPosition());
        });

        if (this.markers.length > 0) {
            this.map.fitBounds(bounds, {
                padding: 50,
            });
        }
    }

    createMarkerIcon(status) {
        const color = status === 'available' ? '#27ae60' : '#e74c3c';
        
        return {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: color,
            fillOpacity: 1,
            strokeColor: '#fff',
            strokeWeight: 2,
            scale: 8,
        };
    }

    createInfoWindowContent(pin) {
        return `
            <div style="padding: 12px; font-family: Arial, sans-serif;">
                <h3 style="margin: 0 0 8px; font-size: 14px; color: #2c3e50;">
                    ${this.escapeHtml(pin.title)}
                </h3>
                <p style="margin: 4px 0; font-size: 12px; color: #7f8c8d;">
                    ${this.escapeHtml(pin.location)}
                </p>
                <p style="margin: 4px 0; font-weight: bold; font-size: 13px; color: #27ae60;">
                    ${pin.price}
                </p>
                <p style="margin: 4px 0; font-size: 11px; color: ${pin.status === 'available' ? '#27ae60' : '#e74c3c'};">
                    ${pin.status === 'available' ? '✓ Available' : '✗ Reserved'}
                </p>
                <a href="/lands/${pin.id}/" style="color: #1a5c38; font-weight: 600; font-size: 12px; text-decoration: none; margin-top: 8px; display: inline-block;">
                    View Details →
                </a>
            </div>
        `;
    }

    fitBounds() {
        if (this.markers.length === 0) return;

        const bounds = new google.maps.LatLngBounds();
        this.markers.forEach(marker => bounds.extend(marker.getPosition()));
        this.map.fitBounds(bounds, { padding: 50 });
    }

    handleResize() {
        window.addEventListener('resize', () => {
            if (this.map) {
                google.maps.event.trigger(this.map, 'resize');
                this.fitBounds();
            }
        });

        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                if (this.map) {
                    google.maps.event.trigger(this.map, 'resize');
                    this.fitBounds();
                }
            }, 100);
        });
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    setMapType(type) {
        if (this.map) {
            this.map.setMapTypeId(type === 'satellite' ? google.maps.MapTypeId.SATELLITE : google.maps.MapTypeId.ROADMAP);
        }
    }

    clearMarkers() {
        this.markers.forEach(marker => marker.setMap(null));
        this.markers = [];
        this.infoWindows.forEach(iw => iw.close());
        this.infoWindows = [];
    }

    addMarker(lat, lng, title, status = 'available') {
        const marker = new google.maps.Marker({
            position: { lat: parseFloat(lat), lng: parseFloat(lng) },
            map: this.map,
            title: title,
            icon: this.createMarkerIcon(status),
        });
        this.markers.push(marker);
        return marker;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const mapElement = document.getElementById('map');
    if (mapElement && typeof google !== 'undefined') {
        const mapData = window.mapPins ? JSON.parse(window.mapPins) : [];
        window.mapManager = new LandMapManager({
            mapElement: mapElement,
            mapData: mapData,
            defaultLat: -6.5,
            defaultLng: 35.5,
            defaultZoom: 6,
        });
    }
});