#!/bin/bash

# Script to commit all responsive design changes at once
# Run this from your repository root directory

echo "🚀 Starting complete responsive design commit process..."

# 1. Create land-cards-responsive.css
cat > static/css/land-cards-responsive.css << 'EOF'
/* Land Cards Responsive Styling */

.lands-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
    padding: 1rem;
}

@media (min-width: 640px) {
    .lands-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 1.25rem;
        padding: 1.5rem;
    }
}

@media (min-width: 1024px) {
    .lands-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        padding: 2rem;
    }
}

.land-card {
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    height: 100%;
}

.land-card:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    transform: translateY(-4px);
}

.land-card__image {
    width: 100%;
    height: 200px;
    background: #e0e0e0;
    object-fit: cover;
    position: relative;
}

@media (min-width: 768px) {
    .land-card__image {
        height: 250px;
    }
}

.land-card__badge {
    position: absolute;
    top: 12px;
    right: 12px;
    background: #ff6b6b;
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.land-card__content {
    padding: 1.5rem;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
}

.land-card__title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #2c3e50;
}

.land-card__location {
    color: #7f8c8d;
    font-size: 0.95rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.land-card__details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin: 1rem 0;
    padding: 1rem 0;
    border-top: 1px solid #ecf0f1;
    border-bottom: 1px solid #ecf0f1;
}

.land-card__detail-item {
    text-align: center;
}

.land-card__detail-label {
    font-size: 0.85rem;
    color: #7f8c8d;
    margin-bottom: 0.25rem;
}

.land-card__detail-value {
    font-size: 1.1rem;
    font-weight: 600;
    color: #2c3e50;
}

.land-card__price {
    font-size: 1.5rem;
    font-weight: 700;
    color: #27ae60;
    margin: 1rem 0;
}

.land-card__actions {
    display: flex;
    gap: 1rem;
    margin-top: auto;
}

.land-card__btn {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.95rem;
    min-height: 44px;
}

.land-card__btn-primary {
    background: #3498db;
    color: white;
}

.land-card__btn-primary:hover {
    background: #2980b9;
}

.land-card__btn-primary:active {
    background: #1f618d;
}

.land-card__btn-secondary {
    background: #ecf0f1;
    color: #2c3e50;
    border: 1px solid #bdc3c7;
}

.land-card__btn-secondary:hover {
    background: #d5dbdb;
}

.land-card__btn-secondary:active {
    background: #b8bfc7;
}

.land-card__status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 500;
}

.land-card__status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}

.land-card__status-dot.available {
    background: #27ae60;
}

.land-card__status-dot.reserved {
    background: #e74c3c;
}

.carousel-prev,
.carousel-next {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.9);
    border: none;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    z-index: 10;
}

.carousel-prev:hover,
.carousel-next:hover {
    background: white;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.carousel-prev {
    left: 8px;
}

.carousel-next {
    right: 8px;
}

@media (max-width: 480px) {
    .land-card__content {
        padding: 1.25rem;
    }

    .land-card__title {
        font-size: 1.1rem;
    }

    .land-card__actions {
        flex-direction: column;
    }

    .land-card__btn {
        width: 100%;
    }

    .land-card__details {
        gap: 0.75rem;
    }
}
EOF

echo "✅ Created static/css/land-cards-responsive.css"

# 2. Create google-maps-responsive.css
cat > static/css/google-maps-responsive.css << 'EOF'
/* Google Maps Responsive Styling */

.map-container {
    width: 100%;
    height: 100vh;
    position: relative;
}

.map-wrapper {
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
}

@media (max-width: 1024px) {
    .map-container {
        height: 60vh;
    }
}

@media (max-width: 768px) {
    .map-container {
        height: 50vh;
        min-height: 300px;
    }
}

@media (max-width: 480px) {
    .map-container {
        height: 40vh;
        min-height: 250px;
    }
}

.map-controls {
    position: absolute;
    top: 15px;
    right: 15px;
    z-index: 400;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.map-control-btn {
    width: 40px;
    height: 40px;
    background: white;
    border: none;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
}

.map-control-btn:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    transform: scale(1.05);
}

.map-control-btn:active {
    transform: scale(0.95);
}

@media (max-width: 768px) {
    .map-control-btn {
        width: 44px;
        height: 44px;
    }
}

.custom-marker {
    background: white;
    border: 2px solid #1a5c38;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.custom-marker.available {
    border-color: #059669;
    color: #059669;
}

.custom-marker.reserved {
    border-color: #f59e0b;
    color: #f59e0b;
}

.custom-marker:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    transform: scale(1.1);
}

.map-info-window {
    background: white;
    border-radius: 8px;
    padding: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.map-info-window h3 {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: #2c3e50;
}

.map-info-window p {
    margin: 4px 0;
    font-size: 12px;
    color: #7f8c8d;
}

@media (max-width: 768px) {
    .map-overlay {
        position: fixed;
        inset: 0;
        z-index: 999;
        background: white;
    }
    
    .map-overlay .map-container {
        height: 100vh;
    }
}

.map-layer-toggle {
    display: flex;
    background: white;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    overflow: hidden;
}

.map-layer-toggle button {
    padding: 8px 12px;
    border: none;
    background: white;
    color: #666;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.3s ease;
}

.map-layer-toggle button.active {
    background: #1a5c38;
    color: white;
}

.map-layer-toggle button:hover {
    background: #f5f5f5;
}

.map-layer-toggle button.active:hover {
    background: #134428;
}

.map-filter-panel {
    position: absolute;
    bottom: 20px;
    left: 20px;
    right: 20px;
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 300;
}

@media (max-width: 768px) {
    .map-filter-panel {
        bottom: 70px;
        left: 10px;
        right: 10px;
        padding: 12px;
    }
}

.map-draw-tools {
    position: absolute;
    bottom: 20px;
    left: 20px;
    background: white;
    border-radius: 4px;
    padding: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    display: none;
}

.map-draw-tools.active {
    display: flex;
    gap: 8px;
    align-items: center;
}

.map-draw-tools button {
    padding: 8px 12px;
    background: #1a5c38;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}

.map-draw-tools button:hover {
    background: #134428;
}
EOF

echo "✅ Created static/css/google-maps-responsive.css"

# 3. Create google-maps-manager.js
cat > static/js/google-maps-manager.js << 'EOF'
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
                    📍 ${this.escapeHtml(pin.location)}
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
EOF

echo "✅ Created static/js/google-maps-manager.js"

# 4. Create RESPONSIVE_DESIGN_GUIDE.md
cat > RESPONSIVE_DESIGN_GUIDE.md << 'EOF'
# Responsive Design Guide - LandReserve

## Overview
This guide documents the responsive design improvements made to the land-reservation-system for optimal viewing across desktop, tablet, and mobile devices.

## File Structure
