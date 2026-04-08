# Responsive Design Guide - LandReserve

## Overview
This guide documents the responsive design improvements made to the land-reservation-system for optimal viewing across desktop, tablet, and mobile devices.

## File Structure

### CSS Files
- `static/css/responsive-framework.css` - Base responsive utilities and breakpoints
- `static/css/land-cards-responsive.css` - Responsive land card grid and styling
- `static/css/google-maps-responsive.css` - Google Maps responsive behavior

### JavaScript Files
- `static/js/google-maps-manager.js` - Google Maps initialization and management

## Breakpoints

| Breakpoint | Width | Devices |
|------------|-------|---------|
| xs | < 480px | Mobile small |
| sm | 480px | Mobile large |
| md | 768px | Tablet |
| lg | 1024px | Desktop small |
| xl | 1280px | Desktop large |

## Land Cards Responsive Grid

```css
/* Mobile first - single column */
.lands-grid {
    grid-template-columns: 1fr;
}

/* Tablet - 2 columns */
@media (min-width: 640px) {
    .lands-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Desktop - 3 columns */
@media (min-width: 1024px) {
    .lands-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}
```

## Google Maps Responsive Behavior

- Desktop: Full viewport height (100vh)
- Tablet: 60vh height
- Mobile: 40-50vh height with minimum 250px
- Touch-friendly controls (44px minimum on mobile)
- Orientation change handling

## JavaScript Usage

```javascript
// Initialize map manager
const mapManager = new LandMapManager({
    mapElement: document.getElementById('map'),
    mapData: window.mapPins,
    defaultLat: -6.5,
    defaultLng: 35.5,
    defaultZoom: 6
});

// Change map type
mapManager.setMapType('satellite');

// Add new marker
mapManager.addMarker(-6.8, 39.2, 'New Land', 'available');
```

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+
- Mobile browsers (iOS Safari, Chrome Mobile)