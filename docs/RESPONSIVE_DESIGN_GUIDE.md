# Responsive Design Guide

## Current Responsive Strategy

The application uses shared CSS from `static/css/styles.css` with page-specific template structures. The responsive behavior is primarily server-rendered and enhanced with lightweight JavaScript for search, booking, and dashboard interactions.

## Responsive Areas In The Current UI

- Public landing page and listing grids
- Search filters and result cards
- Registration and profile forms
- Owner listing forms and dashboard tables
- Reservation management screens
- Messaging and notification pages
- Payment submission flow

## Confirmed Responsive Patterns

- Stacked form layouts on smaller screens
- Grid-to-single-column listing transitions
- Full-width mobile controls for booking and auth actions
- Compact navigation behavior inside shared templates
- Mobile-safe booking flows that do not assume large desktop widths

## Areas That Need Continued Attention

- Owner dashboard density is still high on narrow screens.
- Reservation management tables likely need more mobile-specific summarization.
- Messaging and notification views should be validated for smaller touch devices.
- Multi-step listing creation should maintain clear progress feedback on phones.
- Search filters would benefit from a more deliberate mobile presentation pattern.

## Recommended Responsive Checklist

1. Verify all owner dashboard actions remain usable below 768px.
2. Collapse reservation tables into cards or expandable rows on phones.
3. Keep tap targets at comfortable mobile sizes in booking and admin actions.
4. Prevent horizontal overflow in form-heavy templates.
5. Test live search, wishlist, and payment flows on both mobile and desktop breakpoints.
